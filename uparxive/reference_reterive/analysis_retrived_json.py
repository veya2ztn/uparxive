import os
import sys
from tqdm.auto import tqdm
ROOT=sys.argv[1]#"/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_cs"
Analysis = {
    'Missing_Reterive.Citation':[],
    'Done.for.Reterive.Json':[],
    'Fail.for.Build.Reterive.Json':[],
    'Need_Complete_Reterive.Citation':[],
}

for arxiv_id in tqdm(os.listdir(os.path.join(ROOT,'unprocessed_json'))):
    arxiv_id = arxiv_id.strip()
    FILE=os.path.join(ROOT,'unprocessed_json',arxiv_id)
    paper_files = os.listdir(FILE)   
    if 'reference.es_retrived_citation.json' not in paper_files:
        Analysis['Missing_Reterive.Citation'].append(arxiv_id)
        continue 
    if os.path.getsize(os.path.join(FILE, 'reference.txt')) == 0:
        if os.path.exists(os.path.join(FILE, f'{arxiv_id}.retrieved.json')):
            Analysis['Done.for.Reterive.Json'].append(arxiv_id)
        else:
            Analysis['Fail.for.Build.Reterive.Json'].append(arxiv_id)
        continue 
    else:
        Analysis['Need_Complete_Reterive.Citation'].append(arxiv_id)
        continue 
exit()  
    
SAVEROOT = os.path.join(ROOT, 'analysis.final_build_retrived_json')
os.makedirs(SAVEROOT, exist_ok=True)
with open(os.path.join(SAVEROOT,'no_do_reterive'),'w') as f:
    for arxiv_id in Analysis['Missing_Reterive.Citation']:
        f.write(arxiv_id+'\n')
with open(os.path.join(SAVEROOT,'finish_reterive.arxivid_list'),'w') as f:
    for arxiv_id in Analysis['Done.for.Reterive.Json']:
        f.write(arxiv_id+'\n')
with open(os.path.join(SAVEROOT,'finish_reterive.filelist'),'w') as f:
    for arxiv_id in Analysis['Done.for.Reterive.Json']:
        f.write(os.path.join(ROOT,'unprocessed_json',arxiv_id, f'{arxiv_id}.retrieved.json')+'\n')
with open(os.path.join(SAVEROOT,'fail_to_build_retrived_json'),'w') as f:
    for arxiv_id in Analysis['Fail.for.Build.Reterive.Json']:
        f.write(arxiv_id+'\n')
with open(os.path.join(SAVEROOT,'need_complete_reterive'),'w') as f:
    for arxiv_id in Analysis['Need_Complete_Reterive.Citation']:
        f.write(arxiv_id+'\n')
for k, v in Analysis.items():
    print(f"{k}: {len(v)}")          



## rclone --progress --files-from-raw /nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_old_quant_ph/analysis.grobid_reference/missing_reterive_citation.filelist --no-traverse copy /nas/zhangtianning.di/datasets/arxiv/whole_arxiv_old_quant_ph/
## rclone copy --include "reference.structured.jsonl" --progress /nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_old_quant_ph/unprocessed_json/ /nas/zhangtianning.di/datasets/arxiv/whole_arxiv_old_quant_ph/unprocessed_json/