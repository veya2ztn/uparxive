
import sys
import pathlib
import traceback
from pathlib import Path

module_dir = str(Path(__file__).resolve().parent)

# Add this directory to sys.path
if module_dir not in sys.path:
    sys.path.append(module_dir)
from citation_string_to_reference import get_anystyle_ref_query_dict_v21
from Reference import *
import os,json
from tqdm.auto import tqdm

force_recompute_score = True
if __name__ == '__main__':
    ROOTDIR = sys.argv[1]#"/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_old_quant_ph"
    if os.path.isdir(ROOTDIR):
        alread_processing_file_list = os.listdir(os.path.join(ROOTDIR, 'unprocessed_json'))
    elif os.path.isfile(ROOTDIR):
        with open(ROOTDIR,'r') as f:
            alread_processing_file_list = [line.strip() for line in f]
        assert not os.path.isfile(alread_processing_file_list[0]),"should be arxiv id xxxx.xxxx"
        while True:
            ROOTDIR = os.path.dirname(ROOTDIR)
            if 'unprocessed_json' in os.listdir(ROOTDIR):break
            if len(ROOTDIR) < 4:
                continue
    else:
        raise NotImplementedError

    ROOT = ROOTDIR
    ROOTDIR = os.path.join(ROOT, 'unprocessed_json')
    ArxivIDs= alread_processing_file_list
    Analysys={'Fail.DifferentLength':[]}
    for i,arxiv_id in enumerate(tqdm(ArxivIDs),):
       
        
        paper_fold = os.path.join(ROOTDIR, arxiv_id)
        paper_files= os.listdir(paper_fold)
        
        name_list =  ['reference.structured.anystyle.jsonl',
                      'reference.structured.grobid.jsonl',
                      'reference.grobid.tei.xml',
                     ]
        for name in name_list:
            path = os.path.join(paper_fold,name)
            if os.path.exists(path):
                os.remove(f"{path}")