
import os,glob,re
from tqdm.auto import tqdm
from typing import Tuple
from uparxive.batch_run_utils import BatchModeConfig, dataclass
from .standalize_tex import TexStandardConfig

@dataclass
class TexCompilingConfig(BatchModeConfig):
    mode : str = 'analysis'
    task_name = 'tex_to_xml'

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

def get_first_n_lines(file_path, n):
    with open(file_path, 'r', encoding='utf-8') as f:
        ### notice that this will read the first n lines of the file, case that if the len(f) < n
        #lines = [next(f) for _ in range(n)] 
        lines = []
        for i, line in enumerate(f):
            lines.append(ensure_string(line).strip())
            if i > n:break
    return lines

def get_last_n_lines(file_path, n):
    with open(file_path, 'rb') as file:
        file.seek(0, os.SEEK_END)
        position = file.tell()
        lines = []
        while position >= 0 and len(lines) < n:
            file.seek(position)
            next_char = file.read(1)
            if next_char == b'\n':
                lines.append(file.readline().decode().rstrip())
            position -= 1
        file.seek(0)
        if len(lines) < n:
            lines.extend(file.readlines())
        return lines[-n:][::-1]

def analysis_pass_or_fail_from_log(logpath):
    
    last_ten_lines = get_first_n_lines(logpath,3) + get_last_n_lines(logpath, 10)

    last_line = None
    for line in last_ten_lines:
        if 'Conversion ' in str(line):
            last_line = str(line)
    if last_line is None:
        return 'EmptyLog'
    if 'error' in last_line or 'Quick End' in last_line:
        return 'Error'
    elif 'timed out' in last_line :
        return 'timeout'
    elif 'warning'in last_line:
        return 'Warning'
    else:
        return 'Success'

import shutil
def analysis_tex_xml_processing_via_path(DIR, args:TexCompilingConfig)->Tuple[str,str]:
    
    origin_file = None
    if os.path.isfile(DIR):
        origin_file = DIR
        DIR = os.path.dirname(DIR).replace('unprocessed_tex','unprocessed_xml')
    DIR = DIR.replace('unprocessed_tex','unprocessed_xml')
    ROOTPATH, DIRNAME = os.path.split(DIR)
    RETURNPATH = origin_file if origin_file is not None else DIR
    
    if not os.path.exists(DIR):
        #print(f"no such directory: {DIR}")
        return RETURNPATH, 'EmptyDir'
    
    #texfiles = glob.glob(os.path.join(DIR, '*.tex'), recursive=False)
    logfiles = glob.glob(os.path.join(DIR, '*.log'), recursive=False)
    error_file = False
    if len(logfiles) > 1:
        status_record = {}
        failed_dir = os.path.join(DIR,'fail_attempt')
        os.makedirs(failed_dir,exist_ok=True)
        final_status = 'Error'
        for logpath in logfiles:
            logname = os.path.basename(logpath)
            xmlpath = logpath.replace('.log','.xml')
            
            status = analysis_pass_or_fail_from_log(logpath)
            
            if status in ['Success', 'Warning']:
                final_status = status
                if not os.path.exists(xmlpath):
                    return RETURNPATH, 'NoXML'
            else:
                
                shutil.move(logpath, os.path.join(failed_dir, logname))
                if os.path.exists(xmlpath):
                    shutil.move(xmlpath, os.path.join(failed_dir, logname.replace('.log','.xml')))

        if final_status in ['Success', 'Warning']:
            return DIRNAME, final_status
        else:
            return RETURNPATH, 'Error'


    elif len(logfiles) == 0:
        return RETURNPATH, 'NoLog'
    else:
        logfile = logpath = logfiles[0]
        xmlpath = logfile[:-4]+'.xml'
        
        status = analysis_pass_or_fail_from_log(logfile)
        
        if status in ['Success', 'Warning']:
            #print(xmlpath)
            if not os.path.exists(xmlpath):
                return RETURNPATH, 'NoXML'
            return DIRNAME, status
        else:
            logname = os.path.basename(logpath)
            failed_dir = os.path.join(DIR,'fail_attempt')
            if status in ['Error', 'timeout']:
                os.makedirs(failed_dir,exist_ok=True)
                shutil.move(logpath, os.path.join(failed_dir, logname))
                if os.path.exists(xmlpath):
                    shutil.move(xmlpath, os.path.join(failed_dir, logname.replace('.log','.xml')))
            return RETURNPATH, status
    
def analysis_fail_status(DIR,args:TexCompilingConfig)->Tuple[str,str]:
    origin_file = None
    if os.path.isfile(DIR):
        origin_file = DIR
        DIR = os.path.dirname(DIR).replace('unprocessed_tex','unprocessed_xml')
    
    ROOTPATH, DIRNAME = os.path.split(DIR)
    RETURNPATH = origin_file if origin_file is not None else DIRNAME
    
    if not os.path.exists(DIR):
        tqdm.write(f"no such directory: {DIR}")
        return 
    
    if len(os.listdir(DIR))==0:
        shutil.rmtree(DIR)
        return 


    
    failed_dir = os.path.join(DIR,'fail_attempt')
    
    # if not os.path.exists(failed_dir):
    #     print(f"why you try to analysis fail status without failed dir? ==> {DIR}")
    #     return RETURNPATH, 'NofailDir'

    #texfiles = glob.glob(os.path.join(DIR, '*.tex'), recursive=False)
    logfiles = (list(glob.glob(os.path.join(failed_dir, '*.log'), recursive=False)) + 
                list(glob.glob(os.path.join(DIR, '*.log'), recursive=False))
                )  
    
    status_record = {}
    for logpath in logfiles:
        logpath = str(logpath)
        key = 'origin'
        for mode in TexStandardConfig.modelist:
            flag = f'.{mode}.log'
            if logpath.lower().endswith(flag):
                key = mode
            break

        status = analysis_pass_or_fail_from_log(logpath)
        if status in ['Success', 'Warning']:
            status = 'pass'
            xmlpath = logpath.replace('.log','.xml')
            # if not os.path.exists(xmlpath):
            #     return RETURNPATH, 'NoXML'
        elif status in ['EmptyLog']:
            status = 'fail'
            #return RETURNPATH, 'EmptyLog'
        else:
            status = 'fail'
        status_record[key] = status

    status_string = [DIR]
    for key in ['origin'] + TexStandardConfig.modelist:
        status_string.append(status_record.get(key,'none'))
    return " ".join(status_string), 'fail_reason'

import shutil
def analysis_origin_tex_xml_compiling(DIR, args:TexCompilingConfig)->Tuple[str,str]:
    origin_file = None
    if os.path.isfile(DIR):
        origin_file = DIR
        DIR = os.path.dirname(DIR).replace('unprocessed_tex','unprocessed_xml')
    ROOTPATH, DIRNAME = os.path.split(DIR)
    RETURNPATH = origin_file if origin_file is not None else DIRNAME
    if not os.path.exists(DIR):
        tqdm.write(f"no such directory: {DIR}")
        return 
    if len(os.listdir(DIR))==0:
        shutil.rmtree(DIR)
        return 
    failed_dir = os.path.join(DIR,'fail_attempt')
    logfiles = (list(glob.glob(os.path.join(failed_dir, '*.log'), recursive=False)))  
    logfiles = [t for t in logfiles if not t.endswith('clean.log') and not t.endswith('revtex.log')]
    status_record = {}
    for logpath in logfiles:
        logpath = str(logpath)
        key = 'origin'
        status = analysis_pass_or_fail_from_log(logpath)
        if status in ['Success', 'Warning']:status = 'pass'
        elif status in ['EmptyLog']:status = 'emptylog'
        else:status = 'fail'
        status_record[key] = status

    status_string = [DIR]
    for key in ['origin']:
        status_string.append(status_record.get(key,'none'))
    return " ".join(status_string), 'fail_reason'
 
def analysis_tex_to_xml(foldpath, args:TexCompilingConfig):
    if args.mode == 'analysis':
        return analysis_tex_xml_processing_via_path(foldpath, args)
    elif args.mode == 'fail_reason':
        return analysis_fail_status(foldpath, args)
    elif args.mode == 'check_origin':
        return analysis_origin_tex_xml_compiling(foldpath, args)
    else:
        raise NotImplementedError

def analysis_tex_to_xml_wrapper(args):
    arxiv_path, args = args
    return analysis_tex_to_xml(arxiv_path, args)
  

    

    