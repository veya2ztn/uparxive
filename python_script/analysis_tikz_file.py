
from pathlib import Path
import sys, os
module_dir = str(Path(__file__).resolve().parent.parent)
if module_dir not in sys.path:sys.path.append(module_dir)
from uparxive.batch_run_utils import BatchModeConfig, obtain_processed_filelist, process_files,dataclass, save_analysis
from simple_parsing import ArgumentParser
import re
@dataclass
class LogAnalysisConfig(BatchModeConfig):
    task_name = 'TikzAnalysis'

tikzflag = [
    "tikz-cd",
    "sty_jtana_tikzit",
    "auxTikzDefs",
    #"tikz",
    "tikzit",
    "tikz-timing",
    "tikzpicture",
]

def check_one_path(arxiv_path,args):
    arxivid = os.path.basename(os.path.dirname(arxiv_path))
    if not os.path.exists(arxiv_path):return arxivid, 'NoSource'

    with open(arxiv_path,'r',encoding='utf-8', errors='ignore') as f:
        hastikzpicture = False
        for line in f:
            #if line.strip().startswith('%'):continue
            if any([t in line for t in tikzflag ]):
                hastikzpicture=True
                break
        if hastikzpicture:
            return arxivid, 'HasTIKZ'
        else:
            return arxivid, 'NoTIKZ'

def check_one_path_wrapper(args):
    logpath, args = args
    return check_one_path(logpath, args)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_arguments(LogAnalysisConfig, dest="config")
    args = parser.parse_args()
    args = args.config

    
    #if args.mode == 'analysis':
    alread_processing_file_list = obtain_processed_filelist(args)
    results = process_files(check_one_path_wrapper, alread_processing_file_list, args)
    #print(results)
    analysis= {}
    for arxivid, _type in results:
        if _type not in analysis:
            analysis[_type] = []
        analysis[_type].append(arxivid)

    totally_paper_num = len(alread_processing_file_list)
    save_analysis(analysis, totally_paper_num==1, args)
