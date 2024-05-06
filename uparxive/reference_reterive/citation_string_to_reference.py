import os,re
import json
import sys
from pathlib import Path
from .Reference import Reference
from .evaluate_reterive_quality import similarity_structured
from uparxive.xml_to_json.check_string_is_citation import should_the_string_be_regard_as_note
from tqdm.auto import tqdm, trange
from collections import defaultdict
from nameparser import HumanName
from pathlib import Path
from elasticsearch import Elasticsearch
from dateutil import parser
import sys
from tqdm.auto import tqdm
from uparxive.batch_run_utils import BatchModeConfig, dataclass

selected_engine = f"http://localhost:9200"
es = Elasticsearch(selected_engine,request_timeout=1000)

@dataclass 
class RetrieveESConfig(BatchModeConfig):
    port:int = 9200
    score_limit : float = 0.5
    search_engine : str = 'integrate'
    redo : bool = False
    verbose : bool = False
    notchecknote : bool = False
    task_name = 'retrieve_reference'
    
def contains_arxiv_id(text):
    # Regular expression pattern for matching ArXiv IDs
    # It matches "arXiv:" or "arXiv" followed by optional space(s) and the ID pattern
    arxiv_pattern = r'arxiv:? *\s*(\d{4})\.(\d{3,4})(v\d+)?'
    
    # Search for the pattern in the text
    match = re.search(arxiv_pattern, text)
    
    # Return True if a match is found, False otherwise
    return match

def strfy(x):
    while isinstance(x, list):
        x = " ".join(x)
    return x

def get_anystyle_ref_query_dict_v21(info):
    search_should = []
    flags = defaultdict(int)
    if 'author' in info and info['author']:
        for author_i in info['author'][:3]:
            if isinstance(author_i,dict):
                name = HumanName(" ".join([author_i.get("given", ""), author_i.get("family", "")]).strip(),initials_format="{first} {middle}")
            elif isinstance(author_i, str):
                name = HumanName(full_name=author_i, initials_format="{first} {middle}")
            name = name.initials() + ' ' + name.last
            search_should.append({
                "multi_match": {"query": "{}".format(name),"fields": ["author.0", "author.1", "author.2"],"type": "best_fields"}
            })
            flags['author'] += 1
    volume = (info.get('volume',None) or info.get('journal_volume',None))
    if not volume and 'imprint' in info and info['imprint'] and 'volume' in info['imprint']:
       volume =  info['imprint']['volume'] 
    if volume:
        search_should.append({
            "multi_match": {"query": strfy(volume),"fields": ["jvol"],"type": "best_fields"}
        })
        flags['volume'] = 1
    
    page = (info.get('page',None) or info.get('journal_page',None))
    if not page and 'imprint' in info and info['imprint'] and 'page' in info['imprint']:
       page =  info['imprint']['page']
    
    if page:
        search_should.append({
            "multi_match": {"query": strfy(page),"fields": ["jpage"],"type": "best_fields"}
        })
        flags['page'] = 1
    

    title = (info.get('title',None) or info.get('title',None))
    if title:
        search_should.append({
            "multi_match": {"query": strfy(title),"fields": ["title" ],"type": "best_fields"}
        })
        flags['title'] = 1
                      
    journal = (info.get('container-title',None) or info.get('journal',None) or info.get('publisher',None))
    if journal:
        search_should.append({
            "multi_match": {"query": strfy(journal),"fields": ["jname"],"type": "best_fields"}
        })
        flags['vene'] = 1
    
    
    year = None
    if not year:
        year = info.get('year', None)
    if not year and 'issued' in info and info['issued'] and 'date-parts' in info['issued']:
        date_part = info['issued']['date-parts']
        while isinstance(date_part, list):
            date_part = date_part[0] 
        year = date_part
    if not year and 'imprint' in info and info['imprint'] and 'date' in info['imprint']:
        date_part = info['imprint']['date']
        while isinstance(date_part, list):
            date_part = date_part[0] 
        year = date_part
    
    if year:
        year = parser.parse(year).year
        search_should.append({
            "multi_match": {"query": strfy(year),"fields": ["year"],"type": "best_fields"}
        })
        flags['year'] = 1

    
    ### form the query 
    query_dict = {
        "bool": {
            "should": search_should
        }
    }
    return query_dict

class anystyle_ref_search_v21:
    @staticmethod
    def get_es_query_dict_from_Reference(ref:Reference):
        search_should = []
        flags = defaultdict(int)
        if ref.author:
            authors = ref.author.split(',') if isinstance(ref.author,str) else ref.author
            for author_i in authors[:3]:
                search_should.append({
                    "multi_match": {"query": "{}".format(author_i),"fields": ["author.0", "author.1", "author.2"],"type": "best_fields"}
                })
                flags['author'] += 1
        
        if ref.journal_volume:
            search_should.append({
                "multi_match": {"query": strfy(ref.journal_volume),"fields": ["jvol"],"type": "best_fields"}
            })
            flags['volume'] = 1
        
        if ref.journal_page:
            search_should.append({
                "multi_match": {"query": strfy(ref.journal_page),"fields": ["jpage"],"type": "best_fields"}
            })
            flags['page'] = 1
        
        if ref.title:
            search_should.append({
                "multi_match": {"query": strfy(ref.title),"fields": ["title" ],"type": "best_fields"}
            })
            flags['title'] = 1
                        
        if ref.journal:
            search_should.append({
                "multi_match": {"query": strfy(ref.journal),"fields": ["jname"],"type": "best_fields"}
            })
            flags['vene'] = 1
        

        if ref.year:
            search_should.append({
                "multi_match": {"query": strfy(ref.year),"fields": ["year"],"type": "best_fields"}
            })
            flags['year'] = 1

        
        ### form the query 
        query_dict = {
            "bool": {
                "should": search_should
            }
        }
        return query_dict
    
    @staticmethod
    def search(_es, query, size=1):
        return _es.search(index='s2-papers-v2.1', query=query, size=size).body

class anystyle_ref_search_alex_v1(anystyle_ref_search_v21):
    @staticmethod
    def search(_es, query, size=1):
        return _es.search(index='alex-papers-v1', query=query, size=size).body

class anystyle_ref_search_integrate:
    @staticmethod
    def get_es_query_dict_from_Reference(ref:Reference):
        search_should = []
        flags = defaultdict(int)
        if ref.author:
            authors = ref.author.split(',') if isinstance(ref.author,str) else ref.author
            for author_i in authors[:3]:
                search_should.append({
                    "multi_match": {"query": "{}".format(author_i),"fields": ["author.0", "author.1", "author.2"],"type": "best_fields"}
                })
                flags['author'] += 1
        
        if ref.journal_volume:
            search_should.append({
                "multi_match": {"query": strfy(ref.journal_volume),"fields": ["journal_volume"],"type": "best_fields"}
            })
            flags['volume'] = 1
        
        if ref.journal_page:
            search_should.append({
                "multi_match": {"query": strfy(ref.journal_page),"fields": ["journal_page"],"type": "best_fields"}
            })
            flags['page'] = 1
        
        if ref.title:
            search_should.append({
                "multi_match": {"query": strfy(ref.title),"fields": ["title" ],"type": "best_fields"}
            })
            flags['title'] = 1
                        
        if ref.journal:
            search_should.append({
                "multi_match": {"query": strfy(ref.journal),"fields": ["journal"],"type": "best_fields"}
            })
            flags['vene'] = 1
        

        if ref.year:
            search_should.append({
                "multi_match": {"query": strfy(ref.year),"fields": ["year"],"type": "best_fields"}
            })
            flags['year'] = 1

        
        ### form the query 
        query_dict = {
            "bool": {
                "should": search_should
            }
        }
        return query_dict
    
    @staticmethod
    def search(_es, query, size=1):
        return _es.search(index='integrate20240311', query=query, size=size).body

class anystyle_ref_search_sentense:
    @staticmethod
    def get_es_query_dict_from_Reference(ref:Reference):
        search_should = []
        flags = defaultdict(int)
        assert ref.content

        search_should.append({
            "multi_match": {"query": "{}".format(ref.content),"fields": ["content", "short_content"],"type": "best_fields"}
        })
        flags['author'] += 1

        
        ### form the query 
        query_dict = {
            "bool": {
                "should": search_should
            }
        }
        return query_dict
    
    @staticmethod
    def search(_es, query, size=1):
        return _es.search(index='integrate20240311', query=query, size=size).body

def retrieve_reference(es,ref,num,search_engine):
    if search_engine == 'semantic_scholar':
        query = anystyle_ref_search_v21.get_es_query_dict_from_Reference(ref)
        result = anystyle_ref_search_v21.search(es,query,num)
    elif search_engine == 'alex':
        query = anystyle_ref_search_alex_v1.get_es_query_dict_from_Reference(ref)
        result = anystyle_ref_search_alex_v1.search(es,query,num)
    elif search_engine == 'integrate':
        query = anystyle_ref_search_integrate.get_es_query_dict_from_Reference(ref)
        result = anystyle_ref_search_integrate.search(es,query,num)
    elif search_engine == 'sentense':
        query = anystyle_ref_search_sentense.get_es_query_dict_from_Reference(ref)
        result = anystyle_ref_search_sentense.search(es,query,num)
    else:
        raise NotImplementedError
    return result 

def process_one_reflist(reflist, es, args:RetrieveESConfig):
    search_engine = args.search_engine 
    score_limit=args.score_limit
    verbose =args.verbose
    checknote= not args.notchecknote
        
    whole_results = []
    bar = tqdm(reflist, leave=False,position=1) if args.verbose else reflist
    for refdict_dual in bar:
        isNote = False
        if checknote: 
            content = refdict_dual['plain_sentense']['content']
            isNote  = should_the_string_be_regard_as_note(content)
        if isNote:
            results = [{'unique_id': 'the_is_a_note'}]
            #tqdm.write(f"this is a note {content}")
        else:
            results = process_one_duel_structure(refdict_dual, es, search_engine, score_limit,verbose=verbose)
        whole_results.append(results)
    return whole_results


def normlize_one_string(string):
    string = string.lower().replace('\n', " ")
    string = re.sub(r'\s+', ' ', string)
    return string

def process_one_duel_structure(refdict_dual, es, search_engine, score_limit=0.5, verbose=False):
    score = None
    retrieved_results = []
    ## phase 1: plain reterive the structured reference
    for structure_name, refdict in refdict_dual.items():
        unique_id = (refdict.get('unique_id',None) or refdict.get('arxiv',None))
        #tqdm.write(f"treat as {structure_name} {refdict}")
        if unique_id is None:
            arxiv_match = contains_arxiv_id(refdict.get('content','').lower().strip('.'))
            unique_id = arxiv_match.group(0) if arxiv_match else None
        
        if unique_id is not None:
            result = {'unique_id':unique_id}
            score  = 1
            retrieved_results.append(result|{'score':score,'from_structure':structure_name})

        else:
            ref    = Reference.load_from_dict(refdict)
            result = retrieve_reference(es,ref, 1, search_engine if structure_name != 'plain_sentense' else 'sentense')
            if not('hits' in result and 'hits' in result['hits'] and len(result['hits']['hits'])>0):continue
            result    = result['hits']['hits'][0]['_source']
            candidate = Reference.load_from_dict(result)
            score     = similarity_structured(candidate,ref)
            retrieved_results.append(result|{'score':score,'from_structure':structure_name})
        
        retrieved_results.sort(key=lambda x:x['score'],reverse=True)   
        score=retrieved_results[0]['score'] 
        if score > 0.95:
            return retrieved_results
    # if score > 0.8:
    #     ### if anystyle and grobid return very similar result, we also regard true
    #     for results in retrieved_results:
    #         title_now = normlize_one_string(results.get('title',""))



    if verbose:
        tqdm.write(f'score={score} too small for ===> {ref} ===> {retrieved_results} we reterive more')
    for structure_name, refdict in refdict_dual.items():
        if score is not None and score <= score_limit:
            ref    = Reference.load_from_dict(refdict)
            result = retrieve_reference(es,ref, 5, search_engine if structure_name != 'plain_sentense' else 'sentense')
            scored_result = []
            for t in result['hits']['hits']:
                t = t['_source']
                candidate = Reference.load_from_dict(t)
                score = similarity_structured(candidate,ref)
                scored_result.append(t|{'score':score,'from_structure':structure_name})
            retrieved_results.extend(scored_result)
            retrieved_results.sort(key=lambda x:x['score'],reverse=True)   
            retrieved_results=retrieved_results[:3]
            score=retrieved_results[0]['score'] 
        
    return retrieved_results

def build_the_structured_citation_pool(INPUTPATH, REFTEXT):
    with open(INPUTPATH,'r') as f:
        reflist = json.load(f)
    with open(REFTEXT,'r') as f:
        reftext = [t.strip() for t in f.readlines()]
    assert len(reftext) == len(reflist), f"reftext={len(reftext)} reflist={len(reflist)}"

    final_ref_list = []
    for refdualpool, text in zip(reflist,reftext):
        final_ref_list.append(refdualpool|{'plain_sentense':{'content':text}})
    return final_ref_list

def process_one_path(ROOTDIR, args:RetrieveESConfig):
    selected_engine = f"http://localhost:{args.port}"
    es = Elasticsearch(selected_engine,request_timeout=1000)
    #es.indices.refresh(index='integrate20240311')
    arxiv_id = ROOTDIR.rstrip('/').split('/')[-3]
    INPUTPATH  = os.path.join(ROOTDIR,'reference.structured.jsonl')
    REFTEXT    = os.path.join(ROOTDIR,'reference.txt')
    OUTPUTPATH = os.path.join(ROOTDIR,f"reference.es_retrived_citation.json")
    if not os.path.exists(REFTEXT):
        return arxiv_id, 'no_ref_text'
    if os.path.getsize(REFTEXT) == 0:
        return arxiv_id, 'empty_ref_text'
    if not os.path.exists(INPUTPATH):
        return arxiv_id, 'no_ref_structured'
    if os.path.exists(OUTPUTPATH) and not args.redo:
        return arxiv_id, 'already_done'

    try:
        final_ref_list = build_the_structured_citation_pool(INPUTPATH, REFTEXT)
        if args.verbose:tqdm.write(f"now deal with ====> [{arxiv_id}]")
    
        results = process_one_reflist(final_ref_list, es, args)
        with open(OUTPUTPATH, 'w') as f:
            json.dump(results, f)
        return arxiv_id, 'pass'
    except:
        tqdm.write(f"Error in {ROOTDIR}")
        if len(alread_processing_file_list) == 1 or args.debug:
            traceback.print_exc()
        if args.debug:
            raise
        return arxiv_id, 'error'

def process_one_path_wrapper(args):
    arxiv_path, args = args
    return process_one_path(arxiv_path, args) 
if __name__ == '__main__':
    import os
    import sys
    from tqdm.auto import tqdm
    import numpy as np
    import argparse, logging,traceback
    parser = argparse.ArgumentParser()
    parser.add_argument("--root_path", type=str)
    parser.add_argument("--index_part", type=int, default=0)
    parser.add_argument('--num_parts', type=int, default=1)
    parser.add_argument('--port', type=int, default=9200)
    parser.add_argument('--score_limit',  type=float, default=0.5)
    parser.add_argument('--search_engine',  type=str, default='integrate')
    parser.add_argument('--redo', action='store_true', help='', default=False)
    parser.add_argument('--verbose', '-v', action='store_true', help='', default=False)
    parser.add_argument('--notchecknote',  action='store_true', help='', default=False)
    args = parser.parse_args()

    filelistpath = args.root_path
    analysis = {}
    task_name= 'retreive_reference'
    if os.path.isdir(filelistpath):
        root_path = filelistpath
        while not root_path.endswith('whole_arxiv_all_files'):
            root_path = os.path.dirname(root_path)
            assert root_path != '/'
        root_path = os.path.join(root_path,f'analysis.{task_name}')
        all_file_list = [filelistpath]
    elif os.path.isfile(filelistpath):
        root_path = filelistpath
        while not root_path.endswith('whole_arxiv_all_files'):
            root_path = os.path.dirname(root_path)
            assert root_path != '/'
        root_path = os.path.join(root_path,f'analysis.{task_name}')
        
        os.makedirs(root_path,exist_ok=True)
        with open(filelistpath,'r') as f:
            all_file_list = [t.strip() for t in f.readlines()]
    else:
        raise NotImplementedError("What is your filelistpath?")
    index_part= args.index_part
    num_parts = args.num_parts 

    totally_paper_num = len(all_file_list)
    logging.info(totally_paper_num)
    if totally_paper_num > 1:
        divided_nums = np.linspace(0, totally_paper_num, num_parts+1)
        divided_nums = [int(s) for s in divided_nums]
        start_index = divided_nums[index_part]
        end_index   = divided_nums[index_part + 1]
    else:
        start_index = 0
        end_index   = 1
        verbose = True
    alread_processing_file_list = all_file_list[start_index:end_index]

    selected_engine = f"http://localhost:{args.port}"
    es = Elasticsearch(selected_engine,request_timeout=1000)
    es.indices.refresh(index='integrate20240311')

    for file_idx, ROOTDIR in enumerate(tqdm(alread_processing_file_list,position=0)):
        
        arxiv_id = ROOTDIR.rstrip('/').split('/')[-3]
        INPUTPATH  = os.path.join(ROOTDIR,'reference.structured.jsonl')
        REFTEXT    = os.path.join(ROOTDIR,'reference.txt')
        OUTPUTPATH = os.path.join(ROOTDIR,f"reference.es_retrived_citation.json")
        if not os.path.exists(REFTEXT):
            analysis['no_ref_text'] = analysis.get('no_ref_text',[])+[ROOTDIR]
            continue
        if os.path.getsize(REFTEXT) == 0:
            analysis['empty_ref_text'] = analysis.get('empty_ref_text',[])+[ROOTDIR]
            continue
        if not os.path.exists(INPUTPATH):
            analysis['no_ref_structured'] = analysis.get('no_ref_structured',[])+[ROOTDIR]
            continue
        if os.path.exists(OUTPUTPATH) and not args.redo:
            analysis['already_done'] = analysis.get('already_done',[])+[ROOTDIR]
            continue

        final_ref_list = build_the_structured_citation_pool(INPUTPATH, REFTEXT)
        tqdm.write(f"now deal with ====> [{arxiv_id}]")
        try:
            results = process_one_reflist(final_ref_list, es, args.search_engine , args.score_limit, args.verbose, not args.notchecknote)
            with open(OUTPUTPATH, 'w') as f:
                json.dump(results, f)
        except:
            tqdm.write(f"Error in {ROOTDIR}")
            if len(alread_processing_file_list) == 1:
                traceback.print_exc()
            analysis['error'] = analysis.get('error',[])+[ROOTDIR]
            continue
    
    print(root_path)
    os.makedirs(root_path,exist_ok=True)
    if num_parts > 1:
        for key, val in analysis.items():
            print(f"{key}=>{len(val)}")
            fold = os.path.join(root_path,f"{key.lower()}.filelist.split")
            os.makedirs(fold, exist_ok=True)
            with open(os.path.join(fold,f"{start_index}-{end_index}"), 'w') as f:
                for line in (val):
                    f.write(line+'\n')
    else:
        #print(analysis)
        for key, val in analysis.items():
            print(f"{key}=>{len(val)}")
            # with open(os.path.join(root_path,f"{key.lower()}.filelist"), 'w') as f:
            #     for line in set(val):
            #         f.write(line+'\n')