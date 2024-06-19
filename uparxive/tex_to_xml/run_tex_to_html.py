from pathlib import Path
import sys
module_dir = str(Path(__file__).resolve().parent.parent)
if module_dir not in sys.path:sys.path.append(module_dir)
import subprocess
import logging
import os
from ..batch_run_utils import BatchModeConfig, dataclass
from tqdm.auto import tqdm


@dataclass
class Tex2HTMLConfig(BatchModeConfig):
    verbose : bool = False
    redo : bool = False
    task_name = 'tex_compiling'


def tex_to_html(file_path,args):
    verbose = args.verbose 
    redo=args.redo
    TEXROOT  = os.path.dirname(file_path)
    HTMLROOT = os.path.join(TEXROOT,'temp')
    FileN    = os.path.basename(file_path)

    output_file = os.path.join(HTMLROOT, FileN[:-4]+'.html')  # Change extension as needed
    log_file    = os.path.join(HTMLROOT, FileN[:-4]+'.log')
    # if os.path.exists(log_file) and not redo:
    #     #if args.batch_num==0: tqdm.write(f"[Skip] ==> {log_file}")
    #     return 
    if os.path.exists(output_file) and not redo:
        #if args.batch_num==0: tqdm.write(f"[Skip] ==> {log_file}")
        return
    os.makedirs(HTMLROOT,exist_ok=True)
    #tqdm.write(f"[Now] ==> {output_file}")
    process = subprocess.Popen(
        ['latexmlc', '--noparse','--nocomments', '--includestyles' ,'--timeout','360',
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
        

        # if "Error" in decoded_line or 'Fatal' in decoded_line:
        #     process.kill()  # Kill the process if an error is detected
        #     break
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



def tex_to_html_wrapper(args):
    arxiv_path, args = args
    return tex_to_html(arxiv_path, args)