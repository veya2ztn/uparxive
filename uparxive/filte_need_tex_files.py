from tqdm.auto import tqdm
import sys
assert len(sys.argv) == 2, "Usage: python filte_need_tex_files.py flag"
import os

flag = sys.argv[1] # flag = quant-ph
extensions = ['.tex', '.ps', '.bbl', '.sty', '.cls', '.bst', '.bib', '.bbx','.tikz','.csv','.clo','.cbx','.dtx','.fls']
filepath_we_need = []
with open("data/whole_file_path_in_arxiv",'r') as f:
    for line in f:
        if flag in line :
            line=line.strip()
            if any(line.lower().endswith(ext) for ext in extensions):
                filepath_we_need.append(line.split()[1])
ROOTDIR = f"data/whole_arxiv.{flag}"
os.makedirs(ROOTDIR, exist_ok=True)
with open(os.path.join(ROOTDIR,f"{flag}_file_path"),'w') as f:
    for line in tqdm(filepath_we_need):
        f.write(line+"\n")