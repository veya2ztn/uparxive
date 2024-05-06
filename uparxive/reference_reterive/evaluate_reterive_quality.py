
import sys
import pathlib
import traceback
from pathlib import Path

module_dir = str(Path(__file__).resolve().parent)

# Add this directory to sys.path
if module_dir not in sys.path:
    sys.path.append(module_dir)

from Reference import *
import os,json
from tqdm.auto import tqdm

force_recompute_score = True
if __name__ == '__main__':
    parser = argparse.ArgumentParser('parse tf.event file to wandb', add_help=False)
    parser.add_argument('--root',type=str)
    parser.add_argument('--mode',type=str,default='normal', choices=['normal', 'remove_retrevied_citation','redo'])
    parser.add_argument('--structure_name', type=str, default='anystyle', choices=['anystyle', 'grobid','sentense'])
    args = parser.parse_known_args()[0]

    ROOTDIR = args.root #"/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_old_quant_ph"
    if os.path.isdir(ROOTDIR):
        alread_processing_file_list = os.listdir(os.path.join(ROOTDIR, 'unprocessed_json'))
    elif os.path.isfile(ROOTDIR):
        with open(ROOTDIR,'r') as f:
            alread_processing_file_list = [line.strip() for line in f]
        assert not os.path.isfile(alread_processing_file_list[0]),"should be arxiv id xxxx.xxxx"
        while True:
            ROOTDIR = os.path.dirname(ROOTDIR)
            if 'unprocessed_json' in os.listdir(ROOTDIR):break
            if len(ROOTDIR) < 4:
                continue
    else:
        raise NotImplementedError

    ROOT = ROOTDIR
    ROOTDIR = os.path.join(ROOT, 'unprocessed_json')
    ArxivIDs= alread_processing_file_list
    Analysys={'Missing_Structured.JSON':[],
            'Missing_Reterive.Citation':[],
            'Pass.DifferentLength':[],
            'Pass.HasFailFactCheck':[],
            'Reterive.AllDone':[],
            'Reterive.Part':[],
            'Reterive.Finish.Rows':0,
            'Reterive.Missing.Rows':0,
            'Fail_Case':[]
            }
    count = 0

    for i,arxiv_id in enumerate(tqdm(ArxivIDs)):
        #if i <30332:continue
        try:
            paper_fold = os.path.join(ROOTDIR, arxiv_id)
            paper_files= os.listdir(paper_fold)
            if args.mode != 'remove_retrevied_citation':
                # if 'reference.structured.jsonl' not in paper_files:
                #     Analysys['Missing_Structured.JSON'].append(arxiv_id)
                #     continue
                # if f'reference.es_retrived_citation.json' not in paper_files:
                #     Analysys['Missing_Reterive.Citation'].append(arxiv_id)
                #     continue   
                pass
            
            
            path = os.path.join(paper_fold,'reference.structured.jsonl.done')
            if os.path.exists(path) and not args.mode == 'redo':
                path = os.path.join(paper_fold,'reference.txt.done')
                with open(path,'r') as f:
                    reference_txts = [t.strip() for t in f]   
                Analysys['Reterive.Finish.Rows' ]+=len(reference_txts)
                if os.path.getsize(os.path.join(paper_fold,'reference.keys'))==0:
                    Analysys['Reterive.AllDone'].append(arxiv_id)
                    
                    continue
                else:
                    Analysys['Reterive.Part'].append(arxiv_id)
                    path = os.path.join(paper_fold,'reference.txt')
                    with open(path,'r') as f:
                        reference_txts = [t.strip() for t in f]   
                    Analysys['Reterive.Missing.Rows' ]+=len(reference_txts)
                    if args.mode == 'remove_retrevied_citation':
                        for name in [f'reference.es_retrived_citation.json', 
                                      #'reference.structured.jsonl',
                                      'reference.grobid.tei.xml',
                                      
                                     ]:
                            path = os.path.join(paper_fold,name)
                            if os.path.exists(path):os.remove(path) 
                        
                continue
            
            done_reference_strings = read_jsonl(os.path.join(paper_fold,'reference.structured.jsonl.done'))
            done_reterive_results  = read_jsonl(os.path.join(paper_fold,f'reference.es_retrived_citation.json.done'))
            done_reference_keys    = read_linefile(os.path.join(paper_fold,'reference.keys.done'))
            done_reference_txts    = read_linefile(os.path.join(paper_fold,'reference.txt.done'))

            
            


            reference_keys    = read_linefile(os.path.join(paper_fold,'reference.keys'))
            reference_txts    = read_linefile(os.path.join(paper_fold,'reference.txt'))

            reference_strings_path = os.path.join(paper_fold,'reference.structured.jsonl')
            if not os.path.exists(reference_strings_path):
                if len(reference_keys) == 0 and len(reference_txts)==0:
                    reference_strings=[]
                else:
                    #print(f"{arxiv_id} has no reterive results reference_keys={len(reference_keys)} reference_txts={len(reference_txts)}")
                    Analysys['Missing_Structured.JSON'].append(arxiv_id)
                    continue
            else:
                reference_strings = read_jsonl(reference_strings_path)
            
            reterive_results_path  = os.path.join(paper_fold,'reference.es_retrived_citation.json')
            if not os.path.exists(reterive_results_path):
                if len(reference_keys) == 0 and len(reference_txts)==0:
                    reterive_results=[]
                else:
                    #print(f"{arxiv_id} has no reterive results reference_keys={len(reference_keys)} reference_txts={len(reference_txts)}")
                    Analysys['Missing_Reterive.Citation'].append(arxiv_id)
                    continue
            else:
                reterive_results  = read_jsonl(reterive_results_path)
            
                
                


            if args.mode == 'redo':
                reference_strings = reference_strings + done_reference_strings
                reterive_results  = reterive_results  + done_reterive_results 
                reference_keys    = reference_keys    + done_reference_keys   
                reference_txts    = reference_txts    + done_reference_txts   
                done_reference_strings = []
                done_reterive_results  = []
                done_reference_keys    = []
                done_reference_txts    = []
            
            if len(reference_strings) != len(reterive_results):
                Analysys['Pass.DifferentLength'].append(arxiv_id)
                continue
            
            fail_reference_keys=[]
            fail_reference_txts=[]
            fail_reference_strings = []
            fail_reterive_results = []
            for index, (structured_citation, paper_information, citation_txt, citation_key) in enumerate(zip(reference_strings, reterive_results,reference_txts, reference_keys)):
                correct_pool = structured_citation[args.structure_name] if args.structure_name in structured_citation else structured_citation
                if correct_pool is None:continue
                ref       = Reference.load_from_dict(correct_pool) 
                #print(paper_information)
                if isinstance(paper_information,list):
                    result = paper_information
                elif isinstance(paper_information,dict):
                    if 'hits' in paper_information:
                        if len(paper_information['hits']['hits'])<1:
                            result = None
                        else:
                            result = paper_information['hits']['hits'][0]['_source']
                    else:
                        result = paper_information
                    result = [result]
                else:
                    raise ValueError(f"paper_information type is {type(paper_information)}")
                
                scored_result = []
                for t in result:
                    if t is None:
                        scored_result.append({'NotFind': 1,'score':0})
                        break
                    if 'unique_id' in t: 
                        scored_result.append(t|{'score':1})
                        break
                    if '_source' in t: t=t['_source']
                    candidate = Reference.load_from_dict(t)
                    if 'score' not in t or force_recompute_score:
                        score = similarity_structured(candidate,ref)
                        t['score']=score
                    scored_result.append(t)
                scored_result.sort(key=lambda x:x['score'],reverse=True)    
                
                result = scored_result[0]
                score  = result['score']
                #print("======")
                passQ = score> 0.8
                if passQ:
                    done_reference_keys.append(citation_key)
                    done_reference_txts.append(citation_txt)
                    done_reterive_results.append(result|{'score':score})
                    done_reference_strings.append(structured_citation)
                else:
                    fail_reference_keys.append(citation_key)
                    fail_reference_txts.append(citation_txt)
                    fail_reterive_results.append(result|{'score':score})
                    fail_reference_strings.append(structured_citation)

        except KeyboardInterrupt:
            raise
        except:
            traceback.print_exc()
            Analysys['Fail_Case'].append(arxiv_id)
            print(arxiv_id)
            continue
        
        save_linefile(os.path.join(paper_fold,'reference.keys.done'),done_reference_keys)
        save_linefile(os.path.join(paper_fold,'reference.txt.done'),done_reference_txts)
        save_jsonl(os.path.join(paper_fold,'reference.structured.jsonl.done'),done_reference_strings)
        save_jsonl(os.path.join(paper_fold,f'reference.es_retrived_citation.json.done'),done_reterive_results)
        
        save_linefile(os.path.join(paper_fold,'reference.keys'),fail_reference_keys)
        save_linefile(os.path.join(paper_fold,'reference.txt'),fail_reference_txts)
        save_jsonl(os.path.join(paper_fold,'reference.structured.jsonl'),fail_reference_strings)
        save_jsonl(os.path.join(paper_fold,f'reference.es_retrived_citation.json'),fail_reterive_results)
    for k,v in Analysys.items():
        if isinstance(v, list):
            print(f"{k}=>{len(v)}")
        else:
            print(f"{k}=>{v}")
    

    #print(Analysys['Reterive.Part'][0])
    SAVEROOT = os.path.join(ROOT, 'analysis.eval_reterive_quality')
    os.makedirs(SAVEROOT, exist_ok=True)
    with open(os.path.join(SAVEROOT,'reterive.alldone'),'w') as f:
        for arxiv_id in Analysys['Reterive.AllDone']:
            f.write(arxiv_id+'\n')
    
    with open(os.path.join(SAVEROOT,'reterive.remain'),'w') as f:
        for arxiv_id in Analysys['Reterive.Part']:
            f.write(arxiv_id+'\n')
    
    with open(os.path.join(SAVEROOT,'DifferentLength.remain'),'w') as f:
        for arxiv_id in Analysys['Pass.DifferentLength']:
            f.write(arxiv_id+'\n')

    if len(Analysys['Fail_Case'])>0:
        with open(os.path.join(SAVEROOT,'Fail_Case.remain'),'w') as f:
            for arxiv_id in Analysys['Fail_Case']:
                f.write(arxiv_id+'\n')

    with open(os.path.join(SAVEROOT,'Missing_Structured.remain'),'w') as f:
        for arxiv_id in Analysys['Missing_Structured.JSON']:
            f.write(arxiv_id+'\n')
    
    with open(os.path.join(SAVEROOT,'Missing_Reterive.remain'),'w') as f:
        for arxiv_id in Analysys['Missing_Reterive.Citation']:
            f.write(arxiv_id+'\n')
                