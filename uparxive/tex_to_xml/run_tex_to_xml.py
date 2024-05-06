import subprocess
import logging
import os
from ..batch_run_utils import BatchModeConfig, dataclass
from tqdm.auto import tqdm

@dataclass
class Tex2XMLConfig(BatchModeConfig):
    verbose : bool = False
    redo : bool = False
    task_name = 'tex_compiling'


def tex_to_xml(file_path,args):
    verbose = args.verbose 
    redo=args.redo
    TEXROOT = os.path.dirname(file_path)
    XMLROOT = TEXROOT.replace('unprocessed_tex','unprocessed_xml').replace('archive_tex','unprocessed_xml')
    FileN    = os.path.basename(file_path)

    output_file = os.path.join(XMLROOT, FileN[:-4]+'.xml')  # Change extension as needed
    log_file    = os.path.join(XMLROOT, FileN[:-4]+'.log')
    if os.path.exists(log_file) and not redo:
        if args.batch_num==0: tqdm.write(f"[Skip] ==> {log_file}")
        return 
    if os.path.exists(output_file) and not redo:
        if args.batch_num==0: tqdm.write(f"[Skip] ==> {log_file}")
        return
    os.makedirs(XMLROOT,exist_ok=True)
    
    #with open(log_file, 'a') as logfile:
        # Start the process
    #print(log_file)
    process = subprocess.Popen(
        ['latexmlc', '--noparse', '--nocomments', '--includestyles' , '--nopictureimages','--nographicimages','--nosvg','--timeout','360',
            f'--log={log_file}',
            f'--path={TEXROOT}',
            f'--dest={output_file}',
            FileN],  # Replace with actual command and options
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )

    # Log queue to handle log messages
    while True:
        line = process.stdout.readline()
        if not line:  # If readline returns an empty bytes object, the process has finished
            break
        decoded_line = line#.decode('utf-8')
        if verbose:print(decoded_line, end='')  # Print the output in real-time
        

        if "Error" in decoded_line or 'Fatal' in decoded_line:
            process.kill()  # Kill the process if an error is detected
            break
        # Check exit status
    process.wait()
    result = process.returncode
    with open(log_file, 'a') as logfile:
        if result != 0:
            logfile.write('\n' + decoded_line+'\n')
            logfile.write(f"Conversion failed with status {result}: error \n")
            if args.batch_num==0: tqdm.write(f"[Fail] ==> {log_file}")
        else:
            pass
            if args.batch_num==0: tqdm.write(f"[Pass] ==> {log_file}")


def process_file(args):
    file_path, redo = args
    return tex_to_xml(file_path, redo)


from multiprocessing import Pool

def batch_process_files(file_list, num_processes=32, redo=False):
    with Pool(processes=num_processes) as pool:
        args_list = [(file, redo) for file in file_list]
        results = list(tqdm(pool.imap(process_file, args_list), total=len(file_list)))
    return results    

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
    parser.add_argument('--shuffle',  action='store_true', help='', default=False)
    parser.add_argument('--batch',  action='store_true', help='', default=False)
    args = parser.parse_args()
    
    xml_path = args.root_path
    analysis = {}
    if os.path.isdir(xml_path):
        
        root_path = xml_path
        while not root_path.endswith('whole_arxiv_all_files'):
            root_path = os.path.dirname(root_path)
            assert root_path != '/'
        root_path = os.path.join(root_path,'analysis/tex_to_xml')
        print(root_path)
        os.makedirs(root_path,exist_ok=True)
        ROOTPATH = xml_path
        all_file_list = os.listdir(ROOTPATH)
        all_file_list = [os.path.join(ROOTPATH, DIRNAME) for DIRNAME in all_file_list]
    elif os.path.isfile(xml_path):

        root_path = xml_path
        while not root_path.endswith('whole_arxiv_all_files'):
            root_path = os.path.dirname(root_path)
            assert root_path != '/'
        root_path = os.path.join(root_path,'analysis/tex_to_xml')
        #root_path= os.path.join(os.path.dirname(os.path.dirname(xml_path)),'analysis.tex_to_xml')
        print(root_path)
        os.makedirs(root_path,exist_ok=True)
        if xml_path.endswith('.tex'):
            all_file_list=[xml_path]
        else:
            with open(xml_path,'r') as f:
                all_file_list = [t.strip() for t in f.readlines()]
    else:
        raise NotImplementedError
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

    if args.shuffle:
        np.random.shuffle(all_file_list)
    all_file_list = all_file_list[start_index: end_index]
    
    if args.batch:
        batch_process_files(all_file_list, num_processes=32,redo=args.redo)
    else:
        for file_path in tqdm(all_file_list):
            tex_to_xml(file_path,args.verbose, args.redo)

    print("Processing completed.")