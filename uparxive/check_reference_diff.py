

import os
from pathlib import Path
ROOT = '/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_cs_new'
reference_filelist = list(Path(os.path.join(ROOT,"unprocessed_json")).glob("*/reference.txt"))
num_new_to_exist = 0
num_same_to_exist= 0
num_diff_to_exist_list = []
for path in reference_filelist:
    path_old = str(path).replace('whole_arxiv_all_cs_new','whole_arxiv_all_cs')
    if not os.path.exists(path_old) or os.path.getsize(path_old) ==0:
        num_new_to_exist+=1
        continue
    if os.path.getsize(path) == os.path.getsize(path_old):
        num_same_to_exist+=1
        continue
    with open(path_old,'r') as f:
        old_content = [line.strip() for line in f]
    with open(path,'r') as f:
        new_content = [line.strip() for line in f]
    if old_content != new_content:
        num_diff_to_exist_list.append(path)
        continue
    sameQ = True
    for line1, line2 in zip(old_content,new_content):
        if line1 != line2:
            sameQ = False
            break
    if not sameQ:
        num_diff_to_exist_list.append(path)
    else:
        num_same_to_exist+=1
print(f"num_new_to_exist:{num_new_to_exist}")
print(f"num_same_to_exist:{num_same_to_exist}")
print(f"num_diff_to_exist_list:{len(num_diff_to_exist_list)}")
with open(f'diff_to_exist_list.txt','w') as f:
    for line in num_diff_to_exist_list:
        f.write(str(line)+'\n')

