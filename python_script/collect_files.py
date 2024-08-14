import os
from tqdm.auto import tqdm
ROOT='/home/zhangtianning.di/temp/archive_json'
arxivids = os.listdir(ROOT)
with open('/home/zhangtianning.di/temp/archive_json/all_reference.path.txt','w') as f:
    for arxivid in tqdm(arxivids):
        
        arxivpath     = os.path.join(ROOT,arxivid)
        ReferencePath = os.path.join(ROOT,arxivid,'uparxive', 'Reference')
        ReferenceTxT  = os.path.join(ReferencePath, 'reference.txt' )
        AnystyleJson  = os.path.join(ReferencePath, 'reference.structured.anystyle.jsonl')
        if os.path.exists(AnystyleJson):
            f.write(AnystyleJson.replace('/home/zhangtianning.di/temp/',"")+'\n')
            