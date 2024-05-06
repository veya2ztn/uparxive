
import os,re,sys
from pathlib import Path
from tqdm.auto import tqdm
from tqdm.auto import tqdm
module_dir = str(Path(__file__).resolve().parent)
if module_dir not in sys.path:sys.path.append(module_dir)
from utils import *
################
# deal with ref with bbl is easy, we replace the \bibliography with the content in .bbl file
################
import re
def extract_bib_files(tex_content):
    # Define the regular expression for the bibliography pattern
    bib_pattern = r'\\bibliography{([^}]*)}'
    
    # Search using the regular expression
    matches = re.findall(bib_pattern, tex_content)
    
    # matches is a list of all occurrences of the bib_pattern
    if matches:
        # Split the result to get individual bib files
        bib_files = [bib.strip() for bib in matches[0].split(',') if bib.strip() != '']
        return bib_files
    else:
        return None ##<<<----this should be None

### lets firstly deal with the empty reference case, which is always due to the bib problem.
### In modern tex standard, the bib information always in a seperate file .bib, thus we will roll back those task into tex_to_xml processing
# PATHLIST_FILEPATH = '/nvme/zhangtianning.di/datasets/LLM/arxiv/whole_arxiv_all_cs/analysis.tex_to_xml/tex_to_xml.pass.badbib/tex_to_xml.pass.badbib.but_bib_complete.whole_bbl_complete'
# ROOT= '/nvme/zhangtianning.di/datasets/LLM/arxiv/whole_arxiv_all_cs'
PATHLIST_FILEPATH=sys.argv[1] #"/nvme/zhangtianning.di/datasets/LLM/arxiv/whole_arxiv_all_cs/analysis.tex_to_xml/tex_to_xml.pass.badbib/tex_to_xml.pass.badbib.but_bib_complete.whole_bbl_complete"
ROOT= get_directory_before_analysis(PATHLIST_FILEPATH)

arxiv_id_to_root_tex_name = {}
with open(os.path.join(ROOT,"filelist.all_tex.root"),'r') as f:
    for tex_path in f:
        tex_path = tex_path.strip()
        tex_name = os.path.basename(tex_path)
        arxiv_id = os.path.basename(os.path.dirname(tex_path))
        arxiv_id_to_root_tex_name[arxiv_id] = tex_name

with open(PATHLIST_FILEPATH,'r') as f:
    arxiv_id_list = [arxiv_id.strip() for arxiv_id in f]



with open(PATHLIST_FILEPATH+".pathlist",'w') as f:
    for  arxiv_id in tqdm(arxiv_id_list):
        arxiv_id = arxiv_id.strip()
        tex_fold = os.path.join(ROOT,"unprocessed_tex",arxiv_id)
        tex_name = arxiv_id_to_root_tex_name[arxiv_id]
        tex_path = os.path.join(tex_fold,tex_name)
        if os.path.exists(tex_path+'.bk'):
            os.rename(tex_path+'.bk',tex_path)
        if os.path.exists(tex_path+'.origin'):
            os.rename(tex_path+'.origin',tex_path)
            #continue 
        tex_name = tex_name.replace('.tex','')
        with open(tex_path, 'r', encoding='utf-8', errors='ignore') as file:
            lines = file.readlines()
        lines = [line.strip() for line in lines if not line.strip().startswith('%')]
        tex_content = '\n'.join(lines)

        bib_names= extract_bib_files(tex_content)
        if bib_names is not None:
            bib_names= [name for name in bib_names if name not in ['IEEEabrv','anthology']]
            if len(bib_names) >0:
                #assert bib_names[0] == tex_name, f'bibname is {bib_names[0]} but texname is {tex_name}. Task => {tex_path}'
                print("skip via it already has bib")
                continue
            assert len(bib_names) == 0, f"get bib_names is {bib_names}. Task => {tex_path}"
            assert os.path.exists(os.path.join(tex_fold,tex_name+'.bbl')) ## in those case, we have already get the correct and complete bib reference in bbl file
            bib_pattern = r'\\bibliography{[^}]*}'
            bbl_content = r'\bibliography{' + tex_name +r'}'  
            
            tex_content_updated = re.sub(bib_pattern, lambda match: bbl_content, tex_content)
        else:
            end_document_pattern = r'\\end\{document\}'
            replacement_content = r'\\bibliography{' + tex_name + r'}' + '\n' + r'\\end{document}'
            tex_content_updated = re.sub(end_document_pattern, replacement_content, tex_content)
        f.write(tex_path+'\n')
        os.rename(tex_path,tex_path+'.origin')
        #new_tex_path = os.path.join(tex_fold,"new."+tex_name+'.tex')
        with open(tex_path, 'w', encoding='utf-8') as file:
            file.write(tex_content_updated)
        #tqdm.write(tex_path)