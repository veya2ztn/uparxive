import pandas as pd
import os
from tqdm.auto import tqdm
import glob
import networkx as nx
import re

def extract_missing_file(text):
    missing_file_pattern = r"missing file\[(.*?)\]"

    missing_file_match = re.search(missing_file_pattern, text)

    missing_file = missing_file_match.group(1) if missing_file_match else None

    return missing_file

def extract_numbers(input_string):
    warning_pattern=r'(\d+)\swarning'
    error_pattern = r'(\d+)\serror'
    undefined_macro_pattern = r'(\d+)\sundefined macros'
    missing_file_pattern = r'(\d+)\smissing file'
    
    warnings=re.search(warning_pattern, input_string)
    errors = re.search(error_pattern, input_string)
    undefined_macros = re.search(undefined_macro_pattern, input_string)
    missing_files = re.search(missing_file_pattern, input_string)
    
    num_warnings= int(warnings.group(1)) if warnings else 0
    num_errors = int(errors.group(1)) if errors else 0
    num_undefined_macros = int(undefined_macros.group(1)) if undefined_macros else 0
    num_missing_files = int(missing_files.group(1)) if missing_files else 0

    return num_warnings,num_errors, num_undefined_macros, num_missing_files

def find_the_root_tex(tex_files):
    G = nx.DiGraph()

    for file_path in tex_files:
        _dir, file = os.path.split(file_path)
        with open(file_path, 'r', errors='ignore') as f:
            contents = f.read()
        # Add the current file as a node in the graph
        G.add_node(file)
        # Find \input{} or \include{} commands
        inputs = re.findall(r'\\(input|include)(?:\{(.+?)\}| ([^\s]+))', contents)
        #print(inputs)
        for _, input_braces, input_space in inputs:
            # Determine the correct input file
            input_file = input_braces or input_space
            input_file = input_file.split("\\")[0].strip('{}%')
            #print(input_file)
            # Add the .tex extension to input file if it's not there
            if not input_file.endswith('.tex'):
                input_file += '.tex'
            # Add the input file as a node (if it's not already) and the edge
            G.add_node(input_file)
            G.add_edge(file, input_file)

    # The main file is a node with no incoming edges (in-degree of 0) but with outgoing edges (out-degree > 0)
    main_files = [os.path.join(_dir,node) for node, degree in G.degree() if G.in_degree(node) == 0 and G.out_degree(node) > 0]
    return main_files

import re
def package_replace(file, old_package_name, new_package_name):
    

    # Open the file
    with open(file, "r") as f:
        data = f.read()

    # Use regular expressions to replace 'amssym' with 'amssymb' in \usepackage{amssym}
    data = re.sub('\\\\usepackage\\{' + old_package_name + '\\}', 
                  '\\\\usepackage{' + new_package_name + '}', data)

    # Write the data back to the file
    with open(file, "w") as f:
        f.write(data)

package_name = {
    'amssym':'amssymb',
    'subeqnar':'subeqnarray'
}


def find_the_fail_xml_path(ROOTPATH="data/whole_arxiv_quant_ph/unprocessed_xml"):
    FAIL_PATH= []
    READ_PATH= []
    package_needed = {}

    for DIRNAME in tqdm(os.listdir(ROOTPATH)):
        DIR = os.path.join(ROOTPATH, DIRNAME)
        #texfiles = glob.glob(os.path.join(DIR, '*.tex'), recursive=False)
        logfiles = glob.glob(os.path.join(DIR, '*.log'), recursive=False)
        error_file = False
        if len(logfiles) > 1:
            error_file = True
            fail_reason = "more than one log file"
        elif len(logfiles) == 0:
            error_file = True
            fail_reason = "no log file"
            print(f"{DIR} dont have log")
        else:
            logfile  = logfiles[0]
            with open(logfile, 'r') as f:last_line = f.readlines()[-2]
            if 'error' in last_line:
                error_file = True
                fail_reason = last_line
                num_warnings,error_count, missing_macros_count, missing_file_count = extract_numbers(last_line)            
                if error_count <= missing_macros_count + missing_file_count:
                    # this is normal case that most macros dones not loaded or tex missing
                    # should suppose it will now destroy the paper flow
                    missing_file = extract_missing_file(last_line)
                    error_file = False
                    if missing_file and 'sty' in missing_file:
                        if missing_file not in package_needed:package_needed[missing_file]=[]
                        package_needed[missing_file].append(DIR)
                        missing_name = missing_file.replace('.sty','')
                        if missing_name in package_name:
                            new_name = package_name[missing_name]
                            the_dir  = DIR.replace('whole_arxiv_quant_ph_xml','whole_arxiv_quant_ph_tex')
                            texfiles = glob.glob(os.path.join(the_dir, '*.tex'), recursive=False)
                            if len(texfiles)>1:
                                main_file = find_the_root_tex(texfiles)
                            else:
                                main_file = texfiles
                            if len(main_file) ==0:
                                raise NotImplementedError( f"checkfile {the_dir}")
                            main_file = main_file[0]
                            print(f"replace {missing_name} to {new_name} in {main_file}")
                            package_replace(main_file,missing_name,new_name)
                            error_file = True
                        print(missing_file, DIR, "\n","========================")
        if error_file:
            #print(fail_reason)
            FAIL_PATH.append([DIRNAME,fail_reason])
            #os.system(f'rm ')
        else:
            READ_PATH.append(DIRNAME)
    return FAIL_PATH,READ_PATH

def find_the_correct_tex(filelist_all,ROOTPATH="data/whole_arxiv_quant_ph/unprocessed_tex"):
    REMAKE_FILES=[]
    multifiles_case = []
    main_file_miss_case=[]
    for DIRNAME in tqdm(filelist_all):
        DIR = os.path.join(ROOTPATH, DIRNAME)
        texfiles = (glob.glob(os.path.join(DIR, '*.tex'), recursive=False) +
                    glob.glob(os.path.join(DIR, '*.TEX'), recursive=False)
                    )
        if len(texfiles)==0:
            main_file_miss_case.append(DIR)
            #print(f"{DIR} dont have tex???")
            continue
        if len(texfiles)>1:
            
            main_file = find_the_root_tex(texfiles)
            if len(main_file)>1:
                multifiles_case.append(DIR)
                continue
            
        else:
            main_file = texfiles
        if len(main_file)==0:
            main_file_miss_case.append(DIR)
            #print(f"{DIR} dont have main file")
            continue
        REMAKE_FILES.append(main_file[0])   
    return REMAKE_FILES, multifiles_case, main_file_miss_case


if __name__ == '__main__':
    import sys
    import os
    assert len(sys.argv)==2 
    xml_path = sys.argv[1]#"data/whole_arxiv_quant_ph/unprocessed_xml"
    tex_paht = xml_path.replace('unprocessed_xml','unprocessed_tex')
    root_path= os.path.dirname(xml_path)
    FAIL_PATH,READ_PATH = find_the_fail_xml_path(ROOTPATH=xml_path)
    filelist = [a for a,b in FAIL_PATH]

    with open(f'{root_path}/fail_reason_list','w') as f:
        for a,b in FAIL_PATH:
            f.write(f"{a}=>{b}"+'\n')
   
    with open('filelists/ready_file','w') as f:
        for a in READ_PATH:
            f.write(a+'\n')

    
    if len(filelist)>0:
        print(f" detected {len(filelist)} failed project in xml dir, from {filelist[0]} to {filelist[-1]}")

    Should_Finished_FILELIST=set(os.listdir("data/whole_arxiv_quant_ph/unprocessed_tex/"))
    So_far_we_have_processed=set(os.listdir("data/whole_arxiv_quant_ph/unprocessed_xml/"))
    So_far_yet_precessed_file= Should_Finished_FILELIST - So_far_we_have_processed
    print(f"there are {len(So_far_yet_precessed_file)} fold that won't get processed")

    filelist_all = set(filelist) | So_far_yet_precessed_file

    print(f"totally we need process {len(filelist_all)} files")


    REMAKE_FILES, multifiles_case, main_file_miss_case= find_the_correct_tex(filelist_all)

    print(f"you need remake {len(REMAKE_FILES)} folds")
    print(f"there are {len(multifiles_case)} cases failed due to multitex compiled in one project")
    print(f"there are {len(main_file_miss_case)} cases failed due to no main tex file")

    with open('filelists/filelist_multimain','w') as f:
        for a in multifiles_case:
            f.write(a+'\n')

    with open('filelists/filelist_mainmiss','w') as f:
        for a in main_file_miss_case:
            f.write(a+'\n')

    with open('filelists/filelist_remake','w') as f:
        for a in REMAKE_FILES:
            f.write(a+'\n')
    
    # for a in READ_PATH:
    #     os.system(f"mv data/whole_arxiv_quant_ph/unprocessed_tex/{a} data/whole_arxiv_quant_ph/successed_tex/{a}")
# ROOTPATH="data/whole_arxiv_quant_ph_xml/"
# print(f" we will remove failed fold !!!!")
# for DIRNAME in tqdm(filelist):
#     DIR = os.path.join(ROOTPATH, DIRNAME)
#     os.system(f'rm -rf {DIR}')