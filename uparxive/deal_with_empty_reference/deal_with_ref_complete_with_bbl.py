
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


### lets firstly deal with the empty reference case, which is always due to the bib problem.
### In modern tex standard, the bib information always in a seperate file .bib, thus we will roll back those task into tex_to_xml processing
# PATHLIST_FILEPATH = '/nvme/zhangtianning.di/datasets/LLM/arxiv/whole_arxiv_all_cs/analysis.tex_to_xml/tex_to_xml.pass.badbib/tex_to_xml.pass.badbib.but_bib_complete.whole_bbl_complete'
# ROOT= '/nvme/zhangtianning.di/datasets/LLM/arxiv/whole_arxiv_all_cs'

import chardet
import os
import sys
from tqdm.auto import tqdm
import numpy as np
import traceback
import argparse,logging

import re
from pylatexenc.latex2text import LatexNodes2Text

def parse_latex_string(match):
    bibitem_part = match.group(1)
    content_part = match.group(2)
    try:
        plain_content = LatexNodes2Text().latex_to_text(content_part)
    except:
        plain_content = content_part
    pattern_angle_brackets = re.compile(r'<[^>]*>')
    plain_content = re.sub(pattern_angle_brackets, '', plain_content)
    plain_content = plain_content.replace('\n'," ")
    plain_content = re.sub(r'\s+', ' ', plain_content)
    return bibitem_part + '\n' + plain_content + '\n'


def parse_bbl_string_to_plain(bbl_content):
    bibitem_entries_pattern = r'(\\bibitem\{.*?\})(.*?)(?=\\bibitem|$|\\end{thebibliography)'
    content = re.sub(bibitem_entries_pattern, parse_latex_string, bbl_content, flags=re.DOTALL)
    return content

def extract_bibitem_elements(input_text):
    # This regular expression captures the optional label [aaa], the citation key {bbb},
    # and the content associated with each \bibitem until the next \bibitem or end of text
    pattern = re.compile(r'''
        \\bibitem                  # Match the \bibitem command
        (?:\[(?P<label>[^\]]*)\])? # Non-capturing group for optional label, capturing the label as 'label'
        \{(?P<key>[^\}]*)\}        # Capture the citation key as 'key'
        (?P<content>.*?)           # Lazily capture the content as 'content'
        (?=\\bibitem|\Z|\\end{thebibliography})           # Stop capturing when the next \bibitem or end of text is encountered
    ''', re.DOTALL | re.VERBOSE)

    # Find all matches of the pattern
    matches = [match.groupdict() for match in pattern.finditer(input_text)]

    return matches
def parse_bbl_string_to_plain(input_text):
    file_content = re.sub(r'\\providecommand.*', '', input_text, flags=re.MULTILINE)
    # Extract the \bibitem elements
    bibitem_elements = extract_bibitem_elements(file_content)
    plain_contents = []
    for pool in bibitem_elements:
        label = pool['label']
        key   = pool['key']
        subcontent = pool['content']
        pattern_angle_brackets = re.compile(r'<[^>]*>')
        try:
            plain_content = LatexNodes2Text().latex_to_text(subcontent)
        except:
            plain_content = subcontent
            
        plain_content = re.sub(pattern_angle_brackets, '', plain_content)
        plain_content = plain_content.replace('\n'," ").replace('NoStop ',"")
        plain_content = re.sub(r'\s+', ' ', plain_content)
        ## print(match[0])
        ## if match[0]: plain_content = f"\\bibitem{match[0]}{match[1]}\n{plain_content}"
        ## else: plain_content = f"\\bibitem{match[1]}\n{plain_content}"
        plain_content = f"\\bibitem{key}\n{plain_content}"
        plain_contents.append(plain_content)
    plain_contents = "\n".join(plain_contents)
    plain_contents = "\\begin{thebibliography}{99}"+'\n' + plain_contents+'\n'+"\\end{thebibliography}"
    return plain_contents

if __name__ == '__main__':


    parser = argparse.ArgumentParser()
    parser.add_argument("--root_path", type=str)
    parser.add_argument("--index_part", type=int, default=0)
    parser.add_argument('--num_parts', type=int, default=1)
    parser.add_argument('--redo', action='store_true', help='', default=False)
    parser.add_argument('--mode', type=str, default='normal')

    args = parser.parse_args()

    verbose = False
    ROOT_PATH = args.root_path # '/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/successed_xml.filelist'
    if os.path.isfile(ROOT_PATH):
        if ROOT_PATH.endswith('.tex'):
            alread_processing_file_list = [ROOT_PATH]
        else:
            with open(ROOT_PATH,'r') as f:
                alread_processing_file_list = [t.strip() for t in f.readlines()]
            
    elif os.path.isdir(ROOT_PATH):
        alread_processing_file_list = os.listdir(ROOT_PATH)
    else:
        alread_processing_file_list = [ROOT_PATH]
    index_part= args.index_part
    num_parts = args.num_parts 

    totally_paper_num = len(alread_processing_file_list)
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
    alread_processing_file_list = alread_processing_file_list[start_index:end_index]

    PATHLIST_FILEPATH=sys.argv[1] #"/nvme/zhangtianning.di/datasets/LLM/arxiv/whole_arxiv_all_cs/analysis.tex_to_xml/tex_to_xml.pass.badbib/tex_to_xml.pass.badbib.but_bib_complete.whole_bbl_complete"
    ROOT= "/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/"

    Analysis = {}
    for  arxiv_id in tqdm(alread_processing_file_list):
        arxiv_id = arxiv_id.strip()
        if arxiv_id.endswith('.tex'):
            tex_path  = arxiv_id
            tex_fold, tex_name =  os.path.split(tex_path)
            xml_path = None
        else:
            tex_fold = os.path.join(ROOT,"unprocessed_tex",arxiv_id)
            #xml_fold = os.path.join(ROOT,"successed_xml",arxiv_id)
            xml_fold = os.path.join(ROOT,"successed_xml",arxiv_id)
            if not os.path.exists(xml_fold):
                tqdm.write(f"WARNING: why the xml fold for {arxiv_id} is missing?")
                Analysis['xml_fold_missing'] = Analysis.get('xml_fold_missing',[])+[arxiv_id]
                continue
            xml_path = list(Path(xml_fold).glob("*.xml"))
            if len(xml_path) == 0:
                tqdm.write(f"WARNING: why the xml file for {arxiv_id} is missing?")
                Analysis['xml_path_missing'] = Analysis.get('xml_path_missing',[])+[arxiv_id]
            elif len(xml_path) > 1:
                Analysis['xml_path_toomany'] = Analysis.get('xml_path_toomany',[])+[arxiv_id]
                tqdm.write(f"WARNING: why the xml file for {arxiv_id} is more than one?")
            xml_path = xml_path[0]
            xml_name = os.path.basename(xml_path)
            tex_name = xml_name.replace('.xml','.tex')#.replace('.clean.tex','.tex')
            tex_path = os.path.join(tex_fold,tex_name)
        
        if os.path.exists(tex_path+'.bk'):
            if not args.redo:
                Analysis['success_add_bib'] = Analysis.get('success_add_bib',[])+[tex_path]
                continue 
            else:
                os.rename(tex_path+'.bk',tex_path)
        if verbose:
            if xml_path:tqdm.write(f"deal with xml file ==> {xml_path}")
            tqdm.write(f"deal with tex file ==> {tex_path}")
        
        tex_name = tex_name.replace('.clean.tex','.tex').replace('.revtex.tex','.tex').replace('.nopackage.tex','.tex').replace('.tex','')
        #print(tex_name)
        with open(tex_path, 'r', encoding='utf-8', errors='ignore') as file:
            lines = file.readlines()
        lines = [line.strip() for line in lines if not line.strip().startswith('%')]
        tex_content = '\n'.join(lines)

        bib_names= extract_bib_files(tex_content)
        bib_names= [name for name in bib_names if name not in ['IEEEabrv','anthology']]

        bbl_count= 0
        bib_count= 0
        for bib_name in bib_names:
            bbl_path = os.path.join(tex_fold,bbl_file(bib_name))
            bib_path = os.path.join(tex_fold,bib_file(bib_name))
            if os.path.exists(bbl_path):
                bbl_count+=1
            elif os.path.exists(bib_path):
                bib_count+=1
        assert len(bib_names) == bbl_count + bib_count or os.path.exists(os.path.join(tex_fold,bbl_file(tex_name))), f'fail at {tex_path}, bbl_count={bbl_count}, bib_count={bib_count}, bib_names={bib_names}'
        
            
        if os.path.exists(os.path.join(tex_fold,bbl_file(tex_name))): ## in those case, we have already get the correct and complete bib reference in bbl file
            bbl_path = os.path.join(tex_fold,bbl_file(tex_name))
            # bbl_content = []
            # with open(bbl_path,'r', errors='ignore' ) as ffff:
            #     for line in ffff:bbl_content.append(line.strip())
            # bbl_content = '\n'.join(bbl_content)
            with open(bbl_path, "rb") as file:
                bbl_content = file.read()
                encoding = chardet.detect(bbl_content)["encoding"]
            with open(bbl_path,'r',encoding=encoding, errors='ignore') as ffff:
                bbl_content = ffff.read()
            
        elif bbl_count == len(bib_names):
            bbl_content = []
            for bib_name in bib_names:
                bbl_path = os.path.join(tex_fold,bbl_file(bib_name))
                with open(bbl_path, "rb") as file:
                    bbl_content = file.read()
                    encoding = chardet.detect(bbl_content)["encoding"]
                with open(bbl_path,'r', errors='ignore',encoding=encoding ) as ffff:
                    for line in ffff:
                        bbl_content.append(line.strip())
            bbl_content = '\n'.join(bbl_content)
        else:
            raise NotImplementedError(f'fail at {tex_path}, bbl_count={bbl_count}, bib_count={bib_count}, bib_names={bib_names}')
        
        if args.mode == 'plain_bbl':
            if 'bibitem' in bbl_content:
                bbl_content = parse_bbl_string_to_plain(bbl_content)

        if "begin{thebibliography}" not in bbl_content:
            bbl_content = "\\begin{thebibliography}[99]\n" + bbl_content + "\n\\end{thebibliography}"
        bib_pattern = r'\\bibliography{[^}]+}'
        # Replace the \bibliography command with the contents of bbl_content
        isusebiblio = re.search(bib_pattern, tex_content)

        if isusebiblio:
            # Replace the \bibliography command with the contents of bbl_content
            tex_content_updated = re.sub(bib_pattern, lambda match: bbl_content, tex_content)
        else:
            # print(os.path.join(tex_fold,bbl_file(tex_name)))
            # print(bbl_content)
            # print("=====================")
            end_document_pattern = r'\\end\{document\}'
            # If the \bibliography command is not found, add the contents of bbl_content before \end{document}
            tex_content_updated = re.sub(end_document_pattern, lambda match: bbl_content + '\n' + match.group(), tex_content)
        #tex_content_updated = re.sub(bib_pattern, lambda match: bbl_content, tex_content)
        
        os.rename(tex_path,tex_path+'.bk')
        #new_tex_path = os.path.join(tex_fold,"new."+tex_name+'.tex')
        with open(tex_path, 'w', encoding='utf-8') as file:
            file.write(tex_content_updated)

        Analysis['success_add_bib'] = Analysis.get('success_add_bib',[])+[tex_path]
        
    
    SAVE_ANALYSIS_PATH = "/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/analysis.tex_to_xml.pass.badbib/deal_with_bib_complete.whole_bbl_complete"
    os.makedirs(SAVE_ANALYSIS_PATH, exist_ok=True)
    print(f"analysis save at {SAVE_ANALYSIS_PATH}")
    if num_parts > 1:
        for key, val in Analysis.items():
            print(f"{key}=>{len(val)}")
            fold = os.path.join(SAVE_ANALYSIS_PATH,f"tex_to_xml.{key.lower()}.filelist.split")
            os.makedirs(fold, exist_ok=True)
            with open(os.path.join(fold,f"{start_index}-{end_index}"), 'w') as f:
                for line in (val):
                    f.write(line+'\n')
    else:
        #print(analysis)
        for key, val in Analysis.items():
            print(f"{key}=>{len(val)}")
            with open(os.path.join(SAVE_ANALYSIS_PATH,f"tex_to_xml.{key.lower()}.filelist"), 'w') as f:
                for line in set(val):
                    f.write(line+'\n')