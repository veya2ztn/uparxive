import re
import sys
import os,json
from tqdm.auto import tqdm
import re

def is_valid_citation(citation):
    # Simple heuristic:
    # 1. Check if there's a year (four digits) in the citation.
    # 2. Check if the citation starts with an uppercase letter.
    year_pattern = re.compile(r'\b(19|20)\d{2}\b')
    citation = citation.strip(" .;:,!?")
    starts_with_uppercase = citation and citation[0].isupper()
    #print(citation, "==>", starts_with_uppercase)
    return starts_with_uppercase and len(citation.split())>10 and not citation.lower().startswith('doi')

def split_citations(citation_text):
    citation_text = citation_text.strip(" .;:,")

    # Split based on semicolon
    possible_citations = citation_text.split(';')

    # Initialize variables
    valid_citations = []
    last_citation = ""
    for new_citation in possible_citations:
        new_citation  = new_citation.strip(" .;:,!?")
        if is_valid_citation(new_citation):
            if last_citation:valid_citations.append(last_citation)
            last_citation = new_citation
        else:
            last_citation = last_citation + new_citation + ';'

    # Check for any remaining citation at the end
    if last_citation and is_valid_citation(last_citation):
        valid_citations.append(last_citation)

    return valid_citations


if __name__ == '__main__':
    import os
    import sys
    from tqdm.auto import tqdm
    import numpy as np
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--root_path", type=str)
    parser.add_argument("--index_part", type=int, default=0)
    parser.add_argument('--num_parts', type=int, default=1)
    parser.add_argument('--redo', action='store_true', help='', default=False)

    args = parser.parse_args()
    verbose = False
    ROOT_PATH = args.root_path# '/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/successed_xml.filelist'
    if os.path.isfile(ROOT_PATH):
        #raise NotImplementedError
        if ROOT_PATH.endswith('.xml'):
            alread_processing_file_list = [ROOT_PATH]
        else:
            with open(ROOT_PATH,'r') as f:
                alread_processing_file_list = [t.strip() for t in f.readlines()]
            
    elif os.path.isdir(ROOT_PATH):
        ROOTDIR = ROOT_PATH.rstrip('/')
        if ROOTDIR.endswith('Reference'):
            alread_processing_file_list = [ROOTDIR]
        else:
            alread_processing_file_list = os.listdir(ROOT_PATH)
    else:
        raise NotImplementedError
    index_part= args.index_part
    num_parts = args.num_parts 
    totally_paper_num = len(alread_processing_file_list)

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
    #ROOTDIR=sys.argv[1] #"/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_old_quant_ph/unprocessed_json/"
    #alread_processing_file_list = os.listdir(ROOTDIR)

    alex_results     = []
    semantic_results = []
    citation_jsons   = []
    citation_keyss   = []
    citation_strings =[]
    count = 0
    string_colloect= []
    for i,filename in tqdm(enumerate(alread_processing_file_list),total=len(alread_processing_file_list)):
        if "/" not in filename:
            filepath = os.path.join(ROOTDIR,filename)
        else:
            filepath = filename
        filelist = os.listdir(filepath)
        splited_ref =False
        if not os.path.exists(os.path.join(filepath,'reference.txt')) and not os.path.exists(os.path.join(filepath,'reference.txt.bk')):continue

        if os.path.exists(os.path.join(filepath,'reference.keys.bk')):
            continue
            # below is clean processing
            os.rename(os.path.join(filepath,'reference.keys.bk'),os.path.join(filepath,'reference.keys'))
            os.rename(os.path.join(filepath,'reference.txt.bk'),os.path.join(filepath,'reference.txt'))
            name_list =  [
                          'reference.grobid.tei.xml',
                          'reference.structured.jsonl', 
                          'reference.structured.anystyle.jsonl', 
                          'reference.structured.grobid.jsonl', 
                        #   'reference.keys.done','reference.txt.done',
                        #   'reference.structured.jsonl.done',
                        #   'reference.es_retrived_citation.json.done', 
                        #   'reference.es_retrived_citation.json',
                        #   'reference.es_retrived_citation.json',
                        #   'reference.es_retrived_citation.json.done'
                          ]
            for name in name_list:
                path = os.path.join(filepath,name)
                if os.path.exists(path):
                    os.remove(f"{path}")
            continue
        
        with open(os.path.join(filepath,'reference.keys'),'r') as f: citation_keys   = [line.strip() for line in f ]
        with open(os.path.join(filepath,'reference.txt'),'r') as f:  citation_string = [line.strip() for line in f ]
        
        ### we will check the citation string and split then via ;
        single_citation_string = []
        single_citation_keys   = []
        for key, citation in zip(citation_keys,citation_string):
            citation = citation.strip(" .;:,")
            for string in split_citations(citation):
                string = string.strip()
                if len(string)==0:continue
                single_citation_string.append(string)
                single_citation_keys.append(key)
        os.rename(os.path.join(filepath,'reference.keys'),os.path.join(filepath,'reference.keys.bk'))
        os.rename(os.path.join(filepath,'reference.txt'),os.path.join(filepath,'reference.txt.bk'))
        with open(os.path.join(filepath,'reference.keys'),'w') as f: 
            for line in single_citation_keys: f.write(line+'\n')
        with open(os.path.join(filepath,'reference.txt'), 'w') as f:  
            for line in single_citation_string: f.write(line+'\n')

                