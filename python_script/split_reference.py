
import os
from pathlib import Path
import sys
module_dir = str(Path(__file__).resolve().parent.parent)
if module_dir not in sys.path:sys.path.append(module_dir)


from uparxive.reference_reterive.split_concencated_reference import process_one_file_wrapper
from simple_parsing import ArgumentParser
from uparxive.batch_run_utils import obtain_processed_filelist, process_files,save_analysis, BatchModeConfig
import time

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_arguments(BatchModeConfig, dest="config")
    args = parser.parse_args()
    args = args.config

    alread_processing_file_list = obtain_processed_filelist(args)
    results = process_files(process_one_file_wrapper, alread_processing_file_list, args)
    
    