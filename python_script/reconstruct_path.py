import os,shutil
from tqdm.auto import tqdm
from pathlib import Path
import re
import sys
ROOT=sys.argv[1]#"archive_xml"

arxivids= os.listdir(ROOT)
no_source_xml = []
for arxivid in tqdm(arxivids):
    if len(arxivid)==4:continue
    assert len(arxivid)>4, f"arxivid is too short {arxivid}"
    arxivpath     = os.path.join(ROOT, arxivid)
    match = re.search(r"\d{4}", arxivid)
    if match:
        # Print the matched pattern
        date = match.group()
    else:
        raise NotImplementedError(f"which is your arxivid date??? ==? {arxivid}")
    new_root = os.path.join(ROOT, date)
    new_path = os.path.join(ROOT, date,arxivid)
    os.makedirs(new_root, exist_ok=True)
    shutil.move(arxivpath, new_path)