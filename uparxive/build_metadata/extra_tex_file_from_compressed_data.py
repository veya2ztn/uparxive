import os
import tarfile
import gzip
import sys
from pathlib import Path
module_dir = str(Path(__file__).resolve().parent)
if module_dir not in sys.path:sys.path.append(module_dir)

from utils import (get_tex_file_name, isHardTex, isSoftTex, isComponentOfTex, 
                   get_batch_control_parser, obtain_processed_filelist,process_files)


import magic
import time
import shutil

def get_file_type(filepath):
    mime = magic.Magic(mime=True)
    return mime.from_file(filepath)

def endswithextension(name):
    return isHardTex(name) or isSoftTex(name) or isComponentOfTex(name)

def extra_as_tar(tar_file, save_dir)->str:
    with tarfile.open(tar_file, 'r') as tar:
        uncompressed_file = []
        for member in tar.getmembers():
            if endswithextension(member.name.lower()):
                tar.extract(member, save_dir)
                uncompressed_file.append(member.name.lower())
    hasTeX = any([isHardTex(t) for t in uncompressed_file])
    hasTxt = any([isSoftTex(t) for t in uncompressed_file])
    if hasTeX:
        return 'isTeX'
    if hasTxt:
        return 'isPlainTeX'
    if len(uncompressed_file)>0:
        return 'DecompressedButNoTeX'
    else:
        return 'NoTeX'

def get_arxivid_from_tarname(tarname):
    return tarname.replace('.gz','').replace('.tar','')

def deal_with_one_path(source_path, target_dir)->str:
    source_name   = get_arxivid_from_tarname(os.path.basename(source_path))
    target_path   = os.path.join(target_dir,source_name )
    file_type     = get_file_type(source_path) 
    if file_type == 'application/x-tar':
        result=extra_as_tar(source_path, target_dir)
        # os.remove(thepath)
        return result
    elif file_type == 'text/plain':
        shutil.copy(source_path , target_path+'.tex.txt')
        return 'isPlainTeX'
    elif file_type == 'text/x-tex':
        shutil.copy(source_path , target_path+'.tex')
        return 'isTeX'
    elif file_type == 'application/pdf':
        #os.rename(save_path , save_path.replace('.tex','.pdf'))
        #os.remove(thepath)
        return 'isPDF'
    elif file_type == 'application/x-gzip': 
        save_path = os.path.join(target_dir, 'uncompressed_file')
        with gzip.open(source_path, 'rb') as f_in:
            with open(save_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        time.sleep(0.5)
        return deal_with_one_path(save_path, target_dir)
    else:
        return file_type

def untar_and_extract(tar_file,args):
    save_dir = args.savepath
    #assert os.path.exists(tar_file)
    dest_folder          = save_dir
    tar_fold, dest_name  = os.path.split(tar_file)
    arxivid              = get_arxivid_from_tarname(dest_name)
    dest_dir             = os.path.join(dest_folder, arxivid)

    has_File             = False
    if os.path.exists(tar_file):
        has_File         = True
    else:
        for postfix in ['.tar.gz','.gz','','.tar']:
            tar_file   = os.path.join(tar_fold, arxivid+postfix)
            if os.path.exists(tar_file):
                has_File = True
                break
    if not has_File:
        print(f"Warning: {tar_file} is not found")
        return arxivid, "noSource"
    
    if os.path.exists(dest_dir) and not args.redo:
        print(f"Warning: {dest_dir} is existed, we skip")
        return 
    os.makedirs(dest_dir, exist_ok=True)
    try:
        result = deal_with_one_path(tar_file,dest_dir)
    except:
        result = "Fail"
    return arxivid,result
    

if __name__ == '__main__':
    parser = get_batch_control_parser()
    args   = parser.parse_args()
    alread_processing_file_list = obtain_processed_filelist(args)
    fail_collect = process_files(untar_and_extract, alread_processing_file_list, args)
    totally_paper_num= len(alread_processing_file_list)
    if totally_paper_num > 1:
        with open(f'analysis/fail_collect/{args.start_index:03d}_{args.end_index:03d}.txt','w') as f:
            for line in fail_collect:
                f.write(f"{line}\n")
    else:
        print(fail_collect)

