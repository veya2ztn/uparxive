if __name__ == '__main__':
    import sys
    import os 
    import numpy as np
    from tqdm.auto import tqdm
    import argparse
    import shutil

    parser = argparse.ArgumentParser()
    parser.add_argument("--root_path", type=str)
    parser.add_argument("--mode", type=str)
    args = parser.parse_args()
    ROOT_PATH = args.root_path
    with open(ROOT_PATH,'r') as f:
        alread_processing_file_list = [t.strip() for t in f.readlines()]

    
    OLDPATH = '/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/unprocessed_xml'
    NEWPATH = '/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/successed_xml'

    if args.mode == 'normal':
        for arxiv_id in tqdm(alread_processing_file_list):
            old_path = os.path.join(OLDPATH, arxiv_id)
            new_path = os.path.join(NEWPATH, arxiv_id)
            # old_path = os.path.join(NEWPATH, arxiv_id)
            # new_path = os.path.join(OLDPATH, arxiv_id)
            if not os.path.exists(old_path):continue
            if os.path.exists(new_path):
                shutil.rmtree(new_path)
                # if len(set(os.listdir(old_path)) - set(os.listdir(new_path)) ) == 0:
                #     shutil.rmtree(old_path)
                #     #shutil.rmtree(old_path)
                # else:
                #     print(f"{arxiv_id} new_path={len(os.listdir(new_path))} != old_path={len(os.listdir(old_path))}")
                #print(f"{new_path} exist, plead check, we skip")

            shutil.move(old_path, new_path)
    elif args.mode == 'new_bibed_xml':
        for arxiv_id in tqdm(alread_processing_file_list):
            old_path = os.path.join(OLDPATH, arxiv_id)
            if not os.path.exists(old_path):continue
            new_path = os.path.join(NEWPATH, arxiv_id)
            if os.path.exists(new_path):
                for filename in os.listdir(new_path):
                    filepath = os.path.join(new_path, filename)
                    if os.path.isdir(filepath):continue
                    old_file_dir= os.path.join(new_path, 'old_no_bibed_xml')
                    os.makedirs(old_file_dir, exist_ok=True)
                    old_file_path=os.path.join(old_file_dir, filepath)
                    shutil.move(filepath, old_file_path)
                shutil.move(old_path, new_path)
            else:
                shutil.move(old_path, new_path)
            #print(f"move {old_path} to {new_path}")
    else:
        raise NotImplementedError
