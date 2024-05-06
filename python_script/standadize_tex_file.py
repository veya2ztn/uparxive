from pathlib import Path
import sys
module_dir = str(Path(__file__).resolve().parent.parent)
if module_dir not in sys.path:sys.path.append(module_dir)

from uparxive.batch_run_utils import obtain_processed_filelist, process_files,save_analysis
from uparxive.tex_to_xml.standalize_tex import TexStandardConfig, standardize_one_file_wrapper
from simple_parsing import ArgumentParser
import os

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_arguments(TexStandardConfig, dest="config")
    args = parser.parse_args()
    args = args.config

    alread_processing_file_list = obtain_processed_filelist(args)
    results = process_files(standardize_one_file_wrapper, alread_processing_file_list, args)
    
    analysis= {}
    for arxivid, _type in results:
        if _type not in analysis:
            analysis[_type] = []
        analysis[_type].append(arxivid)
    
    totally_paper_num = len(alread_processing_file_list)
    save_analysis(analysis, totally_paper_num==1, args)