
import re
from lxml import etree
from typing import List, Optional
import os
from tqdm.auto import tqdm
import numpy as np
import traceback,json
import argparse, logging
from pathlib import Path

def contains_arxiv_id(text):
    # Regular expression pattern for matching ArXiv IDs
    # It matches "arXiv:" or "arXiv" followed by optional space(s) and the ID pattern
    arxiv_pattern = r'arxiv:? *\s*(\d{4})\.(\d{3,4})(v\d+)?'
    
    # Search for the pattern in the text
    match = re.search(arxiv_pattern, text)
    
    # Return True if a match is found, False otherwise
    return match


def obtain_reference_list(tmp_xml_path,args):
    reference_string_path = tmp_xml_path.replace('reference.grobid.tei.xml','reference.txt')
    with open(reference_string_path,'r') as f:
        string_list = [line.strip() for line in f ]
    parser = etree.XMLParser(remove_comments=True)
    with open(tmp_xml_path) as f:
        tree = etree.parse(f, parser)  # get tree of XML hierarchy
    root=tree
    # Define the namespaces used in the XML data
    namespaces = {
        'tei': "http://www.tei-c.org/ns/1.0",
    }
    biblStructs = root.findall('.//tei:biblStruct', namespaces)
    assert len(biblStructs) == len(string_list), f"num_of_structured_ref:{len(biblStructs)} num_of_ref_string:{len(string_list)}, {tmp_xml_path}"

    reference_list=[]
    # Initialize an empty dictionary to store the extracted poolrmation
    bibliography = []

    # Iterate through each 'biblStruct' element in the XML
    for biblStruct,citation_string in zip(biblStructs,string_list):
        arxiv_match = contains_arxiv_id(citation_string.lower().strip('.'))
        unique_id = arxiv_match.group(0) if arxiv_match else None
        # Extract the ID of the biblStruct
        bib_id = biblStruct.get('{http://www.w3.org/XML/1998/namespace}id')
        
        # Initialize a dictionary to store the current biblStruct data
        bib_pool = {
            'title': None,
            'author': [],
            'imprint': {},
            'note': None,
            'journal': None,
            'journal_volume': None,
            'publisher':None,
            'content': citation_string
        }

        # Extract analytic (article-level) poolrmation, if any
        for analytic in biblStruct.findall('tei:analytic', namespaces):
            for title in analytic.findall('tei:title', namespaces):
                bib_pool['title']=(title.text or None)
            for author in analytic.findall('.//tei:author/tei:persName', namespaces):
                forename = ".".join(name.text.strip() for name in author.findall('.//tei:forename', namespaces))
                surname  = ".".join(name.text.strip() for name in author.findall('.//tei:surname', namespaces))
                author_name = f"{forename} {surname}"
                bib_pool['author'].append(author_name)

        # Extract monographic (book-level) poolrmation, if any
        for monogr in biblStruct.findall('tei:monogr', namespaces):
            for title in monogr.findall('tei:title', namespaces):
                bib_pool['journal']=(title.text or None)
            for imprint in monogr.findall('tei:imprint', namespaces):
                for item in imprint:
                    if item.tag.endswith('biblScope'):
                        bib_pool['imprint'][item.get('unit')] = item.get('from', item.text)
                    elif item.tag.endswith('date'):
                        bib_pool['imprint']['date'] = item.get('when')
                    elif item.tag.endswith('publisher'):
                        bib_pool['imprint']['publisher'] = item.text

        # Extract notes, if any
        for note in biblStruct.findall('tei:note', namespaces):
            bib_pool['note']=(note.text or None)
        
        
            
    #     reference_list.append(Reference(
    #         unique_id = unique_id,
    #             title = bib_pool['titles'][0] if len(bib_pool['titles'])>0 else None,
    #             author= bib_pool['authors'][0] if len(bib_pool['authors'])>0 else None,
    #             journal=bib_pool['journal'][0],
    #             journal_volume=bib_pool['imprint'].get('volume',None),
    #             journal_page=bib_pool['imprint'].get('page',None),
    #             year = bib_pool['imprint'].get('year',None),
    #             publisher = bib_pool['imprint'].get('publisher',None),
    #         content=citation_string,
            
    #     ))
        # Add the current biblStruct to the bibliography dictionary
        bibliography.append(bib_pool)

    return bibliography


def process_one_path(ROOTPATH, args):
    if not os.path.exists(ROOTPATH):
        return ROOTPATH, 'no_root'
    filepath = os.path.join(ROOTPATH,'reference.grobid.tei.xml')
    targetpath=os.path.join(ROOTPATH,'reference.structured.grobid.jsonl')
    
    # bad_reference_path = Path(ROOTPATH).glob("reference_*")
    # for bad_reference in bad_reference_path:
    #     #print(bad_reference)
    #     #raise
    #     os.remove(bad_reference)
    reference_path = os.path.join(ROOTPATH,'reference.txt')
    if not os.path.exists(reference_path):
        return ROOTPATH, 'no_ref_file'
    if os.path.getsize(reference_path) == 0:
        return ROOTPATH, 'empty_ref_file'
    if not os.path.exists(filepath):
        return ROOTPATH,'no_source'
    if os.path.exists(targetpath) and not args.redo:
        return ROOTPATH,'skip'
    try:
        bibliography = obtain_reference_list(filepath, args)
        with open(targetpath,'w') as f: 
            json.dump(bibliography,f)
        return ROOTPATH,'pass'
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except:
        return ROOTPATH,'fail'
    
def process_one_file_wrapper(args):
    arxiv_path, args = args
    return process_one_path(arxiv_path,args)

if __name__ == '__main__':
    # import sys
    # assert len(sys.argv)==2
    # INPUTPATH =sys.argv[1]
    # assert "reference.grobid.tei.xml "in INPUTPATH
    # bibliography_list = obtain_reference_list(INPUTPATH)
    # for i,ref in enumerate(bibliography_list):
    #     print(f"Reference {i+1}")
    #     print(get_print_namespace_tree(ref))
    import os
    import sys
    from tqdm.auto import tqdm
    import numpy as np
    import traceback,json
    import argparse, logging
    from pathlib import Path
    parser = argparse.ArgumentParser()
    parser.add_argument("--root_path", type=str)
    parser.add_argument("--index_part", type=int, default=0)
    parser.add_argument('--num_parts', type=int, default=1)
    # parser.add_argument('--mode', type=str, default='analysis')
    # parser.add_argument('--verbose', '-v', action='store_true', help='', default=False)
    # parser.add_argument('--redo',  action='store_true', help='', default=False)

    args = parser.parse_args()
    
    filelistpath = args.root_path
    analysis = {}
    if os.path.isdir(filelistpath):
        if filelistpath.endswith('archive_json'):
            root_path = filelistpath
            while not root_path.endswith('whole_arxiv_all_files'):
                root_path = os.path.dirname(root_path)
                assert root_path != '/'
            root_path = os.path.join(root_path,'analysis.parse_reference')
            print(root_path)
            os.makedirs(root_path,exist_ok=True)
            ROOTPATH = filelistpath
            all_file_list = os.listdir(ROOTPATH)
            all_file_list = [os.path.join(ROOTPATH, DIRNAME) for DIRNAME in all_file_list]
        else:
            all_file_list = [filelistpath]
    elif os.path.isfile(filelistpath):
        root_path = filelistpath
        while not root_path.endswith('whole_arxiv_all_files'):
            root_path = os.path.dirname(root_path)
            assert root_path != '/'
        root_path = os.path.join(root_path,'analysis.parse_reference')
        #root_path= os.path.join(os.path.dirname(os.path.dirname(filelistpath)),'analysis.tex_to_xml')
        print(root_path)
        os.makedirs(root_path,exist_ok=True)
        with open(filelistpath,'r') as f:
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
        
    #alread_processing_file_list = ['1303.3256']
    fail_filenames=[]
    for i,ROOTPATH in enumerate(tqdm(all_file_list)):
        if not os.path.exists(ROOTPATH):
            analysis['no_root'] = analysis.get('no_root',[]) + [ROOTPATH]
            continue
        filepath = os.path.join(ROOTPATH,'reference.grobid.tei.xml')
        targetpath=os.path.join(ROOTPATH,'reference.structured.grobid.jsonl')
        
        bad_reference_path = Path(ROOTPATH).glob("reference_*")
        for bad_reference in bad_reference_path:
            #print(bad_reference)
            #raise
            os.remove(bad_reference)
        reference_path = os.path.join(ROOTPATH,'reference.txt')
        if not os.path.exists(reference_path):
            analysis['no_ref_file'] = analysis.get('no_ref_file',[]) + [ROOTPATH]
            continue
        if os.path.getsize(reference_path) == 0:
            analysis['empty_ref_file'] = analysis.get('empty_ref_file',[]) + [ROOTPATH]
            continue
        if not os.path.exists(filepath):
            analysis['no_source'] = analysis.get('no_source',[]) + [ROOTPATH]
            continue
        if os.path.exists(targetpath):
            analysis['skip'] = analysis.get('skip',[]) + [ROOTPATH]
            continue
        try:
            bibliography = obtain_reference_list(filepath)
            with open(targetpath,'w') as f: 
                json.dump(bibliography,f)
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except:
            analysis['fail'] = analysis.get('fail',[]) + [ROOTPATH]
        
        # except:
        #     fail_filenames.append(filename) 
        #     traceback.print_exc() 
    #print(f"fail case {len(fail_filenames)}")
    
    root_path = '/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/analysis.reterive_reference/convert_grobid/'
    os.makedirs(root_path,exist_ok=True)
    if num_parts > 1:
        for key, val in analysis.items():
            print(f"{key}=>{len(val)}")
            fold = os.path.join(root_path,f"{key.lower()}.filelist.split")
            os.makedirs(fold, exist_ok=True)
            with open(os.path.join(fold,f"{start_index}-{end_index}"), 'w') as f:
                for line in (val):
                    f.write(line+'\n')
    else:
        #print(analysis)
        for key, val in analysis.items():
            print(f"{key}=>{len(val)}")
            with open(os.path.join(root_path,f"{key.lower()}.filelist"), 'w') as f:
                for line in set(val):
                    f.write(line+'\n')
