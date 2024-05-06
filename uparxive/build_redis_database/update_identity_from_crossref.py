
import tqdm
import numpy as np
import os
import sys,json
import redis
from pathlib import Path
from tqdm.auto import tqdm
import gzip,json
module_dir = str(Path(__file__).resolve().parent)
# Add this directory to sys.path
if module_dir not in sys.path:
    sys.path.append(module_dir)
from utils import *

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(('usage: python3 write_data_into_redis.py index_part num_parts'))
        sys.exit()
    index_part=int(sys.argv[1])
    num_parts =int(sys.argv[2])
    
    resource_dir = "/nvme/zhangtianning.di/crossref/crossref.filelist.json"
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
        Prefix_Code = str(filename).split('/')[-1].replace('.json.gz','')
        conflict_doi_that_should_same_but_splited = []
        conflict_doi_that_should_same_but_splited_path = str(filename).replace('CrossrefData','CrossrefData_Conflict').replace('.json.gz','.json')
        if os.path.exists(conflict_doi_that_should_same_but_splited_path):continue
        with gzip.open(filename, 'r') as f:
            json_data = json.load(f)
            for slot, t in tqdm(enumerate(json_data['items']),total=len(json_data['items']), position=2, leave=False):
                if 'alternative-id' in t and len(set(t['alternative-id']))>1:
                    continue
                    ### it is quite chos for the alternative-id term in crossref. Lets ignore
                    alternative_pool = [l.lower() for l in t['alternative-id']]
                    primiry_doi      = t['DOI'].lower()
                    alternative_doi  = [primiry_doi.replace(alternative_pool[0], sss) for sss in alternative_pool[1:]]
                    alternative_doi  = [primiry_doi] + alternative_doi 
                    doi_and_indexes  = [[doi,get_index_by_alias(r,'doi', doi)] for doi in alternative_doi]
                    the_valid_indexes= [index for doi, index in doi_and_indexes if index is not None]
                    if len(the_valid_indexes)>1:
                        multirecord_doi = [doi for doi, index in doi_and_indexes if index is not None]
                        conflict_doi_that_should_same_but_splited.append(multirecord_doi)
                        continue
                    if len(the_valid_indexes)==0:
                        the_record_index = f"CR.{Prefix_Code}.{slot}"
                    else:
                        the_record_index = the_valid_indexes[0]
                        
                    for doi, index in doi_and_indexes:
                        if index is not None:continue
                        print(slot,'doi', doi, the_record_index)
                        #add_alias_with_unique_name(r,'doi', doi, the_record_index)
                else:
                    if 'DOI' not in t: continue
                    doi  = t['DOI']
                    the_record_index = get_index_by_alias(r,'doi', doi)
                    if the_record_index is not None:
                        continue
                    else:
                        the_record_index = f"CR.{Prefix_Code}.{slot}"
                        add_alias_with_unique_name(r,'doi', doi, the_record_index)
        # with open(conflict_doi_that_should_same_but_splited_path, 'w') as f:
        #     json.dump(conflict_doi_that_should_same_but_splited, f)