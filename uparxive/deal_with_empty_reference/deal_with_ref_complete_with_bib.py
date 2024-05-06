
import os,re
from pathlib import Path
from tqdm.auto import tqdm
from tqdm.auto import tqdm

################
# deal with ref with bbl is easy, we replace the \bibliography with the content in .bbl file
################
import re
def extract_bib_files(tex_content):
    # Define the regular expression for the bibliography pattern
    bib_pattern = r'\\bibliography{([^}]+)}'
    
    # Search using the regular expression
    matches = re.findall(bib_pattern, tex_content)
    
    # matches is a list of all occurrences of the bib_pattern
    if matches:
        # Split the result to get individual bib files
        bib_files = [bib.strip() for bib in matches[0].split(',')]
        return bib_files
    else:
        return []

PATHLIST_FILEPATH = '/nvme/zhangtianning.di/datasets/LLM/arxiv/whole_arxiv_all_cs/analysis.tex_to_xml/tex_to_xml.pass.badbib/tex_to_xml.pass.badbib.but_bib_complete.only_bib_complete'
ROOT= '/nvme/zhangtianning.di/datasets/LLM/arxiv/whole_arxiv_all_cs'

arxiv_id_to_root_tex_name = {}
with open(os.path.join(ROOT,"filelist.all_tex.root"),'r') as f:
    for tex_path in f:
        tex_path = tex_path.strip()
        tex_name = os.path.basename(tex_path)
        arxiv_id = os.path.basename(os.path.dirname(tex_path))
        arxiv_id_to_root_tex_name[arxiv_id] = tex_name

with open(PATHLIST_FILEPATH,'r') as f:
    arxiv_id_list = [arxiv_id.strip() for arxiv_id in f]

import re

def find_citations(tex_content):
    # This regular expression will match the \cite command and capture the content within the curly braces
    citation_pattern = r'\\cite\{(.*?)\}'
    
    # Find all matches in the TeX content
    matches = re.findall(citation_pattern, tex_content)
    
    return matches

#with open(PATHLIST_FILEPATH+".pathlist",'w') as f:
for  arxiv_id in tqdm(arxiv_id_list):
    arxiv_id = arxiv_id.strip()
    tex_fold = os.path.join(ROOT,"unprocessed_tex",arxiv_id)
    tex_name = arxiv_id_to_root_tex_name[arxiv_id]
    tex_path = os.path.join(tex_fold,tex_name)
    #f.write(tex_path+'\n')
    if os.path.exists(tex_path+'.bk'):
        #os.rename(tex_path+'.bk',tex_path)
        #f.write(tex_path+'\n')
        continue 
    tex_name = tex_name.replace('.tex','')
    with open(tex_path, 'r', encoding='utf-8', errors='ignore') as file:
        lines = file.readlines()
    lines = [line for line in lines if not line.strip().startswith('%')]
    tex_content = ''.join(lines)
    bib_names= extract_bib_files(tex_content)
    bib_names= [name for name in bib_names if name not in ['IEEEabrv','anthology']]
    citations = find_citations(tex_content)
    whole_citation=[]
    for citation in citations:
        whole_citation.extend(citation.split(','))
    citation_string = ["\cite{"+citation+"}" for citation in whole_citation  ]
    citation_string = "\n".join(citation_string)
    bib_string = ",".join(bib_names)
    temp_tex_content = r"""
        \documentclass[letterpaper, 10pt]{article}
        \usepackage[authoryear]{natbib}
        \begin{document}""" + citation_string +r"""
        \bibliographystyle{apalike}
        \bibliography{""" + bib_string + r"""}
        \end{document} 
        """
    print(tex_fold)
    with open(os.path.join(tex_fold,'temp.tex'),'w') as f:
        f.write(temp_tex_content)
    os.system(f'cd {tex_fold}; latex temp; bibtex temp;')
    raise