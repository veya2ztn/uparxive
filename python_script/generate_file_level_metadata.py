import numpy as np
from tqdm.auto import tqdm
import sys,json,re

index_part=int(sys.argv[1])
num_parts =int(sys.argv[2])

totally_paper_num = 2450893
divided_nums = np.linspace(0, totally_paper_num, num_parts+1)
divided_nums = [int(s) for s in divided_nums]
start_index = divided_nums[index_part]
end_index   = divided_nums[index_part + 1]
resource_dir = "/nvme/zhangtianning/datasets/whole_arxiv_data/arxiv_metadata_snapshot/20240407/arxiv-metadata-snapshot.json"
import os
with open(resource_dir,'r') as f:
    with tqdm(range(end_index-start_index), desc="Main") as pbar:
        for unique_index, line in enumerate(f):
            if unique_index<start_index:continue
            if unique_index>end_index:break
            pbar.update(1)
            data = json.loads(line)
            arxiv_id = data['id'].replace('/','_')
            match = re.search(r"\d{4}", arxiv_id)
            if match:
                # Print the matched pattern
                date = match.group()
            title = data['title']
            abstract = data['abstract']
            ROOT = '/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/metadatas'
            metadatadir = os.path.join(ROOT,date,arxiv_id)
            os.makedirs(metadatadir, exist_ok=True)
            metadatapath= os.path.join(metadatadir, 'metadata.json')    
            with open(metadatapath, 'w') as f:
                json.dump({
                    'title':title,
                    'abstract':abstract
                },f)