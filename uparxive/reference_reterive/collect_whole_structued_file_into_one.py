
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
    mode = sys.argv[2]  if len(sys.argv) >= 3 else 'normal'  
    ArxivIDs= alread_processing_file_list
    Analysys={'Fail.DifferentLength':[]}
    for i,arxiv_id in enumerate(tqdm(ArxivIDs),):
       
        
        paper_fold = os.path.join(ROOTDIR, arxiv_id)
        paper_files= os.listdir(paper_fold)
        
        reference_keys    = read_linefile(os.path.join(paper_fold,'reference.keys'))
        reference_txts    = read_linefile(os.path.join(paper_fold,'reference.txt'))
        reference_structured_anystyle = [None]*len(reference_txts)
        reference_structured_grobid   = [None]*len(reference_txts)
        if len(reference_keys) != len(reference_txts):
            Analysys['Fail.DifferentLength'].append(arxiv_id)
            continue
        if 'reference.structured.anystyle.jsonl' in paper_files:
            reference_structured_anystyle = read_jsonl(os.path.join(paper_fold, 'reference.structured.anystyle.jsonl'))
            if len(reference_structured_anystyle) != len(reference_txts):
                Analysys['Fail.DifferentLength'].append(arxiv_id)
                continue
        if 'reference.structured.grobid.jsonl' not in paper_files:
            reference_structured_grobid   = read_jsonl(os.path.join(paper_fold, 'reference.structured.grobid.jsonl'))
            if len(reference_structured_grobid) != len(reference_txts):
                Analysys['Fail.DifferentLength'].append(arxiv_id)
                continue
        reference_structured = []
        for anystyle, grobid in zip(reference_structured_anystyle, reference_structured_grobid):
            reference_structured.append({'anystyle': anystyle, 'grobid': None})
        save_jsonl(os.path.join(paper_fold, 'reference.structured.jsonl'),reference_structured )
    for k,v in Analysys.items():
        if isinstance(v, list):
            print(f"{k}=>{len(v)}")
        else:
            print(f"{k}=>{v}")
    if mode=='clean_after_finish':
        name_list =  ['reference.structured.anystyle.jsonl',
                      'reference.structured.grobid.jsonl',
                      'reference.grobid.tei.xml',
                     ]
        for name in name_list:
            path = os.path.join(paper_fold,name)
            if os.path.exists(path):
                os.remove(f"{path}")
    

