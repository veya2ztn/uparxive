from pathlib import Path
import sys
module_dir = str(Path(__file__).resolve().parent.parent)
if module_dir not in sys.path:sys.path.append(module_dir)

from uparxive.batch_run_utils import obtain_processed_filelist, process_files,save_analysis
from uparxive.tex_to_xml.archive_xml import archive_one_xml_fold_wrapper, ArchiveXMLConfig
from simple_parsing import ArgumentParser

import os
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_arguments(ArchiveXMLConfig, dest="config")
    args = parser.parse_args()
    args = args.config

    alread_processing_file_list = obtain_processed_filelist(args)
    results = process_files(archive_one_xml_fold_wrapper, alread_processing_file_list, args)
    
    