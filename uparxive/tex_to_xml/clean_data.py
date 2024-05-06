import os
from pathlib import Path
from tqdm.auto import tqdm
import glob
if __name__ == '__main__':
    
    import sys
    import os 
    from tqdm.auto import tqdm
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root_path", type=str)
    parser.add_argument("--mode", type=str)
    args = parser.parse_args()
    
    #ROOT= "/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/unprocessed_tex/"
    ROOT_PATH=args.root_path 
    assert "unprocessed_tex" in ROOT_PATH
    if 'clean.' in args.mode:
        if args.mode == 'clean.ps':
            all_files = glob.glob(os.path.join(ROOT_PATH, '*/*.ps'),  recursive=True)
        elif args.mode == 'clean.pdf':
            all_files = glob.glob(os.path.join(ROOT_PATH, '*/*.pdf'),  recursive=True)
        elif args.mode == 'clean.eps':
            all_files = glob.glob(os.path.join(ROOT_PATH, '*/*.eps'),  recursive=True)
        else:
            raise NotImplementedError 
        for file in tqdm(all_files):
            if os.path.isdir(file):
                print(f"please manual delete the .ps fold: {file}")
                continue
            os.remove(file)
        exit()

    ROOT = ROOT_PATH
    need_deal_with_arxiv_id_list = os.listdir(ROOT_PATH)
    totally_paper_num = len(need_deal_with_arxiv_id_list)
    NOTEXFILES=[]
    for arxiv_id in tqdm(need_deal_with_arxiv_id_list):
        ### get whole the files that used .TEX as suffix
        if args.mode =='check.tex':
            all_tex_files = Path(os.path.join(ROOT, arxiv_id)).glob('*.TEX')
            for tex_file in all_tex_files:
                new_name = tex_file.with_suffix('.tex')
                os.rename(tex_file, tex_file.with_suffix('.tex'))

            all_tex_files = Path(os.path.join(ROOT, arxiv_id)).glob('*.tex')
            if len(list(all_tex_files)) == 0:
                NOTEXFILES.append(arxiv_id)
    if args.mode =='check.tex':
        with open(os.path.join(os.path.dirname(ROOT_PATH),'notex.arxivids'),'w') as f:
            for a in NOTEXFILES:
                f.write(a+'\n')
