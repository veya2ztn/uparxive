
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

old_line1 = "\\newcommand{\\colorfbox}[3]{\\definecolor{bgcolor}{RGB}{#2} \\fboxsep=0pt \\fboxrule=0pt \\color{bgcolor} \\fbox{\\colorbox{bgcolor}{\\strut #3}}}"
new_line1 = "\\newcommand{\\colorfbox}[3]{\\definecolor{bgcolor}{RGB}{255,255,255} \\fboxsep=0pt \\fboxrule=0pt  \\fbox{\\colorbox{bgcolor}{\\strut #3}}}"
old_line2 = """\\newcommand{\\colorfboxx}[3]{
\\definecolor{bgcolor}{RGB}{#2} 
\\begin{tcolorbox}[colback=bgcolor, colframe=bgcolor, coltext=bgcolor] 
\\strut #3  
\\end{tcolorbox} 
}"""
new_line2 = """\\newcommand{\\colorfboxx}[3]{
\\definecolor{bgcolor}{RGB}{255,255,255} 
\\begin{tcolorbox}[colback=bgcolor, colframe=bgcolor, coltext=black] 
\\strut #3  
\\end{tcolorbox} 
}"""


def process_one_file(filepath, args:BatchModeConfig):
    with open(filepath,'r') as f:
        content = f.read()
    content = content.replace(old_line1,new_line1)
    content = content.replace(old_line2,new_line2)
    backup_path = filepath[:-4]+'.origin.tex'
    os.rename(filepath,backup_path)
    with open(filepath,'w') as f:
        f.write(content)

    return filepath,"Pass"
   

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
    
    # totally_paper_num = len(alread_processing_file_list)
    # save_analysis(analysis, totally_paper_num==1, args)
    