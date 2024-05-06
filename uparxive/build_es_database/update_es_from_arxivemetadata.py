
import tqdm
import numpy as np
import os
import sys,json
import redis
from pathlib import Path
from tqdm.auto import tqdm
import gzip,json

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
from utils import *

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(('usage: python3 write_data_into_redis.py index_part num_parts'))
        sys.exit()
    index_part=int(sys.argv[1])
    num_parts =int(sys.argv[2])
    vene_name_to_alias ={} ### you can not get the journal name from the arxive metadata


    ROOTDIR = resource_dir = '/nvme/zhangtianning.di/datasets/whole_arxiv_data/arxiv-metadata-snapshot.20231127.json'
    LOCKDIR = "/nvme/zhangtianning.di/datasets/whole_arxiv_data/updateitem/lock"
    LOGDIR  = "/nvme/zhangtianning.di/datasets/whole_arxiv_data/updateitem/unused_doi"
    os.makedirs(LOCKDIR, exist_ok=True)
    os.makedirs(LOGDIR, exist_ok=True)
    totally_paper_num = 2231517
    divided_nums = np.linspace(0, totally_paper_num, num_parts+1)
    divided_nums = [int(s) for s in divided_nums]
    start_index = divided_nums[index_part]
    end_index   = divided_nums[index_part + 1]
    conflict_doi_that_should_same_but_splited = []
    conflict_doi_that_should_same_but_splited_path = f'/nvme/zhangtianning.di/datasets/whole_arxiv_data/arxiv-metadata_conflict/{index_part}_{num_parts}.json'
    conflict_doi_that_should_same_but_splited_dir  = os.path.dirname(conflict_doi_that_should_same_but_splited_path)
    file_name = f"part_{index_part}_{num_parts}.json"
    os.makedirs(conflict_doi_that_should_same_but_splited_dir, exist_ok=True)

    # Connect to Redis
    redis_host = "localhost"
    redis_port = 6379
    redis_password = ""
    r = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True)
    
    ES_INDEX="integrate20240311"
    es = Elasticsearch("http://localhost:9200")

    with open(resource_dir,'r') as f:
        with tqdm(range(end_index-start_index), desc="Main") as pbar:
            Analysis= {'update':0, 'new_add': 0, 'arxive_normal_skip': 0,'escape_by_exist_and_no_update':0,'escape_by_too_less_information':[], 'escape_by_no_unique_id':[]}  
            for unique_index, line in enumerate(f):
                if unique_index<start_index:continue
                if unique_index>end_index:break
                pbar.update(1)
                data = json.loads(line)
                arxiv_id = data.get('id',None)
                
                if arxiv_id is None:
                    Analysis['arxive_normal_skip']+=1
                    continue
                newref = Reference.load_from_dict(data|{'arxiv':data['id']})
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
                    else:
                        Analysis['escape_by_exist_and_no_update']+=1
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