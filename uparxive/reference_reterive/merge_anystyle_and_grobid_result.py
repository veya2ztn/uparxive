
import re
from lxml import etree
from typing import List, Optional

from uparxive.batch_run_utils import BatchModeConfig, dataclass
import os
import os
import sys
from tqdm.auto import tqdm
import numpy as np
import traceback,json
import argparse, logging

@dataclass 
class MergeStructureConfig(BatchModeConfig):
    redo : bool = False
    verbose : bool = False
    task_name = 'merge_structure'

def process_one_path(ROOTPATH, args:MergeStructureConfig):
    arxiv_id = ROOTPATH.rstrip('/').split('/')[-3]

    if not os.path.exists(ROOTPATH):
        return arxiv_id, 'not_exist'
    anystylepath   = os.path.join(ROOTPATH,'reference.structured.anystyle.jsonl')
    grobid_path    = os.path.join(ROOTPATH,'reference.structured.grobid.jsonl')
    targetpath     = os.path.join(ROOTPATH,'reference.structured.jsonl')
    reference_path = os.path.join(ROOTPATH,'reference.txt')
    if not os.path.exists(reference_path):
        return arxiv_id, 'no_reference'
    if os.path.getsize(reference_path) == 0:
        return arxiv_id, 'empty_reference'
    if os.path.exists(targetpath) and not args.redo:
        return arxiv_id, 'already_exist'
    anystyle_lines = None
    if os.path.exists(anystylepath):
        try:
            with open(anystylepath,'r') as f:
                anystyle_lines = json.load(f)
        except:
            return arxiv_id, 'fail_load_anystyle'
    grobid_lines = None
    if os.path.exists(grobid_path):
        try:
            with open(grobid_path,'r') as f:
                grobid_lines = json.load(f)
        except:
            return arxiv_id, 'fail_load_grobid'
    if anystyle_lines is None and grobid_lines is None:
        return arxiv_id, 'no_file'
    
    if anystyle_lines is not None and grobid_lines is not None:
        with open(reference_path,'r') as f:
            real_lines = [t.strip() for t in f.readlines()]
        if len(anystyle_lines) != len(grobid_lines):
            tqdm.write(f"why the two files have different length {len(anystyle_lines)} {len(grobid_lines)} it should be {len(real_lines)}. See \n ====> {ROOTPATH}")
            return arxiv_id,'different_length'
                        

    length = len(anystyle_lines) if anystyle_lines is not None else len(grobid_lines)
    new_lines = []
    for line_id in range(length):
        line_pool = {}
        if anystyle_lines is not None:
            line_pool['anystyle'] = anystyle_lines[line_id]
        if grobid_lines is not None:
            line_pool['grobid'] = grobid_lines[line_id]
        new_lines.append(line_pool)
    
    with open(targetpath,'w') as f:
        json.dump(new_lines,f)
    return arxiv_id, 'pass'

if __name__ == '__main__':
    # import sys
    # assert len(sys.argv)==2
    # INPUTPATH =sys.argv[1]
    # assert "reference.grobid.tei.xml "in INPUTPATH
    # bibliography_list = obtain_reference_list(INPUTPATH)
    # for i,ref in enumerate(bibliography_list):
    #     print(f"Reference {i+1}")
    #     print(get_print_namespace_tree(ref))
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--root_path", type=str)
    parser.add_argument("--index_part", type=int, default=0)
    parser.add_argument('--num_parts', type=int, default=1)
    parser.add_argument('--mode', type=str, default='normal')
    args = parser.parse_args()
    
    filelistpath = args.root_path
    analysis = {}
    if os.path.isdir(filelistpath):
        if filelistpath.endswith('archive_json'):
            root_path = filelistpath
            while not root_path.endswith('whole_arxiv_all_files'):
                root_path = os.path.dirname(root_path)
                assert root_path != '/'
            root_path = os.path.join(root_path,'analysis.merge_anystyle_grobid')
            print(root_path)
            os.makedirs(root_path,exist_ok=True)
            ROOTPATH = filelistpath
            all_file_list = os.listdir(ROOTPATH)
            all_file_list = [os.path.join(ROOTPATH, DIRNAME) for DIRNAME in all_file_list]
        else:
            all_file_list = [filelistpath]
    elif os.path.isfile(filelistpath):
        root_path = filelistpath
        while not root_path.endswith('whole_arxiv_all_files'):
            root_path = os.path.dirname(root_path)
            assert root_path != '/'
        root_path = os.path.join(root_path,'analysis.merge_anystyle_grobid')
        #root_path= os.path.join(os.path.dirname(os.path.dirname(filelistpath)),'analysis.tex_to_xml')
        print(root_path)
        os.makedirs(root_path,exist_ok=True)
        with open(filelistpath,'r') as f:
            all_file_list = [t.strip() for t in f.readlines()]
    
    #all_file_list = [DIR.replace('unprocessed_tex','unprocessed_xml') for DIR in all_file_list if os.path.getsize(DIR) > 0]
    
    index_part= args.index_part
    num_parts = args.num_parts 
    totally_paper_num = len(all_file_list)
    logging.info(totally_paper_num)
    if totally_paper_num > 1:
        divided_nums = np.linspace(0, totally_paper_num, num_parts+1)
        divided_nums = [int(s) for s in divided_nums]
        start_index = divided_nums[index_part]
        end_index   = divided_nums[index_part + 1]
    else:
        start_index = 0
        end_index   = 1
        verbose = True

    all_file_list = all_file_list[start_index: end_index]
        
    #alread_processing_file_list = ['1303.3256']
    fail_filenames=[]
    for i,ROOTPATH in enumerate(tqdm(all_file_list)):
        if not os.path.exists(ROOTPATH):
            analysis['not_exist'] = analysis.get('not_exist',[]) + [ROOTPATH]
            continue
        anystylepath   = os.path.join(ROOTPATH,'reference.structured.anystyle.jsonl')
        grobid_path    = os.path.join(ROOTPATH,'reference.structured.grobid.jsonl')
        targetpath     = os.path.join(ROOTPATH,'reference.structured.jsonl')
        reference_path = os.path.join(ROOTPATH,'reference.txt')
        if not os.path.exists(reference_path):
            analysis['no_reference'] = analysis.get('no_reference',[]) + [ROOTPATH]
            continue
        if os.path.getsize(reference_path) == 0:
            analysis['empty_reference'] = analysis.get('empty_reference',[]) + [ROOTPATH]
            continue
        if os.path.exists(targetpath):
            analysis['already_exist'] = analysis.get('already_exist',[]) + [ROOTPATH]
            continue
        anystyle_lines = None
        if os.path.exists(anystylepath):
            try:
                with open(anystylepath,'r') as f:
                    anystyle_lines = json.load(f)
            except:
                analysis['fail_load_anystyle'] = analysis.get('fail_load_anystyle',[]) + [ROOTPATH]
                continue
        grobid_lines = None
        if os.path.exists(grobid_path):
            try:
                with open(grobid_path,'r') as f:
                    grobid_lines = json.load(f)
            except:
                analysis['fail_load_grobid'] = analysis.get('fail_load_grobid',[]) + [ROOTPATH]
                continue
        if anystyle_lines is None and grobid_lines is None:
            tqdm.write(f"no file here, skip {ROOTPATH}")
            continue
        
        if anystyle_lines is not None and grobid_lines is not None:
            
   
            with open(reference_path,'r') as f:
                real_lines = [t.strip() for t in f.readlines()]
 
            if len(anystyle_lines) != len(grobid_lines):
                tqdm.write(f"why the two files have different length {len(anystyle_lines)} {len(grobid_lines)} it should be {len(real_lines)}. See \n ====> {ROOTPATH}")
                analysis['different_length'] = analysis.get('different_length',[]) + [ROOTPATH]
                continue
                           

        length = len(anystyle_lines) if anystyle_lines is not None else len(grobid_lines)
        new_lines = []
        for line_id in range(length):
            line_pool = {}
            if anystyle_lines is not None:
                line_pool['anystyle'] = anystyle_lines[line_id]
            if grobid_lines is not None:
                line_pool['grobid'] = grobid_lines[line_id]
            new_lines.append(line_pool)
        
        with open(targetpath,'w') as f:
            json.dump(new_lines,f)

    root_path = '/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/analysis/parse_reference/merge_anystyle_grobid/'
    os.makedirs(root_path,exist_ok=True)
    if num_parts > 1:
        for key, val in analysis.items():
            print(f"{key}=>{len(val)}")
            fold = os.path.join(root_path,f"{key.lower()}.filelist.split")
            os.makedirs(fold, exist_ok=True)
            with open(os.path.join(fold,f"{start_index}-{end_index}"), 'w') as f:
                for line in (val):
                    f.write(line+'\n')
    else:
        #print(analysis)
        for key, val in analysis.items():
            print(f"{key}=>{len(val)}")
            with open(os.path.join(root_path,f"{key.lower()}.filelist"), 'w') as f:
                for line in set(val):
                    f.write(line+'\n')