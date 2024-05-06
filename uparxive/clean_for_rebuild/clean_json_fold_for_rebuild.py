import os,re
from pathlib import Path
from tqdm.auto import tqdm
import sys
def get_directory_before_analysis(path):
    # Use a regular expression to match the path up to "analysis."
    match = re.search(r'^(.*/)(analysis\.[^/]*)/', path)
    if match:
        # Return the directory part of the path, excluding the "analysis.xxxxx" part
        return match.group(1).rstrip('/')
    else:
        # If no "analysis.xxxxx" part is found, return None or the original path
        return None
PATHLIST_FILEPATH=sys.argv[1] #"/nvme/zhangtianning.di/datasets/LLM/arxiv/whole_arxiv_all_cs/analysis.tex_to_xml/tex_to_xml.pass.badbib/tex_to_xml.pass.pathlist"
ROOT= get_directory_before_analysis(PATHLIST_FILEPATH)

if PATHLIST_FILEPATH.split('.')[-1] in ['filelist','pathlist']:
    with open(PATHLIST_FILEPATH,'r') as f:
        arxiv_id_list = [os.path.basename(os.path.dirname(arxiv_id.strip())) for arxiv_id in f]
else:
    with open(PATHLIST_FILEPATH,'r') as f:
        arxiv_id_list = [arxiv_id.strip() for arxiv_id in f]
print(f"we will delete {len(arxiv_id_list)} json folds")
print(arxiv_id_list[0])
assert "/" not in arxiv_id_list[0]
for arxiv_id in tqdm(arxiv_id_list):
    xml_fold = os.path.join(ROOT,"unprocessed_json",arxiv_id)
    os.system(f'rm -r {xml_fold}')
    