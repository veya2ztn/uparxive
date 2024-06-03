
import os
from pathlib import Path
import sys
module_dir = str(Path(__file__).resolve().parent.parent)
if module_dir not in sys.path:sys.path.append(module_dir)


from uparxive.lougat.seek_whole_the_resource import process_one_file_wrapper, SeekResourceConfig
from simple_parsing import ArgumentParser
from uparxive.batch_run_utils import obtain_processed_filelist, process_files, save_analysis
import time

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_arguments(SeekResourceConfig, dest="config")
    args = parser.parse_args()
    args = args.config

    alread_processing_file_list = obtain_processed_filelist(args)
    results = process_files(process_one_file_wrapper, alread_processing_file_list, args)
    whole_results = []
    for result in results:
        whole_results.extend(result)
    
    analysis={'undownload_resource':whole_results}
    
    totally_paper_num = len(alread_processing_file_list)
    save_analysis(analysis, totally_paper_num==1, args)
    