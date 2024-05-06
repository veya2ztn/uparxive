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

with open("/nvme/zhangtianning.di/semantic_scholar/vene_alias_map.json", 'r') as f:
    vene_name_to_alias = json.load(f)

def generate_es_filter_stream(r,input_file_path):
    """Reads the file through csv.DictReader() and for each row
    yields a single document. This function is passed into the bulk()
    helper to create many documents in sequence.
    """
    with jsonlines.open(input_file_path, mode="r") as f:

        for rowdata in f:
            reference = Reference.load_from_dict(rowdata)
            doc = {
                "_id": get_digital_worth_index_from_unique_id(r, reference.unique_id),
            }|format_es_paper(reference, vene_name_to_alias)
            yield doc


if __name__ == '__main__':
    import logging
    ROOTDIR = "/nvme/zhangtianning.di/semantic_scholar/split"
    LOCKDIR = "/nvme/zhangtianning.di/semantic_scholar/lock"
    LOGDIR  = "/nvme/zhangtianning.di/semantic_scholar/log"
    os.makedirs(LOCKDIR, exist_ok=True)
    os.makedirs(LOGDIR, exist_ok=True)
    all_paths = list(Path("/nvme/zhangtianning.di/semantic_scholar/split").glob('20231201*'))


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
        lock_file = os.path.join(LOCKDIR,f'{file_path.name}.lock')
        if os.path.exists(lock_file):
            print(f"{lock_file} exist, continue....")
            continue
        print(f'create lock file at {lock_file}')
        os.system(f'touch {lock_file}')
        
        actions = generate_es_filter_stream(r,file_path)
        # actions = generate_actions(file_path)
        number_of_lengths = line_count(file_path)
        logpath= os.path.join(LOGDIR,f"failed.{file_path.name}.jsonl")
        with jsonlines.open(logpath, 'w') as error_file:
            progress = tqdm(unit="docs", total=number_of_lengths, desc=f"The progress of the {file_idx+1}/{len(all_paths)} file")
            successes = 0
            for ok, action in streaming_bulk(
                client=es, index=ES_INDEX, actions=actions,
                # chunk_size=16,
            ):
                progress.update(1)
                successes += ok
                if not ok:
                    error_file.writeline(action)

        logging.info(f"Successfully indexed {successes}/{number_of_lengths} documents")
        if number_of_lengths != successes:
            logging.info(f"{number_of_lengths-successes} failed files in error_file{file_path.name}.jsonl")
        else:
            os.remove(logpath)