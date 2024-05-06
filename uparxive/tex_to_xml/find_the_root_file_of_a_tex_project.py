
import os,re
from tqdm.auto import tqdm
import networkx as nx
from .standalize_tex import read_the_tex_file_into_memory_without_comment
from uparxive.batch_run_utils import BatchModeConfig, dataclass
from uparxive.utils import isHardTexFile
from typing import Tuple,Dict

softblacklist = ['.clean.','.revtex.','.nopackage.']
blacklist     = ['.synctex.tex']#,'bare_t-ase_jrnl']
our_processed_arxiv_flag = softblacklist + blacklist

@dataclass 
class FindRootConfig(BatchModeConfig):
    verbose: bool = False
    task_name = 'find_root'
    def from_dict(d):
        return BatchModeConfig(**d)
def find_the_root_tex(tex_files,arxiv_path,content_check=False):
    G = nx.DiGraph()

    nodename_pool = {}
    for file_path in tex_files:
        if not os.path.isfile(file_path):continue
        filename = os.path.relpath(file_path, arxiv_path)
        contents = read_the_tex_file_into_memory_without_comment(file_path)
        contents = "\n".join(contents)
        if content_check and r"\begin{document}" not in contents:continue
        if len(contents) == 0: continue
        #print(f"add note {filename}")
        nodename = filename.lower().replace('.tex',"")
        nodename_pool[nodename] = filename
        G.add_node(nodename)
        # Find \input{} or \include{} commands
        inputs = re.findall(r'\\(input|include)(?:\{(.+?)\}| ([^\s]+))', contents)
        #print(inputs)
        for _, input_braces, input_space in inputs:
            # Determine the correct input file
            input_file = input_braces or input_space
            input_file = input_file.split("\\")[0].strip('{}%')
            subnodename = input_file.lower().replace('.tex',"")
            nodename_pool[subnodename] = input_file
            # Add the input file as a node (if it's not already) and the edge
            G.add_node(subnodename)
            G.add_edge(nodename, subnodename)

    main_files = [os.path.join(arxiv_path,nodename_pool[node]) for node, degree in G.degree() if G.in_degree(node) == 0 and G.out_degree(node) >=0]
    return main_files


def check_is_supplemtary(filename):
    if filename in ['supp.tex', 'appendix.tex', 'supplementary.tex','app.tex']:
        return True
    for flag in ['supplement', 'appendix']:
        if flag in filename:
            return True
    for postfix in ['suppl.tex', 'appendix']:
        if filename.endswith(postfix):
            return True
    return False


def checkmainfile(main_file, arxiv_path):
    if len(main_file) == 1:
        return main_file, 'root_file'
    else:
        ### deal with filename is main.tex
        for filepath in main_file:
            filename = os.path.basename(filepath).lower().replace('.tex','')
            if filename == 'main':
                main_file = [filepath]
                return main_file, 'root_file'

        ### deal with has .bbl file
        bblnames = [filename for filename in os.listdir(arxiv_path) if filename.endswith('bbl')]
        if len(bblnames) ==1:
            texname = bblnames[0].replace('.bbl','.tex')
            texpath = os.path.join(arxiv_path, texname)
            if os.path.exists(texpath): 
                main_file = [texpath]
                return main_file, 'root_file'

        ### deal with supplementary part
        filted_main_file = [filename for filename in main_file if check_is_supplemtary(filename.lower())]
        if len(filted_main_file) == 1:
            return filted_main_file, 'root_file'


        if len(main_file)>1:
            return main_file, 'multifiles_case'
        elif len(main_file)==0:
            return main_file, 'cannot_locate_main'

def get_good_tex_files(arxiv_path,verbose = False):
    whole_texfiles = [filename for filename in os.listdir(arxiv_path) if isHardTexFile(os.path.join(arxiv_path,filename))]
    if verbose:print(whole_texfiles)
    texfiles       = [t for t in whole_texfiles if all([flag not in t for flag in our_processed_arxiv_flag])]
    if verbose:print(texfiles)
    if len(texfiles) == 0:
        softtexfiles = [t for t in whole_texfiles if all([flag not in t for flag in blacklist])]
        if len(softtexfiles)==1:
            oldtexname = softtexfiles[0]
            newtexname = oldtexname
            for flag in softblacklist:
                newtexname = newtexname.replace(flag,'.')
            oldpath = os.path.join(arxiv_path,oldtexname)
            newpath = os.path.join(arxiv_path,newtexname)
            os.rename(oldpath,newpath)
            tqdm.write(f"rename {oldpath} ==> {newpath}")
            texfiles = [newtexname]
        elif len(softtexfiles)==0:
            texfiles = []
        else:
            tqdm.write(f"WARNING: why the arxivid={arxiv_id} has multiple .tex files named .clean. and .revtex. and so on but no root>??")
            return arxiv_id, 'ErrorCaseI'
    if verbose:print(texfiles)
    texfiles = [os.path.join(arxiv_path, filename) for filename in texfiles]
    return texfiles

def find_the_root_for_one_path(arxiv_path, args:Dict)->Tuple[str,str]:

    if len(arxiv_path.split('/'))==1: ## the arxiv_path is the arxiv_id like 1231.3213
        arxiv_path = os.path.join(args.datapath,arxiv_path)
    arxiv_id       = os.path.basename(arxiv_path)
    if args.verbose:
        print(arxiv_path)
        print(os.listdir(arxiv_path))
    
    texfiles = get_good_tex_files(arxiv_path,verbose = args.verbose)
    if len(texfiles)==0:return arxiv_id,'no_tex'
    status = 'root_file'
    if len(texfiles)>1:
        main_file = find_the_root_tex(texfiles,arxiv_path)
        main_file, status = checkmainfile(main_file, arxiv_path)
        if status == 'multifiles_case':
            ### lets try 
            main_file = find_the_root_tex(main_file, arxiv_path,content_check=True)
            main_file, status = checkmainfile(main_file, arxiv_path)
    else:
        main_file = texfiles
    if len(main_file) == 1:
        return main_file[0], status
    else:
        return arxiv_id, status

def find_the_root_for_one_path_wrapper(args):
    arxiv_path, args = args
    return find_the_root_for_one_path(arxiv_path, args)
