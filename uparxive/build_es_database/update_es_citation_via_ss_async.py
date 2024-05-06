# all in one
import os
import json
import jsonlines
from tqdm.auto import tqdm
import sys,json
from pathlib import Path
from elasticsearch import Elasticsearch
from elasticsearch.helpers import streaming_bulk
module_dir = str(Path(__file__).resolve().parent.parent)
# Add this directory to sys.path
if module_dir not in sys.path:
    sys.path.append(module_dir)
from reference_reterive.Reference import *
from build_redis_database.utils import *
from build_es_database.utils import *
import gzip
from CitationStyleLanguage import *
import traceback

if __name__ == '__main__':
    import logging

    ROOTDIR = "/nvme/zhangtianning.di/semantic_scholar/all_filepath.json"
    LOCKDIR = "/nvme/zhangtianning.di/semantic_scholar/update_citation_content/lock"
    LOGDIR  = "/nvme/zhangtianning.di/semantic_scholar/update_citation_content/analysis"
    FAILSAVE= "/nvme/zhangtianning.di/semantic_scholar/update_citation_content/failcase"
    os.makedirs(LOCKDIR, exist_ok=True)
    os.makedirs(LOGDIR, exist_ok=True)
    os.makedirs(FAILSAVE, exist_ok=True)
    with open(ROOTDIR,'r') as f:
        all_paths = json.load(f)

    redis_host = "localhost"
    redis_port = 6379
    redis_password = ""
    r = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True)

    ES_INDEX="integrate20240311"
    es = Elasticsearch("http://localhost:9200")


    with open("/nvme/zhangtianning.di/semantic_scholar/vene_alias_map.json", 'r') as f:
        vene_name_to_alias = json.load(f)

    for file_idx, file_path in enumerate(all_paths):
        file_name = os.path.split(file_path)[-1].split('.')[0]
        lock_file = os.path.join(LOCKDIR,f'{file_name}.lock')
        
        if os.path.exists(lock_file):
            print(f"{lock_file} exist, continue....")
            continue
        print(f'create lock file at {lock_file}')
        os.system(f'touch {lock_file}')
        usejsonl = False
        if os.path.getsize(file_path)==0:continue
        
        usejsonl = True
        with open(file_path, 'r') as f:
            json_data = f.readlines()

        Analysis= {'update' : 0, 
                    'total': 0, 
                    'crossref_normal_skip': 0,
                    'escape_by_bad_for_citation': 0,
                    'escape_by_not_index_yet': 0,
                    'escape_by_no_unique_id':0,
                    'escape_by_already_have':0
                    }
        failcase    = []

        for i, rowdata in tqdm(enumerate(json_data),total=len(json_data)):
            try:
                if usejsonl:
                    rowdata = json.loads(rowdata)
                Analysis['total']+=1
                newref = Reference.load_from_dict(rowdata)
                
                digital_index = get_digital_worth_index_from_unique_id(r,newref.unique_id)
                if digital_index is None:
                    Analysis['escape_by_no_unique_id']+=1
                    continue
                
                citation = CitationStyleLanguage.from_dict(newref.to_dict())
                if not citation.is_good_for_citation():
                    Analysis['escape_by_bad_for_citation']+=1
                    continue  
                
                if not es.exists(index=ES_INDEX, id=digital_index).body:
                    Analysis['escape_by_not_index_yet']+=1
                    continue
                else:
                    body  = es.get(index=ES_INDEX, id=digital_index)['_source']
                    if 'doc' in body:
                        should_upate = True
                        body = body['doc']
                        es.delete(index=ES_INDEX, id=digital_index)
                        es.index(index=ES_INDEX, id=digital_index, body=body)
                    if 'short_content' in body:
                        Analysis['escape_by_already_have']+=1
                        continue
                    new_information = {'short_content':citation.to_citation('short')}
                    if len(new_information) > 0:
                        body = body|format_es_paper(new_information,vene_name_to_alias)
                        es.update(index=ES_INDEX, id=digital_index, body={'doc':body}) #<-- you must use doc
                        Analysis['update']+=1
            except KeyboardInterrupt:
                raise
            except:# not KeyboardInterrupt
                if 'reference' in rowdata: del rowdata['reference']
                traceback.print_exc()
                failcase.append(rowdata)
                    

        for k,v in Analysis.items():
            if isinstance(v, list):
                print(f"{k}=>{len(v)}")
            else:
                print(f"{k}=>{v}")
        if len(failcase) > 0:
            with open(os.path.join(FAILSAVE,f'{file_name}.jsonl'), 'w') as f:
                for line in failcase:
                    f.write(json.dumps(line)+'\n')


        with open(os.path.join(LOGDIR,f'{file_name}.Analysis.json'), 'w') as f:
            json.dump(Analysis, f)
