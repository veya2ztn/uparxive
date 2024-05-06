
import tqdm
import numpy as np
import os
import sys,json
import redis
from pathlib import Path
from tqdm.auto import tqdm
import gzip,json

module_dir = str(Path(__file__).resolve().parent.parent)
# Add this directory to sys.path
if module_dir not in sys.path:
    sys.path.append(module_dir)
from utils import *
from reference_reterive.Reference import UniqueID
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(('usage: python3 write_data_into_redis.py index_part num_parts'))
        sys.exit()
    index_part=int(sys.argv[1])
    num_parts =int(sys.argv[2])
    
    resource_dir = '/nvme/zhangtianning.di/datasets/whole_arxiv_data/arxiv-metadata-snapshot.20231127.json'
    
    totally_paper_num = 2231517
    divided_nums = np.linspace(0, totally_paper_num, num_parts+1)
    divided_nums = [int(s) for s in divided_nums]
    start_index = divided_nums[index_part]
    end_index   = divided_nums[index_part + 1]
    conflict_doi_that_should_same_but_splited = []
    conflict_doi_that_should_same_but_splited_path = f'/nvme/zhangtianning.di/datasets/whole_arxiv_data/arxiv-metadata_conflict/{index_part}_{num_parts}.json'
    conflict_doi_that_should_same_but_splited_dir  = os.path.dirname(conflict_doi_that_should_same_but_splited_path)
    os.makedirs(conflict_doi_that_should_same_but_splited_dir, exist_ok=True)

    # Connect to Redis
    redis_host = "localhost"
    redis_port = 6379
    redis_password = ""
    r = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True)
    Analysis= {'conflict_doi_then_we_pass':0, 
               'add_new_alias':[],
               'update_old_alias':0,
               'already_has_alias':0}  
            
    with open(resource_dir,'r') as f:
        with tqdm(range(end_index-start_index), desc="Main") as pbar:
            
            for unique_index, line in enumerate(f):
                if unique_index<start_index:continue
                if unique_index>end_index:break
                pbar.update(1)
                identity_set = json.loads(line)
                unique_index = str(unique_index)
                Prefix_Code = f'AX'
                #if os.path.exists(conflict_doi_that_should_same_but_splited_path):continue
                data = json.loads(line)
                arxiv_id = data.get('id',None)
                doi = data.get('doi',None)
                #if doi is None:continue  ### <---- we still need to add the arxiv id even the doi is not provided
                if arxiv_id is None:continue

                paper = UniqueID.from_dict({'arxiv':arxiv_id, 'doi':doi})
                if paper.is_nan():continue
                doi_and_indexes= []
                for alias_type,alias_value in paper.to_dict().items():
                    doi_and_indexes.append([alias_type, alias_value, get_index_by_alias(r,alias_type, alias_value)])
                the_valid_indexes= list(set([index for alias_type, alias_value, index in doi_and_indexes if index is not None]))
                if len(the_valid_indexes)>1:
                    multirecord_doi = [[alias_type, alias_value] for alias_type, alias_value, index in doi_and_indexes if index is not None]
                    conflict_doi_that_should_same_but_splited.append(multirecord_doi)
                    Analysis['conflict_doi_then_we_pass']+=1
                    continue
                if len(the_valid_indexes)==0:
                    the_record_index = f"{Prefix_Code}.{unique_index}"
                    for alias_type, alias_value, index in doi_and_indexes:
                        unique_name = format_alias(alias_type, alias_value)
                        add_alias_with_unique_name(r,alias_type, alias_value, the_record_index)
                    Analysis['add_new_alias'].append(the_record_index)
                else:
                    the_record_index = the_valid_indexes[0]
                    old_set = get_alias_by_index(r,the_record_index)
                    #print(the_valid_indexes)
                    #print(old_set)
                    updateQ=False
                    for alias_type, alias_value, index in doi_and_indexes:
                        unique_name = format_alias(alias_type, alias_value)
                        if unique_name in old_set:continue
                        add_alias_with_unique_name(r,alias_type, alias_value, the_record_index)
                        updateQ=True
                    if updateQ:
                        Analysis['update_old_alias']+=1
                    else:
                        Analysis['already_has_alias']+=1
        for k,v in Analysis.items():
            if isinstance(v, list):
                print(f"{k}=>{len(v)}")
            else:
                print(f"{k}=>{v}")
        with open(conflict_doi_that_should_same_but_splited_path, 'w') as f:
            json.dump(conflict_doi_that_should_same_but_splited, f)

        with open(conflict_doi_that_should_same_but_splited_path.replace('.json','.addpart.json'), 'w') as f:
            for line in Analysis['add_new_alias']:
                f.write(line+'\n')