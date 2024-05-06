import os
import sys
from tqdm.auto import tqdm
ROOT=sys.argv[1]#"/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_cs"
Analysis = {
    'Empty_Reference.TXT':[],
    'Missing_Reference.TXT':[],
    'Missing_Grobid.XML':[],
    'Missing_Structured.JSON':[],
    'Missing_Reterive.Citation':[],
    'AllDone.Citation':[],
}

for arxiv_id in tqdm(os.listdir(os.path.join(ROOT,'unprocessed_json'))):
    
    arxiv_id = arxiv_id.strip()
    FILE=os.path.join(ROOT,'unprocessed_json',arxiv_id)
    paper_files = os.listdir(FILE)
    if 'reference.txt' not in paper_files:
        Analysis['Missing_Reference.TXT'].append(arxiv_id)
        continue
    elif os.path.getsize(os.path.join(ROOT,'unprocessed_json',arxiv_id,'reference.txt'))==0:
        Analysis['Empty_Reference.TXT'].append(arxiv_id)
        continue
    # if 'reference.grobid.tei.xml' not in paper_files:
    #     Analysis['Missing_Grobid.XML'].append(arxiv_id)
    #     continue
    if 'reference.structured.jsonl' not in paper_files:
        if 'reference.grobid.tei.xml' in paper_files:
            os.remove(os.path.join(FILE,'reference.grobid.tei.xml'))
        Analysis['Missing_Structured.JSON'].append(arxiv_id)
        continue
    
    if 'reference.es_retrived_citation.json' not in paper_files:
        Analysis['Missing_Reterive.Citation'].append(arxiv_id)
        continue  
    Analysis['AllDone.Citation'].append(arxiv_id)
    
SAVEROOT = os.path.join(ROOT, 'analysis.grobid_reference')
os.makedirs(SAVEROOT, exist_ok=True)
with open(os.path.join(SAVEROOT,'ready_for_grobid.filelist'),'w') as f:
    for arxiv_id in Analysis['Missing_Grobid.XML']:
        f.write(arxiv_id+'\n')
with open(os.path.join(SAVEROOT,'missing_reference.filelist'),'w') as f:
    for arxiv_id in Analysis['Missing_Reference.TXT']:
        f.write(arxiv_id+'\n')
with open(os.path.join(SAVEROOT,'empty_reference.filelist'),'w') as f:
    for arxiv_id in Analysis['Empty_Reference.TXT']:
        f.write(arxiv_id+'\n')
with open(os.path.join(SAVEROOT,'missing_structured.filelist'),'w') as f:
    for arxiv_id in Analysis['Missing_Structured.JSON']:
        f.write(arxiv_id+'\n')

with open(os.path.join(SAVEROOT,'missing_reterive_citation.filelist'),'w') as f:
    for arxiv_id in Analysis['Missing_Reterive.Citation']:
        f.write(os.path.join(ROOT,'unprocessed_json',arxiv_id,'reference.structured.jsonl')+'\n')
with open(os.path.join(SAVEROOT,'missing_reterive_citation.filelist.remain'),'w') as f:
    for arxiv_id in Analysis['Missing_Reterive.Citation']:
        f.write(arxiv_id+'\n')
with open(os.path.join(SAVEROOT,'all_done_citation.filelist'),'w') as f:
    for arxiv_id in Analysis['AllDone.Citation']:
        f.write(arxiv_id+'\n')
for k, v in Analysis.items():
    print(f"{k}: {len(v)}")

## rclone --progress --files-from-raw /nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_old_quant_ph/analysis.grobid_reference/missing_reterive_citation.filelist --no-traverse copy /nas/zhangtianning.di/datasets/arxiv/whole_arxiv_old_quant_ph/
## rclone copy --include "reference.structured.jsonl" --progress /nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_old_quant_ph/unprocessed_json/ /nas/zhangtianning.di/datasets/arxiv/whole_arxiv_old_quant_ph/unprocessed_json/