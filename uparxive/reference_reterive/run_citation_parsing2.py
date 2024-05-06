import subprocess
import sys 
import threading
import queue
import logging
def monitor_process(process, log_queue):
    # Monitor the stdout and stderr of the process
    for line in iter(process.stdout.readline, b''):
        decoded_line = line
        print(decoded_line, end='')  # Print the output in real-time
        log_queue.put(decoded_line)  # Add output to the queue for logging
        if "Error" in decoded_line:
            process.kill()
            break
    process.stdout.close()
from grobid_client.grobid_client import GrobidClient

client = GrobidClient(config_path="./config.json")

import os
from time import sleep
def process_file(file_dir,verbose=False, redo=False):
    JSONROOT = os.path.dirname(file_dir)
    arxivid  = os.path.basename(file_dir)

    ReferencePath = os.path.join(file_dir,'reference.txt')
    if not os.path.exists(ReferencePath):
        tqdm.write(f"WARNING: why the reference file for {arxivid} is missing?")
        return
    if os.path.getsize(ReferencePath) == 0:
        #tqdm.write(f"WARNING: why the reference file for {arxivid} is empty?")
        return
    
    grobid_output = os.path.join(file_dir, "reference.grobid.tei.xml") 
    #print(grobid_output)
    grobid_result = 0
    if not os.path.exists(grobid_output) or redo:
        client.process("processCitationList", file_dir)

        # process = subprocess.Popen(
        #     ["grobid_client","--input", file_dir,"processCitationList"],  # Replace with actual command and options
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.STDOUT,
        #     text=True
        # )
        # process.wait()
        # grobid_result = process.returncode
    
    grobid_result = "Fail" if grobid_result != 0 else "Pass"

    anystyle_output= os.path.join(file_dir, "reference.structured.anystyle.jsonl") 
    anystyle_result= 0
    # if not os.path.exists(anystyle_output) or redo:

    #     process = subprocess.Popen(
    #         ["anystyle","-f","json", "parse", ReferencePath ],  # Replace with actual command and options
    #         stdout=subprocess.PIPE,
    #         stderr=subprocess.STDOUT,
    #         text=True
    #     )
        
    #     lines = []
    #     while True:
    #         line = process.stdout.readline()
    #         if not line:  # If readline returns an empty bytes object, the process has finished
    #             break
    #         lines.append(line)
    #         # Check exit status
    #     process.wait()
    #     with open(anystyle_output,'w') as f:
    #         for line in lines:
    #             f.write(line)
    #     anystyle_result = process.returncode
    anystyle_result = "Fail" if anystyle_result != 0 else "Pass"
    
    status = f"deal with {arxivid} with grobid {grobid_result} and anystyle {anystyle_result}"
    if anystyle_result == "Fail" or grobid_result == "Fail":
        tqdm.write(status)


    

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