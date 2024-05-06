import os
import tarfile
import gzip
import sys
from pathlib import Path
module_dir = str(Path(__file__).resolve().parent)
if module_dir not in sys.path:sys.path.append(module_dir)

from utils import (get_tex_file_name, isHardTex, isSoftTex, isComponentOfTex, 
                   get_batch_control_parser, obtain_processed_filelist,process_files)

def check_tex_fold(tex_fold_path, args):
    arxivid = os.path.basename(tex_fold_path)
    if any( [isHardTex(filename) for filename in os.listdir(tex_fold_path)]):
        return arxivid, 'isTeX'
    if any( [isSoftTex(filename) for filename in os.listdir(tex_fold_path)]):
        return arxivid, 'isPlainTeX'
    return arxivid, 'NoTeX'
    
if __name__ == '__main__':
    parser = get_batch_control_parser()
    args   = parser.parse_args()
    alread_processing_file_list = obtain_processed_filelist(args)
    fail_collect = process_files(check_tex_fold, alread_processing_file_list, args)
    totally_paper_num= len(alread_processing_file_list)
    os.makedirs(args.logpath, exist_ok=True)
    if totally_paper_num > 1:
        with open(os.path.join(args.logpath,f'{args.start_index:03d}_{args.end_index:03d}.txt'),'w') as f:
            for line in fail_collect:
                if line is None:continue
                arxivid, status = line
                f.write(f"{arxivid} {status}\n")
    else:
        print(fail_collect)


