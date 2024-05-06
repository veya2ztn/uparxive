import sys,json
from pathlib import Path
module_dir = str(Path(__file__).resolve().parent.parent)
# Add this directory to sys.path
if module_dir not in sys.path:
    sys.path.append(module_dir)
from reference_reterive.Reference import *
from build_redis_database.utils import *
def get_digital_worth_index_from_unique_id(r, unique_id:UniqueID):
    for alias_type, alias_value in unique_id.to_dict().items():
        digital_worth_index = get_index_by_alias(r,alias_type, alias_value)
        if digital_worth_index is not None:
            return digital_worth_index

def format_es_paper(ref:Reference,vene_name_to_alias):
    if isinstance(ref,Reference):
        out = ref.to_flatten_dict()
    else:
        out = ref
    if out.get('author',None):
        author_list = out.pop('author')
        for author_order, name in zip(range(3),author_list ):
            out[f'author.{author_order}'] = name
    if out.get('journal',None):
        journal_name =  out.pop('journal')
        journal_name = journal_name.lower()
        if journal_name in vene_name_to_alias:
            journal_name = ", ".join(vene_name_to_alias[journal_name])
        out['journal'] = journal_name
    return out

def line_count(file_path):
    return int(os.popen(f'wc -l {file_path}').read().split()[0])
