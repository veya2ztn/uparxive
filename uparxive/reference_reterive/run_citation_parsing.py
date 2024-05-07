import subprocess
import sys 
import threading
import queue
import logging
from uparxive.batch_run_utils import BatchModeConfig, dataclass
from uparxive.utils import isHardTexFile
from tqdm.auto import tqdm

from grobid_client.grobid_client import GrobidClient
client = GrobidClient(config_path="/home/zhangtianning.di/projects/unique_data_build/uparxive/reference_reterive/grobid_config.json")

@dataclass 
class ParseCitationConfig(BatchModeConfig):
    verbose: bool = False
    task_name = 'parse_citation'
    mode: str = 'anystyle'


import os
from time import sleep
import time
from pathlib import Path
def process_file(file_dir,args):
    verbose = args.verbose
    redo = args.redo
    file_dir = file_dir.rstrip('/')
    JSONROOT = os.path.dirname(file_dir)
    basename = os.path.basename(file_dir)
    arxivid  = file_dir.split('/')[-3]
    ReferencePath = os.path.join(file_dir,'reference.txt')
    if not os.path.exists(ReferencePath):
        tqdm.write(f"WARNING: why the reference file for {arxivid} is missing?")
        return arxivid, 'NoFile'
    if os.path.getsize(ReferencePath) == 0:
        #tqdm.write(f"WARNING: why the reference file for {arxivid} is empty?")
        return arxivid, 'EmptyFile'
    
    if args.mode == 'grobid':
        

        grobid_output = os.path.join(file_dir, "reference.grobid.tei.xml") 
        #print(grobid_output)
        grobid_result = 0
        if not os.path.exists(grobid_output) or redo:
            #failed_path = list(Path(file_dir).glob("reference_*"))
            # if len(failed_path)>0:
            #     print(file_dir)
            #     raise
            client.process("processCitationList", file_dir)
            timeout = 10
            starttime = time.time()
            process = subprocess.Popen(
                        ["grobid_client","--input", file_dir,"processCitationList"],  # Replace with actual command and options
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True
                    )
            process.wait()
            
            grobid_result = "Fail" if grobid_result != 0 else "Pass"
            return arxivid, grobid_result
        else:
            return arxivid, 'Skip'
    elif args.mode == 'anystyle':
        anystyle_output= os.path.join(file_dir, "reference.structured.anystyle.jsonl") 
        anystyle_result= 0
        if not os.path.exists(anystyle_output) or redo:

            process = subprocess.Popen(
                ["anystyle","-f","json", "parse", ReferencePath ],  # Replace with actual command and options
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            lines = []
            while True:
                line = process.stdout.readline()
                if not line:  # If readline returns an empty bytes object, the process has finished
                    break
                lines.append(line)
                # Check exit status
            process.wait()
            with open(anystyle_output,'w') as f:
                for line in lines:
                    f.write(line)
            anystyle_result = process.returncode
        anystyle_result = "Fail" if anystyle_result != 0 else "Pass"
        
        # status = f"deal with {arxivid} with grobid {grobid_result} and anystyle {anystyle_result}"
        # if anystyle_result == "Fail" or grobid_result == "Fail":
        #     tqdm.write(status)

        return arxivid,anystyle_result

def process_file_wrapper(args):
    arxiv_path, args = args
    ##### some case it will Connection reset by peer
    ##### lets wait 10s and auto start 
    while True:
        try:
            return process_file(arxiv_path, args)
        except Exception as e:
            if 'Connection reset by pe' in str(e):
                time.sleep(10)
            else:
                raise e


if __name__ == '__main__':
    import os
    import sys
    from tqdm.auto import tqdm
    import numpy as np
    import traceback
    import argparse, logging
    parser = argparse.ArgumentParser()
    parser.add_argument("--root_path", type=str)
    parser.add_argument("--index_part", type=int, default=0)
    parser.add_argument('--num_parts', type=int, default=1)
    parser.add_argument('--mode', type=str, default='analysis')
    parser.add_argument('--verbose', '-v', action='store_true', help='', default=False)
    parser.add_argument('--redo',  action='store_true', help='', default=False)

    args = parser.parse_args()
    
    filelistpath = args.root_path
    analysis = {}
    if os.path.isdir(filelistpath):
        if filelistpath.endswith('archive_json'):
            root_path = filelistpath
            while not root_path.endswith('whole_arxiv_all_files'):
                root_path = os.path.dirname(root_path)
                assert root_path != '/'
            root_path = os.path.join(root_path,'analysis.parse_reference')
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
        root_path = os.path.join(root_path,'analysis.parse_reference')
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

    if args.mode == 'remain_anystyle':
        new_file_list = []
        for file_path in tqdm(all_file_list):
            if not os.path.exists(os.path.join(file_path,'reference.txt')):continue
            if os.path.getsize(os.path.join(file_path,'reference.txt')) == 0:continue
            if os.path.exists(os.path.join(file_path,'reference.structured.anystyle.jsonl')):continue
            new_file_list.append(file_path)
        with open(args.root_path+'.anystyle','w') as f:
            for file_path in new_file_list:
                f.write(file_path+'\n')
        print(args.root_path+'.anystyle')
        exit()
    if args.mode == 'remain_grobid':
        new_file_list = []
        for file_path in tqdm(all_file_list):
            if not os.path.exists(os.path.join(file_path,'reference.txt')):continue
            if os.path.getsize(os.path.join(file_path,'reference.txt')) == 0:continue
            if os.path.exists(os.path.join(file_path,'reference.grobid.tei.xml')):continue
            new_file_list.append(file_path)
        with open(args.root_path+'.grobid','w') as f:
            for file_path in new_file_list:
                f.write(file_path+'\n')
        print(args.root_path+'.grobid')
        exit()
    
    
    for file_path in tqdm(all_file_list):
        process_file(file_path,args.verbose, args.redo)
    print("Processing completed.")