

import os
from pathlib import Path
from tqdm.auto import tqdm

ROOTDIR="/nvme/zhangtianning.di/sharefold/whole_arxiv_all_cs/unprocessed_json"

all_raw_files   = [str(t) for t in Path(ROOTDIR).glob('*/reference_*.txt')]
print(f"fail for grobid samples: {len(all_raw_files)}")
[print(t) for t in all_raw_files[0:10]]

for t in all_raw_files:
    os.remove(t)