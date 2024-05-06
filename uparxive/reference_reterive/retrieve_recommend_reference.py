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
import numpy as np
class Unarxive_Mongo:
    def __init__(
        self,
        uri="mongodb://10.140.24.12:20034",
        db_name="unarxive",
        collection_name="bib",
    ):
        from pymongo.mongo_client import MongoClient
        from pymongo.server_api import ServerApi

        self._client = MongoClient(uri, server_api=ServerApi("1"))
        self._db = self._client[db_name]
        self._collection = self._db[collection_name]

    def from_hash_code(self, hash_code):
        """get bib entry from hash code in unarxive
        example of hash code: c617b28926bfdb5d456ce1888bfdfe3db47f09ca"""
        return self._collection.find_one(
            {
                "_id": hash_code,
            }
        )

    def from_bib_idx(self, bib_idx):
        """get bib entry from bib idx
        example of bib_idx: 'Ref.32 of ArXiv:1402.0451'"""
        return self._collection.find_one(
            {
                "idx": bib_idx,
            }
        )

    def find_and_update_by_hash_code(self, hash_code, new_values):
        """find and update by hash code"""
        return self._collection.find_one_and_update(
            {
                "_id": hash_code,
            },
            new_values,
        )



if __name__ == '__main__':
    unarxive_mongo = Unarxive_Mongo()

    with open("/nvme/zhangtianning.di/sharefold/num_of_ref_for_unarxive_paper.json", 'r') as f:
        num_of_ref_for_unarxive_paper = json.load(f)
    Analysys={'Missing_Structured.JSON':[],
              'Missing_Reterive.Citation':[],
              'No_Recommend':[],
              'Part_Recommend':[],
              'Full_Recommend':[],
              'Fail_Recommend':[],
              'RowPassByMultiRef':0,
              'RowPassByMissShot':0,
              'RowGetRecommend':0
        }
    ROOT = sys.argv[1]#"/nvme/zhangtianning.di/sharefold/whole_arxiv_old_quant_ph"
    ROOTDIR = os.path.join(ROOT,'unprocessed_json')
    arxiv_id_list = os.listdir(ROOTDIR)
    unarxive_missing_list = []
    for arxiv_id in tqdm(arxiv_id_list):
        arxiv_id = arxiv_id.strip()
        paper_fold = os.path.join(ROOTDIR, arxiv_id)
        paper_files= os.listdir(paper_fold)
        if 'reference.structured.jsonl' not in paper_files:
            Analysys['Missing_Structured.JSON'].append(arxiv_id)
            continue
        if 'reference.es_retrived_citation.json' not in paper_files:
            Analysys['Missing_Reterive.Citation'].append(arxiv_id)
            continue   
            
        Recommend_Citation_Path = os.path.join(paper_fold,'reference.recommend.mapping.json')
        #if os.path.exists(Recommend_Citation_Path):continue
        if arxiv_id not in num_of_ref_for_unarxive_paper:
            #print(f"the arxiv_id:{arxiv_id} not in database, why??")
            Analysys['No_Recommend'].append(arxiv_id)
            continue
            
            
        if num_of_ref_for_unarxive_paper[arxiv_id] == 0:continue
        done_reference_strings = read_jsonl(os.path.join(paper_fold,'reference.structured.jsonl.done'))
        done_reterive_results  = read_jsonl(os.path.join(paper_fold,'reference.es_retrived_citation.json.done'))
        done_reference_keys    = read_linefile(os.path.join(paper_fold,'reference.keys.done'))
        done_reference_txts    = read_linefile(os.path.join(paper_fold,'reference.txt.done'))

        reference_strings = read_jsonl(os.path.join(paper_fold,'reference.structured.jsonl'))
        reterive_results  = read_jsonl(os.path.join(paper_fold,'reference.es_retrived_citation.json'))
        reference_keys    = read_linefile(os.path.join(paper_fold,'reference.keys'))
        reference_txts    = read_linefile(os.path.join(paper_fold,'reference.txt'))
    
        reference_strings = reference_strings + done_reference_strings
        reterive_results  = reterive_results + done_reterive_results
        reference_keys    = reference_keys + done_reference_keys
        reference_txts    = reference_txts + done_reference_txts
        
        old_reference_keys= read_linefile(os.path.join(paper_fold,'reference.keys.bk'))
        old_reference_txts= read_linefile(os.path.join(paper_fold,'reference.txt.bk'))

        citation_pool_unarxive = []
        for idx in range(num_of_ref_for_unarxive_paper[arxiv_id]):
            citation_pool_unarxive.append(unarxive_mongo.from_bib_idx(f'Ref.{idx} of ArXiv:{arxiv_id}'))
        
        recommend_doi_reterive = {}
        for now_key, now_citation in zip(old_reference_keys, old_reference_txts):
            similar = [fuzz.ratio(t['bib_entry_raw'].lower(),now_citation.lower()) for t in  citation_pool_unarxive]
            if np.max(similar)<90:
                #print(f"【{now_citation}】 is not good to match any sentense in reference for arxiv={arxiv_id}" )
                Analysys['RowPassByMultiRef']+=1
                continue
            if ';' in now_citation:
                splited_citations = now_citation.split(';')
                splited_citations = [t.strip() for t in splited_citations if len(t.strip())>0]
                if len(splited_citations)>1:
                    Analysys['RowPassByMissShot']+=1
                    #print(f"【{now_citation}】 has more than one refs" )
                    continue
            Analysys['RowGetRecommend']+=1
            slot    = np.argmax(similar)
            
            recommend_doi_reterive[now_key] = citation_pool_unarxive[slot]
        if len(recommend_doi_reterive) == 0:
            Analysys['Fail_Recommend'].append(arxiv_id)
        elif len(recommend_doi_reterive) == min(len(citation_pool_unarxive),len(reference_txts)):
            Analysys['Full_Recommend'].append(arxiv_id)
        else:
            Analysys['Part_Recommend'].append(arxiv_id)
        with open(Recommend_Citation_Path,'w') as f:
            json.dump(recommend_doi_reterive,f)

    
    for k,v in Analysys.items():
        if isinstance(v, list):
            print(f"{k}=>{len(v)}")
        else:
            print(f"{k}=>{v}")
    
    
    #print(Analysys['Reterive.Part'][0])
    SAVEROOT = os.path.join(ROOT, 'analysis.generate_recommend_reference')
    os.makedirs(SAVEROOT, exist_ok=True)
    with open(os.path.join(SAVEROOT,'Analysys.json'),'w') as f:
        json.dump(Analysys,f)
    with open(os.path.join(SAVEROOT,'No_Recommend.ArxivIds'),'w') as f:
        for arxiv_id in Analysys['No_Recommend']:
            f.write(arxiv_id+'\n')