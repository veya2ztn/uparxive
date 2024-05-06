"""
This part due to the reason that we have the unarxive dataset whole already search the citation once. and we want to use it 
"""

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

def get_recommend_citation_pool(pool):
    ids = pool.get('ids',{})
    if pool.get('crossref_doi', None):
        ids['doi'] = pool['crossref_doi']
    if pool.get('contained_arXiv_ids', None):
        ids['arXiv'] = pool['contained_arXiv_ids'][0]['id']
    return ids
if __name__ == '__main__':
    Analysys={'Missing_Structured.JSON':0,
                'Missing_Reterive.Citation':0,
                'No_RecommendFile':0,
                'Has_RecommendFile':0,
                'Recommend_None':0,
                'Good_PassDoubleCheck':0,
                'Good_FailDoubleCheck':0,
                'Good_TotalDoubleCheck':0,
                'Extra_PassDoubleCheck':0,
                'Extra_FailDoubleCheck':0,
                'Extra_TotalDoubleCheck':0
            }
    ROOT = "/nvme/zhangtianning.di/sharefold/whole_arxiv_old_quant_ph"
    ROOTDIR = os.path.join(ROOT,'unprocessed_json')
    arxiv_id_list = os.listdir(ROOTDIR)
    unarxive_missing_list = []
    undo_for_double_check = []
    for i, arxiv_id in tqdm(enumerate(arxiv_id_list),total=len(arxiv_id_list)):

        #print(arxiv_id)
        arxiv_id = arxiv_id.strip()
        paper_fold = os.path.join(ROOTDIR, arxiv_id)
        paper_files= os.listdir(paper_fold)
        if 'reference.structured.jsonl' not in paper_files:
            Analysys['Missing_Structured.JSON']+=1
            continue
        if 'reference.es_retrived_citation.json' not in paper_files:
            Analysys['Missing_Reterive.Citation']+=1
            continue   

        Recommend_Citation_Path = os.path.join(paper_fold,'reference.recommend.mapping.json')
        if not os.path.exists(Recommend_Citation_Path):
            Analysys['No_RecommendFile']+=1
            continue
        else:
            Analysys['Has_RecommendFile']+=1

        done_reference_strings = read_jsonl(os.path.join(paper_fold,'reference.structured.jsonl.done'))
        done_reterive_results  = read_jsonl(os.path.join(paper_fold,'reference.es_retrived_citation.json.done'))
        done_reference_keys    = read_linefile(os.path.join(paper_fold,'reference.keys.done'))
        done_reference_txts    = read_linefile(os.path.join(paper_fold,'reference.txt.done'))
        undo_reference_strings = read_jsonl(os.path.join(paper_fold,'reference.structured.jsonl'))
        undo_reterive_results  = read_jsonl(os.path.join(paper_fold,'reference.es_retrived_citation.json'))
        undo_reference_keys    = read_linefile(os.path.join(paper_fold,'reference.keys'))
        undo_reference_txts    = read_linefile(os.path.join(paper_fold,'reference.txt'))


        
        # reference_strings = reference_strings + done_reference_strings
        # reterive_results  = reterive_results + done_reterive_results
        # reference_keys    = reference_keys + done_reference_keys
        # reference_txts    = reference_txts + done_reference_txts

        with open(Recommend_Citation_Path,'r') as f:
            recommend_doi_reterive = json.load(f)
        extra_good_ids = {'Good':[], 'Extra':[]}
        for part, series in [['Good', zip(done_reference_keys, done_reference_txts, done_reference_strings, done_reterive_results)],
                            ['Extra',zip(undo_reference_keys, undo_reference_txts, undo_reference_strings, undo_reterive_results)]]:
            for slot, (reference_key, reference_string, reference_query, reference_result) in enumerate(series):

                if reference_key not in recommend_doi_reterive:continue
                recommend_unqiue_id = UniqueID.from_dict(get_recommend_citation_pool(recommend_doi_reterive[reference_key]))
                if recommend_unqiue_id.is_nan():
                    Analysys['Recommend_None']+=1
                    continue
                retrieved_result = reference_result
                if isinstance(retrieved_result, dict):retrieved_result=[retrieved_result]
                assert isinstance(retrieved_result, list)
                DoubleCheck = False
                for result in retrieved_result:
                    retrieved_unique_id = UniqueID.from_dict(result)
                    DoubleCheck = retrieved_unique_id.is_same(recommend_unqiue_id)
                    if DoubleCheck:break
                Analysys[f'{part}_TotalDoubleCheck']+=1
                if not DoubleCheck:
                    # if part == 'Good':
                    #     undo_for_double_check.append(
                    #     {
                    #         'arxiv_id': arxiv_id,
                    #         'citation_string': reference_string,
                    #         'retrieve_result': reference_result,
                    #         'recommend_ids': recommend_unqiue_id.to_dict(),
                    #         'retrieve_ids':retrieved_unique_id.to_dict(),

                    #     }
                    #     )
                    Analysys[f'{part}_FailDoubleCheck']+=1
                else:
                    Analysys[f'{part}_PassDoubleCheck']+=1
                    if part == 'Extra':
                        extra_good_ids['Extra'].append(slot)
                        #print("=======")

 
        if len(extra_good_ids['Extra'])>0:
            extra_reference_keys =[  v for i, v in enumerate(undo_reference_keys)       if i in extra_good_ids['Extra']]
            extra_reference_txts =[  v for i, v in enumerate(undo_reference_txts)       if i in extra_good_ids['Extra']]
            extra_reference_strings =[  v for i, v in enumerate(undo_reference_strings) if i in extra_good_ids['Extra']]
            extra_reterive_results =[  v for i, v in enumerate(undo_reterive_results)   if i in extra_good_ids['Extra']]
            
            done_reference_keys.extend(extra_reference_keys)
            done_reference_txts.extend(extra_reference_txts)
            done_reference_strings.extend(extra_reference_strings)
            done_reterive_results.extend(extra_reterive_results)
            
            undo_reference_keys    =[    v for i, v in enumerate(undo_reference_keys) if i not in extra_good_ids['Extra']]
            undo_reference_txts    =[    v for i, v in enumerate(undo_reference_txts) if i not in extra_good_ids['Extra']]
            undo_reference_strings =[ v for i, v in enumerate(undo_reference_strings) if i not in extra_good_ids['Extra']]
            undo_reterive_results  =[  v for i, v in enumerate(undo_reterive_results) if i not in extra_good_ids['Extra']]
            
            
            save_linefile(os.path.join(paper_fold,'reference.keys.done'),done_reference_keys)
            save_linefile(os.path.join(paper_fold,'reference.txt.done'),done_reference_txts)
            save_jsonl(os.path.join(paper_fold,'reference.structured.jsonl.done'),done_reference_strings)
            save_jsonl(os.path.join(paper_fold,'reference.es_retrived_citation.json.done'),done_reterive_results)

            save_linefile(os.path.join(paper_fold,'reference.keys'),undo_reference_keys)
            save_linefile(os.path.join(paper_fold,'reference.txt'),undo_reference_txts)
            save_jsonl(os.path.join(paper_fold,'reference.structured.jsonl'),undo_reference_strings)
            save_jsonl(os.path.join(paper_fold,'reference.es_retrived_citation.json'),undo_reterive_results)

    for k,v in Analysys.items():
        if isinstance(v, list):
            print(f"{k}=>{len(v)}")
        else:
            print(f"{k}=>{v}")