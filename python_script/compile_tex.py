
import os
from pathlib import Path
import sys
module_dir = str(Path(__file__).resolve().parent.parent)
if module_dir not in sys.path:sys.path.append(module_dir)



from simple_parsing import ArgumentParser
from uparxive.batch_run_utils import obtain_processed_filelist, process_files,save_analysis, BatchModeConfig
import time
import subprocess
from tqdm.auto import tqdm




def process_one_file(file_path, args:BatchModeConfig):
    targetname = get_pdf_name(file_path)
    
    targetpath = os.path.join(os.path.dirname(file_path), 'temp', targetname)
    

    if os.path.exists(targetpath) and not args.redo:return file_path, "Skip"
    #tqdm.write(file_path)
    process = subprocess.Popen(["latexmk", "-quiet","-silent", "-synctex=0","-interaction=nonstopmode","-file-line-error","-pdf","-f","-outdir=temp","-cd" , file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
            )
    while True:
        line = process.stdout.readline()
        if 'SIGTERM' in line:
            process.kill()
            return file_path, "Fail"
        if not line:  # If readline returns an empty bytes object, the process has finished
            break
        decoded_line = line#.decode('utf-8')
        #print(decoded_line)

    # os.rename(targetpath,targetpath.replace('.colorful.pdf','.colorful_all_colored.pdf'))
    
    # with open(file_path,'r') as f:
    #     content_ready_for_modification = f.readlines()
    # new_content = []
    # for line in content_ready_for_modification:
    #     if line.strip() == "\\newcommand{\\colorfbox}[3]{\\definecolor{bgcolor}{RGB}{#2} \\fboxsep=0pt \\fboxrule=0pt \\color{bgcolor} \\fbox{\\colorbox{bgcolor}{\\strut #3}}}":
    #         line = "\\newcommand{\\colorfbox}[3]{\\definecolor{bgcolor}{RGB}{255,255,255} \\fboxsep=0pt \\fboxrule=0pt  \\fbox{\\colorbox{bgcolor}{\\strut #3}}}"
    #     new_content.append(line)
    # os.rename(file_path, no_masked_file_path)
    # with open(file_path,'w') as f:
    #     f.write(''.join(new_content))
    # process = subprocess.Popen(["latexmk", "-quiet","-silent", "-synctex=0","-interaction=nonstopmode","-file-line-error","-pdf","-f","-outdir=temp","-cd" , file_path],
    #         stdout=subprocess.PIPE,
    #         stderr=subprocess.STDOUT,
    #         text=True
    #         )
    # while True:
    #     line = process.stdout.readline()
    #     if 'SIGTERM' in line or 'Fail' in line or 'Error' in line:
    #         process.kill()
    #         return file_path, "Fail"
    #     if not line:  # If readline returns an empty bytes object, the process has finished
    #         break
    #     decoded_line = line#.decode('utf-8')


    return  file_path,"Pass"
   
def get_pdf_name(path):
    path = os.path.basename(path)
    path = path.split('.')[:-1]
    path = ".".join(path)
    path = path+'.pdf'
    return path

def process_one_file_wrapper(args):
    arxiv_path, args = args
    try:
        return process_one_file(arxiv_path,args)
    except:
        return arxiv_path,"Fail"
    

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_arguments(BatchModeConfig, dest="config")
    args = parser.parse_args()
    args = args.config

    alread_processing_file_list = obtain_processed_filelist(args)
    results = process_files(process_one_file_wrapper, alread_processing_file_list, args)
    analysis= {}
    for arxivid, _type in results:
        if _type not in analysis:
            analysis[_type] = []
        analysis[_type].append(arxivid)
    
    totally_paper_num = len(alread_processing_file_list)
    save_analysis(analysis, totally_paper_num==1, args)
    