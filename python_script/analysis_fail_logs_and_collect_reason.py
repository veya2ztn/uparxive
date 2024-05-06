
from pathlib import Path
import sys, os
module_dir = str(Path(__file__).resolve().parent.parent)
if module_dir not in sys.path:sys.path.append(module_dir)
from uparxive.batch_run_utils import BatchModeConfig, obtain_processed_filelist, process_files,dataclass,save_analysis
from simple_parsing import ArgumentParser
import re
@dataclass
class LogAnalysisConfig(BatchModeConfig):
    task_name = 'LogAnalysis'
    mode = 'analysis'
    datapath = '/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/unprocessed_xml/'
    logpath  = '/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/analysis/'

def ensure_string(input_data):
    """
    Ensure that the input data is a normal string.

    If the input is a byte string, it decodes it to a normal string using UTF-8.
    If the input is already a normal string, it returns it as-is.
    
    Args:
        input_data (str or bytes): The input data that might be a byte string or a normal string.

    Returns:
        str: A normal (Unicode) string.
    """
    if isinstance(input_data, bytes):
        # Decode the byte string to a normal string using UTF-8 encoding
        return input_data.decode('utf-8')
    elif isinstance(input_data, str):
        # Return the normal string unchanged
        return input_data
    else:
        raise ValueError("Input must be a string or byte string")

def extract_errors(log_content):
    # Regular expression to capture errors and their positions using non-greedy matching
    error_pattern = r"Error:.*?at.*?line \d+ col \d+ ?"
    
    # Find all occurrences of the pattern
    errors = re.findall(error_pattern, log_content, re.DOTALL)
    
    return errors

def extract_file_info(log_content):
    # Regular expression to capture file details between 'at' and ';'
    file_info_pattern = r"at (.*?);"
    
    # Find all occurrences of the pattern
    file_infos = re.findall(file_info_pattern, log_content)
    if len(file_infos)==0:
        return ""
    file_info =  file_infos[0]
    file_info = file_info.split('at ')[-1]
    return file_info
def analysis_log(logpath,args):
    with open(logpath,'r') as f:
        content = ensure_string(f.read())
        Errors = extract_errors(content)
        Errors = [e.strip().replace('\n',' ') for e in Errors]
        #ErrosShort = [t.split()[0] for t in Errors]
        ErrorPlace = [extract_file_info(t) for t in Errors]
        ErrorPlace = [t for t in ErrorPlace if t.endswith('.sty')]
        origin_tex_dir = os.path.dirname(os.path.dirname(logpath)).replace('unprocessed_xml', 'unprocessed_tex')
        if not os.path.exists(origin_tex_dir):return None, 'skip'
        filelist = set(os.listdir(origin_tex_dir))
        PrivateErrorPlace = set([t for t in ErrorPlace if t in filelist])
        GlobalErrorPlace  = set([t for t in ErrorPlace if t not in filelist])
        ErrorPlace = list(set(ErrorPlace))
    return [PrivateErrorPlace,GlobalErrorPlace] , 'error_reason'

def analysis_log_wrapper(args):
    logpath, args = args
    return analysis_log(logpath, args)


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_arguments(LogAnalysisConfig, dest="config")
    args = parser.parse_args()
    args = args.config

    if args.mode == 'obtain_file':
        All_LOGS = list(Path(args.datapath).glob("*/fail_attempt/*.log"))
        filepath = os.path.join(args.logpath,'all_fail_log.txt')
        with open(filepath,'w') as f:
            for path in All_LOGS:
                f.write(str(path)+'\n')
        print(filepath)
        exit()
    
    #if args.mode == 'analysis':
    alread_processing_file_list = obtain_processed_filelist(args)
    results = process_files(analysis_log_wrapper, alread_processing_file_list, args)
    #print(results)
    analysis= {'PrivateError':[], 'GlobalError':[]}
    for arxivid_list, _type in results:
        if _type == 'skip':continue

        PrivateErrorPlace,GlobalErrorPlace = arxivid_list
        analysis['PrivateError'].extend(PrivateErrorPlace)
        analysis['GlobalError'].extend(GlobalErrorPlace)
    
    for key in analysis.keys():
        analysis[key] = set(analysis[key] )

    totally_paper_num = len(alread_processing_file_list)
    save_analysis(analysis, totally_paper_num==1, args)