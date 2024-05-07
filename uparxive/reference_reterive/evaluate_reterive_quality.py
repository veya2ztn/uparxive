
import sys
import pathlib
import traceback
from pathlib import Path
from .Reference import *
import os,json
from tqdm.auto import tqdm
from uparxive.batch_run_utils import BatchModeConfig, dataclass
from simple_parsing import field

@dataclass 
class QualityESConfig(BatchModeConfig):
    task_name = "quality_es_retrieve"
    force_recompute_score: bool = False
    mode : str = field(default='normal', choices=['normal', 'remove_retrevied_citation','redo'])
    upper_score : float = 0.95
    lower_score : float = 0.5
    batch_retrieve: int = 0

def analysis_quality_of_retrieve_result(retrieve_results:List[dict], args:QualityESConfig):
    """
    input is a path: 2304.01850/uparxive/Reference/reference.es_retrived_citation.json
        This function will analysis the quality of the retrieve result and produce the final retrieve result
        - if the score too small, usually means
            - the content is not archieve in our citation database
            - the citation information is too small to find a reference
        - if the score is considerable and two of the three retrieve engine produce the same result, we can consider the result is correct
    """
    # retrieve_result must be placed in sorted score
    if len(retrieve_results) ==0:
        return {'retrieved_level': 0, 'candidate': {}}
    if retrieve_results[0].get('unique_id') == 'the_is_a_note':
        return {'retrieved_level': -1, 'candidate':retrieve_results[0]}   
    retrieve_results.sort(key=lambda x:x['score'],reverse=True)
    if retrieve_results[0]['score'] == 1:
        # the score is high enough, we can consider the result is correct
        return {'retrieved_level': 5, 'candidate':retrieve_results[0]}   
    if retrieve_results[0]['score'] > args.upper_score:
        # the score is high enough, we can consider the result is correct
        return {'retrieved_level': 4, 'candidate':retrieve_results[0]}
    if retrieve_results[0]['score'] < args.lower_score:
        # the score is too small, we can consider the result is wrong
        return {'retrieved_level': 0, 'candidate':retrieve_results[0]}
    ## lets get the score for each retrieve engine
    best_result_for_each_engine = {}
    for retrieve_result in retrieve_results:
        engine = retrieve_result['from_structure']
        if engine in best_result_for_each_engine:continue
        best_result_for_each_engine[engine] = retrieve_result
    
    retrieve_results = list(best_result_for_each_engine.values())
    #retrieve_results.sort(key=lambda x:x['score'],reverse=True)   
    if len(retrieve_results) == 1:
        # if only one engine produce the result, we can consider the result is wrong
        return {'retrieved_level': 2, 'candidate':retrieve_results[0]}
    else:
        # if two engine produce the same result, we can consider the result is correct
        result1,resutl2 = retrieve_results[0:2] ### the first two result and must be different engine
        title1 = result1.get('title',"aaaa")
        title2 = resutl2.get('title',"bbbb")
        if fuzz.ratio(title1, title2) > 0.95:
            return {'retrieved_level':3, 'candidate':retrieve_results[0]}
        
        ### check title first, because it cover unique_id check
        ref1   = Reference.load_from_dict(result1)
        ref2   = Reference.load_from_dict(resutl2)
        
        if ref1.unique_id and ref2.unique_id and ref1.unique_id.is_same(ref2.unique_id):
                return {'retrieved_level':3, 'candidate':retrieve_results[0]}
       
    
    return {'retrieved_level':1, 'candidate':retrieve_results[0]}

def analysis_quality_of_retrieve_result_wrapper(args):
    retrieve_results, args = args
    return analysis_quality_of_retrieve_result(retrieve_results, args)
    
from multiprocessing import Pool
def process_results(result_per_keys, args:QualityESConfig):
    num_processes = args.batch_retrieve
    
    if num_processes == 0:
        results = []
        bar = tqdm(result_per_keys, leave=False,position=1) if args.verbose else result_per_keys
        for result in bar:
            results.append(analysis_quality_of_retrieve_result(result, args))
        return results
    else:
        assert args.batch_num == 0, "do multiprocessing either in process_one_path or in process_one_reflist"
        with Pool(processes=num_processes) as pool:
            args_list = [(result, args) for result in result_per_keys]
            results = list(tqdm(pool.imap(analysis_quality_of_retrieve_result_wrapper, args_list), total=len(result_per_keys), leave=False,position=1))
    return results

def process_one_path(retrieve_results_path:str, args:QualityESConfig):
    """
    Input:
        retrieve_results_path: 2304.01850/uparxive/Reference/reference.es_retrived_citation.json
    """
    assert os.path.isfile(retrieve_results_path), f"{retrieve_results_path} is not a file"
    arxiv_id   = retrieve_results_path.rsplit("/")[-4]
    OUTPUTDIR  = os.path.dirname(retrieve_results_path)
    OUTPUTPATH = os.path.join(OUTPUTDIR,f"reference.retrived_results_final.json")
    if os.path.exists(OUTPUTPATH) and not args.redo:
        return arxiv_id, 'already_done'

    with open(retrieve_results_path, 'r') as f:
        result_per_keys = json.load(f)
    
    if args.verbose:tqdm.write(f"now deal with ====> [{arxiv_id}]")

    #results = process_one_reflist(final_ref_list, es, args)
    try:
        results = process_results(result_per_keys, args)
        assert len(results) == len(result_per_keys)
        with open(OUTPUTPATH, 'w') as f:
            json.dump(results, f)
        return arxiv_id, 'pass'
    except:
        if args.debug : 
            tqdm.write(f"Error in {retrieve_results_path}")
            traceback.print_exc()
            raise
        return arxiv_id, 'error'

def process_one_path_wrapper(args):
    arxiv_path, args = args
    return process_one_path(arxiv_path, args) 

