from pathlib import Path
import sys
module_dir = str(Path(__file__).resolve().parent.parent)
if module_dir not in sys.path:sys.path.append(module_dir)

from uparxive.batch_run_utils import obtain_processed_filelist, process_files
from uparxive.tex_to_xml.run_tex_to_xml import tex_to_xml, Tex2XMLConfig
from simple_parsing import ArgumentParser
import os

def tex_to_xml_wrapper(args):
    arxiv_path, args = args
    return tex_to_xml(arxiv_path, args)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_arguments(Tex2XMLConfig, dest="config")
    args = parser.parse_args()
    args = args.config
    alread_processing_file_list = obtain_processed_filelist(args)
    results = process_files(tex_to_xml_wrapper, alread_processing_file_list, args)
    
    