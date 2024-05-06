from .analysis_tex_to_xml import get_first_n_lines, get_last_n_lines, ensure_string
from uparxive.batch_run_utils import BatchModeConfig, dataclass
import os
from pathlib import Path

@dataclass
class ArchiveXMLConfig(BatchModeConfig):
    task_name = 'archive_xml'

def archive_one_xml_fold(xml_fold, args):
    """
    Remove and shrink the xml files in the xml_fold to reduce memory usage
    for ar xml fold, it has 
        - fail_attempt/*.xml
        - fail_attempt/*.log
        - [passed].xml
        - [passed].log
    lets remove whole the .xml file in the fail_attempt and only keep the first n=10 lines and last n=10 lines 
    of the log file.
    
    The reason we keep the log file is due to identify the error message.
    """
    
    fail_fold       = os.path.join(xml_fold, 'fail_attempt')
    whole_log_files = list(Path(xml_fold).rglob('*.log'))
    if os.path.exists(fail_fold):
        whole_log_files += list(Path(fail_fold).rglob('*.log'))
    
    for logpath in whole_log_files:
        last_ten_lines = get_first_n_lines(logpath,3) + ["-------------- lots of log ---------------"]  + get_last_n_lines(logpath, 10)
        if len(last_ten_lines)<30:continue
        # then rewrite the log file
        logpath = str(logpath)
        with open(logpath+'.new', 'w', encoding='utf-8') as f:
            for line in last_ten_lines:
                f.write(ensure_string(line.strip())+'\n')
        os.remove(logpath)
        os.rename(logpath+'.new',logpath)

    failxml = Path(fail_fold).rglob('*.xml')
    for failpath in failxml:
        os.remove(failpath)


def archive_one_xml_fold_wrapper(args):
    arxiv_path, args = args
    return archive_one_xml_fold(arxiv_path, args)
