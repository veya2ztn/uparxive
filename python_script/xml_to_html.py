from pathlib import Path
import sys
module_dir = str(Path(__file__).resolve().parent.parent)
if module_dir not in sys.path:sys.path.append(module_dir)

from uparxive.batch_run_utils import obtain_processed_filelist, process_files,BatchModeConfig, dataclass
from simple_parsing import ArgumentParser
import os
import subprocess
import os
from tqdm.auto import tqdm

@dataclass
class XML2HTMLConfig(BatchModeConfig):
    verbose : bool = False
    redo : bool = False
    task_name = 'xml_to_html'


def xml_to_html(file_path,args):
    verbose = args.verbose 
    redo=args.redo
    xmlpath = file_path.replace('html','xml')
    htmlpath= file_path.replace('xml', 'html')

    if os.path.exists(htmlpath) and not redo:
        if args.batch_num==0: tqdm.write(f"[Skip] ==> {htmlpath}")
        return 
    os.makedirs(os.path.dirname(htmlpath),exist_ok=True)
    logpath = htmlpath[:-5]+'.log'
    process = subprocess.Popen(
        ['latexmlpost',f'--log={logpath}' ,f'--dest={htmlpath}', xmlpath],  # Replace with actual command and options
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
        
    process.wait()
    result = process.returncode
    

def xml_to_html_wrapper(args):
    arxiv_path, args = args
    return xml_to_html(arxiv_path, args)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_arguments(XML2HTMLConfig, dest="config")
    args = parser.parse_args()
    args = args.config
    alread_processing_file_list = obtain_processed_filelist(args)
    results = process_files(xml_to_html_wrapper, alread_processing_file_list, args)
    
    