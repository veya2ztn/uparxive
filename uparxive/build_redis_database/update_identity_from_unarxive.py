
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
    
    resource_dir = "/nvme/zhangtianning.di/datasets/unarxive/whole_filelist.json"
    with open(resource_dir,'r') as f:
        resource_files= json.load(f)
    
    totally_paper_num = len(resource_files)
    divided_nums = np.linspace(0, totally_paper_num, num_parts+1)
    divided_nums = [int(s) for s in divided_nums]
    start_index = divided_nums[index_part]
    end_index   = divided_nums[index_part + 1]
    # Connect to Redis
    redis_host = "localhost"
    redis_port = 6379
    redis_password = ""
    r = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True)
    
    for filename in tqdm(resource_files[start_index:end_index], position=1, leave=False):
        Prefix_Code = str(filename).split('/')[-1].replace('arXiv_src_','').replace('.jsonl','')
        conflict_doi_that_should_same_but_splited = []
        conflict_doi_that_should_same_but_splited_path = str(filename).replace('unarxive','unarxive_Conflict').replace('.jsonl','.json')
        conflict_doi_that_should_same_but_splited_dir  = os.path.dirname(conflict_doi_that_should_same_but_splited_path)
        os.makedirs(conflict_doi_that_should_same_but_splited_dir, exist_ok=True)
        if os.path.exists(conflict_doi_that_should_same_but_splited_path):continue
        with open(filename, 'r') as f:
            length = len(f.readlines())
        with open(filename, 'r') as f:
            for slot, line in tqdm(enumerate(f),total=length, position=2, leave=False):
                data = json.loads(line)
                if 'bib_entries' in data:
                    for key, val in data['bib_entries'].items():
                        if 'ids' not in val:continue
                        paper = UniqueID.from_dict(val['ids'])
                        if paper.is_nan():continue
                        doi_and_indexes= []
                        for alias_type,alias_value in paper.to_dict().items():
                            if alias_type == 'semopenalex':continue
                            if 'openalex' in alias_type:alias_value = alias_value.replace('w','W')
                            doi_and_indexes.append([alias_type, alias_value, get_index_by_alias(r,alias_type, alias_value)])
                        the_valid_indexes= list(set([index for alias_type, alias_value, index in doi_and_indexes if index is not None]))
                        if len(the_valid_indexes)>1:
                            multirecord_doi = [[alias_type, alias_value] for alias_type, alias_value, index in doi_and_indexes if index is not None]
                            conflict_doi_that_should_same_but_splited.append(multirecord_doi)
                            continue
                        if len(the_valid_indexes)==0:
                            the_record_index = f"UA.{Prefix_Code}.{slot}"
                            for alias_type, alias_value, index in doi_and_indexes:
                                unique_name = format_alias(alias_type, alias_value)
                                add_alias_with_unique_name(r,alias_type, alias_value, the_record_index)
                        else:
                            the_record_index = the_valid_indexes[0]
                            
                            old_set = get_alias_by_index(r,the_record_index)
                            #print(the_valid_indexes)
                            #print(old_set)
                            for alias_type, alias_value, index in doi_and_indexes:
                                unique_name = format_alias(alias_type, alias_value)
                                if unique_name in old_set:continue
                                add_alias_with_unique_name(r,alias_type, alias_value, the_record_index)
        with open(conflict_doi_that_should_same_but_splited_path, 'w') as f:
            json.dump(conflict_doi_that_should_same_but_splited, f)