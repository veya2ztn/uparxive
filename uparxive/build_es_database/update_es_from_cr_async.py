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
import traceback
with open("/nvme/zhangtianning.di/semantic_scholar/vene_alias_map.json", 'r') as f:
    vene_name_to_alias = json.load(f)



if __name__ == '__main__':
    import logging
    ROOTDIR = "/nvme/zhangtianning.di/crossref/crossref.filelist.json"
    LOCKDIR = "/nvme/zhangtianning.di/crossref/updateitem/lock"
    LOGDIR  = "/nvme/zhangtianning.di/crossref/updateitem/unused_doi"
    os.makedirs(LOCKDIR, exist_ok=True)
    os.makedirs(LOGDIR, exist_ok=True)
    
    #all_paths    = list(Path(ROOTDIR).glob("*.gz"))

    with open(ROOTDIR,'r') as f:
        all_paths = json.load(f)

    redis_host = "localhost"
    redis_port = 6379
    redis_password = ""
    r = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True)

    ES_INDEX="integrate20240311"
    es = Elasticsearch("http://localhost:9200")
    # if es.indices.exists(index=ES_INDEX):
    #     es.indices.delete(index=ES_INDEX)
    # es.indices.refresh()

    
    for file_idx, file_path in enumerate(all_paths):
        with gzip.open(file_path, 'r') as f:
            
            file_name = os.path.split(file_path)[-1].split('.')[0]
            lock_file = os.path.join(LOCKDIR,f'{file_name}.lock')
            try:
                if os.path.exists(lock_file):
                    print(f"{lock_file} exist, continue....")
                    continue
                print(f'create lock file at {lock_file}')
                os.system(f'touch {lock_file}')
                
                json_data = json.load(f)
                Analysis= {'update':0, 'new_add': 0, 'crossref_normal_skip': 0,'escape_by_too_less_information':[], 'escape_by_no_unique_id':[]}
                for i, rowdata in tqdm(enumerate(json_data['items']),total=len(json_data['items'])):
                    if 'alternative-id' in rowdata and len(set(rowdata['alternative-id']))>1:
                        Analysis['crossref_normal_skip']+=1
                        continue
                    newref = Reference.load_from_dict(rowdata)
                    digital_index = get_digital_worth_index_from_unique_id(r,newref.unique_id)
                    if digital_index is None:
                        Analysis['escape_by_no_unique_id'].append(newref.unique_id)
                        continue
                    if not es.exists(index=ES_INDEX, id=digital_index).body:
                        if decide_whether_add_the_ref_into_the_database(newref):
                            body = format_es_paper(newref, vene_name_to_alias)
                            es.index(index=ES_INDEX, id=digital_index, body=body) #<-- you cant use doc
                            Analysis['new_add']+=1
                            
                        else:
                            Analysis['escape_by_too_less_information'].append(newref.unique_id.doi)
                            
                    else:
                        body  = es.get(index=ES_INDEX, id=digital_index)['_source']
                        if 'doc' in body:
                            should_upate = True
                            body = body['doc']
                            es.delete(index=ES_INDEX, id=digital_index)
                            es.index(index=ES_INDEX, id=digital_index, body=body)
                            
                        old_ref = Reference.load_from_dict(body)
                        new_information = old_ref.addtition_information(newref)
                        if len(new_information) > 0:
                            body = body|format_es_paper(new_information,vene_name_to_alias)
                            es.update(index=ES_INDEX, id=digital_index, body={'doc':body}) #<-- you must use doc
                            Analysis['update']+=1
            except:
                if os.path.exists(lock_file):
                    traceback.print_exc()
                    print(f"remove {lock_file} due to fail run")
                    os.remove(lock_file)
                    #exit()

        for k,v in Analysis.items():
            if isinstance(v, list):
                print(f"{k}=>{len(v)}")
            else:
                print(f"{k}=>{v}")

        with open(os.path.join(LOGDIR,f'{file_name}.escape_by_no_unique_id'), 'w') as f:
            for item in Analysis.pop('escape_by_no_unique_id'):
                f.write("%s\n" % item)
        
        with open(os.path.join(LOGDIR,f'{file_name}.escape_by_too_less_information'), 'w') as f:
            for item in Analysis.pop('escape_by_too_less_information'):
                f.write("%s\n" % item)

        with open(os.path.join(LOGDIR,f'{file_name}.Analysis.json'), 'w') as f:
            json.dump(Analysis, f)