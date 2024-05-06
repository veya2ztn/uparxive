import redis


# Function to add an alias with a unique name to the Redis store
def add_alias_with_unique_name(r, alias_type, alias_value, index):
    unique_name = f"{alias_type}:{alias_value}"
    # Set the unique name with the index
    r.set(unique_name, index)
    r.sadd(f"index_{index}", unique_name)
# Function to retrieve the index for a given unique name
def get_index_by_unique_name(r,alias_type, alias_value):
    unique_name = f"{alias_type}:{alias_value}"
    # Get the index associated with the unique name
    return r.get(unique_name)
import tqdm
import numpy as np
import os
import sys,json
if __name__ == '__main__':
    if len(sys.argv) != 3:
        print(('usage: python3 write_data_into_redis.py index_part num_parts'))
        sys.exit()
    index_part=int(sys.argv[1])
    num_parts =int(sys.argv[2])
    totally_paper_num = 241690796
    divided_nums = np.linspace(0, totally_paper_num, num_parts+1)
    divided_nums = [int(s) for s in divided_nums]
    start_index = divided_nums[index_part]
    end_index   = divided_nums[index_part + 1]
    # Connect to Redis
    redis_host = "localhost"
    redis_port = 6379
    redis_password = ""
    r = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True)

    with open("/nvme/zhangtianning.di/openalex/paper_identity.jsonl",'r') as f:
        with tqdm.tqdm(range(end_index-start_index), desc="Main") as pbar:
            for unique_index, line in enumerate(f):
                if unique_index<start_index:continue
                if unique_index>end_index:break
                pbar.update(1)
                identity_set = json.loads(line)
                unique_index = str(unique_index)
                for alias_type, alias_value in identity_set.items():
                    add_alias_with_unique_name(r,alias_type, alias_value, unique_index)