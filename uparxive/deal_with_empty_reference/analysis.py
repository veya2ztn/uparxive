import os,re,sys,json
from pathlib import Path
from tqdm.auto import tqdm
import re
module_dir = str(Path(__file__).resolve().parent)
if module_dir not in sys.path:sys.path.append(module_dir)
from utils import *
import argparse
import os
import sys
from tqdm.auto import tqdm
import numpy as np
import traceback
parser = argparse.ArgumentParser()
parser.add_argument("--root_path", type=str)
parser.add_argument('--mode', type=str)
args = parser.parse_args()
### lets firstly deal with the empty reference case, which is always due to the bib problem.
### In modern tex standard, the bib information always in a seperate file .bib, thus we will roll back those task into tex_to_xml processing

ROOT = args.root_path  #sys.argv[1]#'/nvme/zhangtianning.di/datasets/LLM/arxiv/whole_arxiv_all_cs'
if args.mode == 'get_filelist':
    all_ready_json_arxiv_ids = []
    not_ready_json_arxiv_ids = []
    why_not_reference_list   = []
    JSONROOT= os.path.join(ROOT,"unprocessed_json")
    SAVEPATH = os.path.join(ROOT,'analysis.xml_to_json')
    os.makedirs(SAVEPATH, exist_ok=True)
    arxiv_ids = os.listdir(JSONROOT)
    for arxivid in tqdm(arxiv_ids):
        arxiv_path = os.path.join(JSONROOT, arxivid)
        reference_path = os.path.join(arxiv_path, "reference.txt")
        if not os.path.exists(reference_path):
            why_not_reference_list.append(arxivid)
        elif os.path.getsize(reference_path) > 0:
            all_ready_json_arxiv_ids.append(arxivid)
        else:
            not_ready_json_arxiv_ids.append(arxivid)

    with open(os.path.join(SAVEPATH,'tex_to_xml.no_reference'),'w') as f:
        for task in not_ready_json_arxiv_ids: 
            f.write(task+'\n')
    with open(os.path.join(SAVEPATH,'tex_to_xml.empty_reference'),'w') as f:
        for task in not_ready_json_arxiv_ids: 
            f.write(task+'\n')
    with open(os.path.join(SAVEPATH,'tex_to_xml.pass'),'w') as f:
        for task in all_ready_json_arxiv_ids: 
            f.write(task+'\n')

    # reference_filelist = list(Path(os.path.join(ROOT,"unprocessed_json")).glob("*/reference.txt"))
    # empty_ref_arxiv_id = [os.path.basename(os.path.dirname(reference_path)) for reference_path in reference_filelist if os.path.getsize(reference_path) == 0] #
    print(f"all_ready_json_arxiv_ids: {len(all_ready_json_arxiv_ids)}")
    print(f"not_ready_json_arxiv_ids: {len(not_ready_json_arxiv_ids)}")
    print(f"why_not_reference_list: {len(why_not_reference_list)}")
    exit()

if args.mode == 'analysis':
    print("loading empty reference arxiv id list")
    with open(os.path.join(ROOT,'analysis.xml_to_json', 'tex_to_xml.empty_reference'),'r') as f:
        empty_ref_arxiv_id = [t.strip() for t in f.readlines()]
    ### load the main tex file for each arxiv id
        
    print("loading arxiv id to tex.root ")
    arxiv_id_to_root_tex_name = {}
    with open(os.path.join(ROOT,"root_found.filelist"),'r') as f:
        for tex_path in f:
            tex_path = tex_path.strip()
            tex_name = os.path.basename(tex_path)
            arxiv_id = os.path.basename(os.path.dirname(tex_path))
            arxiv_id_to_root_tex_name[arxiv_id] = tex_name

    noref_in_tex_but_has_bbl_in_fold = []
    noref_in_tex_but_has_bib_in_fold = []
    noref_in_tex_but_has_other_bib_in_fold = []
    noref_in_tex_and_even_no_cite_in_content = []

    noref_in_tex_but_has_bbl_in_fold_filelist=[]
    noref_in_tex_but_has_bib_in_fold_filelist=[]

    ref_complete_whole_bbl_complete_arxiv_ids = []
    ref_complete_whole_bbl_complete_arxiv_ids_filelist=[]
    ref_complete_part_bbl_complete_arxiv_arxiv_ids = []
    ref_complete_only_bib_complete_arxiv_arxiv_ids = []
    ref_complete_only_bib_complete_arxiv_arxiv_ids_filelist=[]
    ref_imcomplete_hasbbl_arxiv_ids  = []
    ref_imcomplete_hasbib_arxiv_ids  = []
    ref_imcomplete_nobib_arxiv_ids   = []
    what_is_this = []
    #empty_ref_arxiv_id=['1612.03101']
    for arxiv_id in tqdm(empty_ref_arxiv_id):
        tex_fold = os.path.join(ROOT,"unprocessed_tex",arxiv_id)
        if not os.path.exists(tex_fold):
            tqdm.write(f"this arxiv id={arxiv_id} not in unprocessed_tex")
            continue
        if arxiv_id not in arxiv_id_to_root_tex_name:
            tqdm.write(f"this arxiv id={arxiv_id} not in arxiv_id_to_root_tex_name")
            continue
        tex_name = arxiv_id_to_root_tex_name[arxiv_id]
        tex_path = os.path.join(tex_fold,tex_name)
        tex_name = tex_name.replace('.tex','')
        with open(tex_path, 'r', encoding='utf-8', errors='ignore') as file:lines = file.readlines()
        lines = [line for line in lines if not line.strip().startswith('%')]
        tex_content = ''.join(lines)

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
        #print(f"arxiv_id: {arxiv_id}, bbl_count: {bbl_count}, bib_count: {bib_count}, bib_names: {bib_names}")
        
        if len(bib_names) ==0:
            if os.path.exists(os.path.join(tex_fold,bbl_file(tex_name))):
                noref_in_tex_but_has_bbl_in_fold.append(arxiv_id)
                noref_in_tex_but_has_bbl_in_fold_filelist.append(tex_path)
            elif os.path.exists(os.path.join(tex_fold,tex_name+'.bib')):
                noref_in_tex_but_has_bib_in_fold.append(arxiv_id)
                noref_in_tex_but_has_bib_in_fold_filelist.append(tex_path)
            else:
                with open(os.path.join(ROOT,"unprocessed_json",arxiv_id,arxiv_id+'.json'),'r') as f:
                    final_output = json.load(f)
                
                if len(final_output['missing_citation_labels']) == 0:
                    noref_in_tex_and_even_no_cite_in_content.append(arxiv_id)
                else:
                    noref_in_tex_but_has_other_bib_in_fold.append(arxiv_id)
        else:
            if len(bib_names) == bbl_count + bib_count:
                if bbl_count == len(bib_names):
                    ref_complete_whole_bbl_complete_arxiv_ids.append(arxiv_id)
                    ref_complete_whole_bbl_complete_arxiv_ids_filelist.append(tex_path)
                elif os.path.exists(os.path.join(tex_fold,bbl_file(tex_name))):
                    #if tex_name in bib_names or os.path.exists(os.path.join(tex_fold,bbl_file(tex_name))): ## in those case, we have already get the correct and complete bib reference in bbl file
                    ref_complete_whole_bbl_complete_arxiv_ids.append(arxiv_id)
                    ref_complete_whole_bbl_complete_arxiv_ids_filelist.append(tex_path)
    
                elif bbl_count > 0:
                    ref_complete_part_bbl_complete_arxiv_arxiv_ids.append(arxiv_id)        
                elif bib_count > 0:
                    ref_complete_only_bib_complete_arxiv_arxiv_ids.append(arxiv_id)
                    ref_complete_only_bib_complete_arxiv_arxiv_ids_filelist.append(arxiv_id)

            else:
                if os.path.exists(os.path.join(tex_fold,bbl_file(tex_name))):
                    ref_complete_whole_bbl_complete_arxiv_ids.append(arxiv_id)  ### <--- this mean it use other .bib file in tex but we can find temp bbl in the fold
                    ref_complete_whole_bbl_complete_arxiv_ids_filelist.append(tex_path)
                elif bbl_count > 0:
                    ref_imcomplete_hasbbl_arxiv_ids.append(arxiv_id)
                elif bib_count > 0:
                    ref_imcomplete_hasbib_arxiv_ids.append(arxiv_id)
                else:
                    ref_imcomplete_nobib_arxiv_ids.append(arxiv_id)

    print(f"noref_in_tex_but_has_bbl_in_fold: {len(noref_in_tex_but_has_bbl_in_fold)}")
    print(f"noref_in_tex_but_has_bib_in_fold: {len(noref_in_tex_but_has_bib_in_fold)}")
    print(f"noref_in_tex_but_has_other_bib_in_fold: {len(noref_in_tex_but_has_other_bib_in_fold)}")
    print(f"noref_in_tex_and_even_no_cite_in_content:{len(noref_in_tex_and_even_no_cite_in_content)}")
    print(f"ref_complete_whole_bbl_complete_arxiv_ids: {len(ref_complete_whole_bbl_complete_arxiv_ids)}")
    print(f"ref_complete_part_bbl_complete_arxiv_arxiv_ids: {len(ref_complete_part_bbl_complete_arxiv_arxiv_ids)}")
    print(f"ref_complete_only_bib_complete_arxiv_arxiv_ids: {len(ref_complete_only_bib_complete_arxiv_arxiv_ids)}")
    print(f"ref_imcomplete_hasbbl_arxiv_ids: {len(ref_imcomplete_hasbbl_arxiv_ids)}")
    print(f"ref_imcomplete_hasbib_arxiv_ids: {len(ref_imcomplete_hasbib_arxiv_ids)}")
    print(f"ref_imcomplete_nobib_arxiv_ids: {len(ref_imcomplete_nobib_arxiv_ids)}")



    SAVEPATH = os.path.join(ROOT,'analysis.tex_to_xml.pass.badbib')
    os.makedirs(SAVEPATH,exist_ok=True)
    with open(os.path.join(SAVEPATH,'tex_to_xml.pass.no_need_bbl_information'),'w') as f:
        for task in noref_in_tex_and_even_no_cite_in_content: 
            f.write(task+'\n')
    ### better save pathlist after 'deal_with_function'
    # with open(os.path.join(SAVEPATH,'tex_to_xml.pass.badbib.noref.but_has_bbl.pathlist'),'w') as f:
    #     for task in noref_in_tex_but_has_bbl_in_fold_filelist: 
    #         f.write(task+'\n')
    # with open(os.path.join(SAVEPATH,'tex_to_xml.pass.badbib.noref.but_has_bib.pathlist'),'w') as f:
    #     for task in noref_in_tex_but_has_bib_in_fold_filelist: 
    #         f.write(task+'\n')
    # with open(os.path.join(SAVEPATH,'tex_to_xml.pass.badbib.but_bib_complete.whole_bbl_complete.pathlist'),'w') as f:
    #     for task in ref_complete_whole_bbl_complete_arxiv_ids_filelist: 
    #         f.write(task+'\n')
    # with open(os.path.join(SAVEPATH,'tex_to_xml.pass.badbib.but_bib_complete.only_bib_complete.pathlist'),'w') as f: 
    #     for task in ref_complete_only_bib_complete_arxiv_arxiv_ids_filelist: 
    #         f.write(task+'\n')        
    with open(os.path.join(SAVEPATH,'tex_to_xml.pass.badbib.noref.but_has_other_bib'),'w') as f:
        for task in noref_in_tex_but_has_other_bib_in_fold: 
            f.write(task+'\n')

    with open(os.path.join(SAVEPATH,'tex_to_xml.pass.badbib.noref.but_has_bbl'),'w') as f:
        for task in noref_in_tex_but_has_bbl_in_fold: 
            f.write(task+'\n')

    with open(os.path.join(SAVEPATH,'tex_to_xml.pass.badbib.noref.but_has_bib'),'w') as f:
        for task in noref_in_tex_but_has_bib_in_fold: 
            f.write(task+'\n')

    with open(os.path.join(SAVEPATH,'tex_to_xml.pass.badbib.but_bib_complete.whole_bbl_complete'),'w') as f:
        for task in ref_complete_whole_bbl_complete_arxiv_ids: 
            f.write(task+'\n')

    with open(os.path.join(SAVEPATH,'tex_to_xml.pass.badbib.but_bib_complete.part_bbl_complete'),'w') as f: 
        for task in ref_complete_part_bbl_complete_arxiv_arxiv_ids: 
            f.write(task+'\n')
    with open(os.path.join(SAVEPATH,'tex_to_xml.pass.badbib.but_bib_complete.only_bib_complete'),'w') as f: 
        for task in ref_complete_only_bib_complete_arxiv_arxiv_ids: 
            f.write(task+'\n')

    with open(os.path.join(SAVEPATH,'tex_to_xml.pass.badbib.bib_incomplete.hasbbl'),'w') as f:
        for task in ref_imcomplete_hasbbl_arxiv_ids: 
            f.write(task+'\n')  
    with open(os.path.join(SAVEPATH,'tex_to_xml.pass.badbib.bib_incomplete.hasbib'),'w') as f:
        for task in ref_imcomplete_hasbib_arxiv_ids: 
            f.write(task+'\n')
    with open(os.path.join(SAVEPATH,'tex_to_xml.pass.badbib.bib_incomplete.nobib'),'w') as f:
        for task in ref_imcomplete_nobib_arxiv_ids: 
            f.write(task+'\n')

        
    import matplotlib.pyplot as plt
    def func(pct, allvals):
        absolute = int(pct/100.*sum(allvals))  # Calculates the absolute number from percentage
        return "{:.1f}%\n({:d})".format(pct, absolute)  # Format the label
    data = [len(ref_complete_whole_bbl_complete_arxiv_ids),len(ref_complete_part_bbl_complete_arxiv_arxiv_ids),len(ref_complete_only_bib_complete_arxiv_arxiv_ids),len(ref_imcomplete_hasbbl_arxiv_ids),len(ref_imcomplete_hasbib_arxiv_ids)]
    keys = ['whole_bbl_complete','part_bbl_complete','only_bib_complete','hasbbl','hasbib']
    plt.figure(figsize=(10, 7))
    plt.pie(data, labels=keys, autopct=lambda pct: func(pct, data), startangle=140)
    plt.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.title('Case Distribution')
    plt.show()
    plt.savefig(os.path.join(SAVEPATH,"tex_to_xml.pass.badbib.case_distribution.png"))