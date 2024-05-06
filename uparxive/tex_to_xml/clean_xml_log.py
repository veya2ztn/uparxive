import os
import sys
from tqdm import tqdm
import shutil
def get_last_n_lines(file_path, n):
    with open(file_path, 'rb') as file:
        file.seek(0, os.SEEK_END)
        position = file.tell()
        lines = []
        while position >= 0 and len(lines) < n:
            file.seek(position)
            next_char = file.read(1)
            if next_char == b'\n':
                lines.append(file.readline().decode().rstrip())
            position -= 1
        file.seek(0)
        if len(lines) < n:
            lines.extend(file.readlines())
        return lines[-n:][::-1]

if __name__ == '__main__':

    import os
    import sys
    from tqdm.auto import tqdm
    import numpy as np
    import traceback
    import argparse, logging
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--root_path", type=str)
    parser.add_argument("--index_part", type=int, default=0)
    parser.add_argument('--num_parts', type=int, default=1)
    parser.add_argument('--mode', type=str, default='analysis')
    args = parser.parse_args()
    
    xml_path = args.root_path#"/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/successed_xml"
    analysis = {}
    if os.path.isdir(xml_path):
        
        root_path = xml_path
        while not root_path.endswith('whole_arxiv_all_files'):
            root_path = os.path.dirname(root_path)
            assert root_path != '/'
        root_path = os.path.join(root_path,'analysis.tex_to_xml')
        print(root_path)
        os.makedirs(root_path,exist_ok=True)
        ROOTPATH = xml_path
        all_file_list = os.listdir(ROOTPATH)
        all_file_list = [os.path.join(ROOTPATH, DIRNAME) for DIRNAME in all_file_list]
    elif os.path.isfile(xml_path):
        root_path = xml_path
        while not root_path.endswith('whole_arxiv_all_files'):
            root_path = os.path.dirname(root_path)
            assert root_path != '/'
        root_path = os.path.join(root_path,'analysis.tex_to_xml')
        #root_path= os.path.join(os.path.dirname(os.path.dirname(xml_path)),'analysis.tex_to_xml')
        print(root_path)
        os.makedirs(root_path,exist_ok=True)
        with open(xml_path,'r') as f:
            all_file_list = [t.strip() for t in f.readlines()]
    
    #all_file_list = [DIR.replace('unprocessed_tex','unprocessed_xml') for DIR in all_file_list if os.path.getsize(DIR) > 0]
    
    index_part= args.index_part
    num_parts = args.num_parts 
    totally_paper_num = len(all_file_list)
    logging.info(totally_paper_num)
    if totally_paper_num > 1:
        divided_nums = np.linspace(0, totally_paper_num, num_parts+1)
        divided_nums = [int(s) for s in divided_nums]
        start_index = divided_nums[index_part]
        end_index   = divided_nums[index_part + 1]
    else:
        start_index = 0
        end_index   = 1
        verbose = True

    all_file_list = all_file_list[start_index: end_index]
    #all_file_list = all_file_list[0:1]
    count = 0
    for arxiv_path in tqdm(all_file_list):
        arxiv_id = os.path.basename(arxiv_path)
        subarxiv_path = os.path.join(arxiv_path,arxiv_id)
 
        all_log_files = Path(arxiv_path).glob("**/*.log")
        all_log_files = [t for t in all_log_files if str(t).endswith('.log')]
        #### modify each log file and only keep the last 20 lines
        for logpath in all_log_files:
            lastlines  = get_last_n_lines(logpath, 20)
            lastlines  = [str(l) for l in lastlines]
            with open(logpath,'w') as f:
                for l in lastlines:
                    f.write(str(l)+'\n')
