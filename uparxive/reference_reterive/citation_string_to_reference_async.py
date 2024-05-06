
import sys
from pathlib import Path
module_dir = str(Path(__file__).resolve().parent)
if module_dir not in sys.path:sys.path.append(module_dir)
from citation_string_to_reference import *

#import numpy as np


if __name__ == '__main__':
    import os
    import sys
    from tqdm.auto import tqdm
    import numpy as np
    import argparse, logging,traceback
    parser = argparse.ArgumentParser()
    parser.add_argument("--root_path", type=str)
    parser.add_argument("--index_part", type=int, default=0)
    parser.add_argument('--num_parts', type=int, default=1)
    parser.add_argument('--port', type=int, default=9200)
    parser.add_argument('--score_limit',  type=float, default=0.5)
    parser.add_argument('--search_engine',  type=str, default='integrate')
    parser.add_argument('--redo', action='store_true', help='', default=False)
    parser.add_argument('--verbose', '-v', action='store_true', help='', default=False)
    parser.add_argument('--notchecknote',  action='store_true', help='', default=False)
    args = parser.parse_args()

    filelistpath = args.root_path
    analysis = {}
    task_name= 'retreive_reference'
    if os.path.isdir(filelistpath):
        root_path = filelistpath
        while not root_path.endswith('whole_arxiv_all_files'):
            root_path = os.path.dirname(root_path)
            assert root_path != '/'
        root_path = os.path.join(root_path,f'analysis.{task_name}')
        all_file_list = [filelistpath]
    elif os.path.isfile(filelistpath):
        root_path = filelistpath
        while not root_path.endswith('whole_arxiv_all_files'):
            root_path = os.path.dirname(root_path)
            assert root_path != '/'
        root_path = os.path.join(root_path,f'analysis.{task_name}')
        
        os.makedirs(root_path,exist_ok=True)
        with open(filelistpath,'r') as f:
            all_file_list = [t.strip() for t in f.readlines()]
    else:
        raise NotImplementedError("What is your filelistpath?")


    totally_paper_num = len(all_file_list)
    logging.info(totally_paper_num)

    
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
    
    alread_processing_file_list = all_file_list
    np.random.shuffle(alread_processing_file_list)
    print(alread_processing_file_list[:10])
    alread_processing_file_list = all_file_list[start_index:end_index]

    selected_engine = f"http://localhost:{args.port}"
    es = Elasticsearch(selected_engine,request_timeout=1000)
    es.indices.refresh(index='integrate20240311')

    LOCKROOT = os.path.join("/nvme/zhangtianning.di/sharefold/whole_arxiv_all_files/lock")
    for file_idx, ROOTDIR in enumerate(tqdm(alread_processing_file_list,position=0)):
        
        arxiv_id = ROOTDIR.rstrip('/').split('/')[-3]
        INPUTPATH  = os.path.join(ROOTDIR,'reference.structured.jsonl')
        REFTEXT    = os.path.join(ROOTDIR,'reference.txt')
        OUTPUTPATH = os.path.join(ROOTDIR,f"reference.es_retrived_citation.json")
        LOCKFILE   = os.path.join(LOCKROOT,f"{arxiv_id}.lock")
        
        
        if os.path.exists(OUTPUTPATH) and not args.redo:
            analysis['already_done'] = analysis.get('already_done',[])+[ROOTDIR]
            continue
        
        if os.path.exists(LOCKFILE): continue
        with open(LOCKFILE,'w') as f: f.write('')
        
        if not os.path.exists(REFTEXT):
            analysis['no_ref_text'] = analysis.get('no_ref_text',[])+[ROOTDIR]
            continue
        if os.path.getsize(REFTEXT) == 0:
            analysis['empty_ref_text'] = analysis.get('empty_ref_text',[])+[ROOTDIR]
            continue
        if not os.path.exists(INPUTPATH):
            analysis['no_ref_structured'] = analysis.get('no_ref_structured',[])+[ROOTDIR]
            continue
        


        final_ref_list = build_the_structured_citation_pool(INPUTPATH, REFTEXT)
        tqdm.write(f"now deal with ====> [{arxiv_id}]")
        try:
            results = process_one_reflist(final_ref_list, es, args.search_engine , args.score_limit, args.verbose, not args.notchecknote)
            with open(OUTPUTPATH, 'w') as f:
                json.dump(results, f)
        except:
            tqdm.write(f"Error in {ROOTDIR}")
            if len(alread_processing_file_list) == 1:
                traceback.print_exc()
            analysis['error'] = analysis.get('error',[])+[ROOTDIR]
            continue
    
    print(root_path)
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
            # with open(os.path.join(root_path,f"{key.lower()}.filelist"), 'w') as f:
            #     for line in set(val):
            #         f.write(line+'\n')