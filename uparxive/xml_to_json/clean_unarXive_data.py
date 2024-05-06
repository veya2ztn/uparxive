
import pandas as pd
import re
import pathlib
import os
import tqdm
from pathlib import Path
import argparse
from ..batch_run_utils import BatchModeConfig, dataclass

#encoding = tiktoken.get_encoding("cl100k_base")
prepositions = {'at', 'in', 'on', 'for', 'with', 'and','see', 'or', 'nor', 'about', 'as', 'by', 'over', 'according to', 'against', 'along', 'among', 'apart from', 'around', 'as for', 'aside from', 'because of', 'before', 'behind', 'below', 'beneath', 'beside', 'between', 'beyond', 'but', 'by means of', 'concerning', 'despite', 'down', 'due to', 'during', 'except', 'except for', 'in addition to', 'in case of', 'in front of', 'in place of', 'in spite of', 'inside', 'instead of', 'into', 'like', 'near', 'next', 'off', 'onto', 'out', 'out of', 'outside', 'over', 'past', 'since', 'through', 'throughout', 'toward', 'under', 'underneath', 'until', 'up', 'upon', 'with', 'within', 'without'}
prepositions = prepositions|set([t.upper() for t in prepositions])
prepositions = prepositions|set([t[0].upper()+t[1:] for t in prepositions])
prepositions = prepositions|set(['\\.', "\\;",'\\,'])

# format function
def format_text(example_text, insert_data, *args):
    placeholders = re.findall(r"\{\{([^{}]+)\}\}", example_text)

    # Replace the placeholders with corresponding values
    for placeholder in placeholders:
        key = "{{" + placeholder + "}}"
        if placeholder in placeholders:
            example_text = example_text.replace(key, insert_data[placeholder])
    
    return example_text

def replace_continuous_spaces(text):
    return re.sub(r'(?<=\S)\s+', ' ', text)

def replace_start_spaces(text):
    return text#re.sub(r'^\s+', '[SENTENCE_START]', text)

def merge_citations(input_str):
    citation_prefixes = ["DOI:", "ArXiv:", "Ref.", "ALEX:"]
    pattern = r"\[\s*(?:" + "|".join(citation_prefixes) + r")\s*\S+\s*(?:of\s+\S+)?\s*\]"
    # Find all citation marks in the input string
    citations = re.findall(pattern, input_str)
    #print(citations)
    # Replace continuous citation marks with a single mark containing all citations
    output_str = re.sub(pattern + r"(?:\s*,\s*" + pattern + r")+", lambda match: ", ".join(match.group(0).replace('[', '').replace(']', '').split(', ')).join(['[', ']']), input_str)

    return output_str

def replace_number_citation_marks(text, paper_id,externel_reference_mapping={}):
    
    def replace_match(match):
        position, name, citation = match.groups()
        #print(position)
        # Case 1: Beginning of the sentence
        is_start_of_string = match.start() == 0 or text[match.start() - 2] in {'.', '!', '?', ';'}

        if is_start_of_string or position == '':
            return f'[Ref.{citation} of {paper_id}]'
        
        # Case 2: End of the sentence
        if position in prepositions:
            return f'{position} [Ref.{citation} of {paper_id}]'
        
        # Case 3: Middle of the sentence
        return f'(See [Ref.{citation} of {paper_id}])'

    pattern = r'(?:(\b(?:' + '|'.join(prepositions) + r')\b) )?\[([\d, -]+)\]'
    pattern = r'(?:(\b(?:' + '|'.join(prepositions) + r')\b) )?(\w+)?(?:\s)?(?:et al\.\s)?\[([\d, -]+)\]'
    return re.sub(pattern, replace_match, text)


def replace_string_citation_marks(text):
    def replace_match(match):
        position, citation = match.groups()
        is_start_of_string = match.start() == 0 or text[match.start() - 2] in {'.', '!', '?', ';'}

        if is_start_of_string:
            return citation
        # Ignore if the citation is preceded by a preposition
        if position and position.lower() in prepositions:
            return f'{position} {citation}'
        return f'(See {citation})'

    #pattern = r'(?:(\b(?:' + '|'.join(prepositions) + r')\b) )?\[([\d, -]+)\]'
    citation_prefixes = ["DOI:", "ArXiv:", "Ref.", "ALEX:"]
    pattern = r"(?:(\b(?:" + '|'.join(prepositions) + r")\b) )?(\[\s*(?:(?:" + "|".join(citation_prefixes) + r")\s*\S+\s*(?:of\s+\S+)?\s*(?:,\s*)?)+\])".format("|".join(prepositions))
    return re.sub(pattern, replace_match, text)

def format_text_with_values(text, values, type_list,paper_id):
    """
    repalce all text that have the format {{ hash_code }}
    
    """
    pattern = r"(?:Ref\.\s*)?\{\{(" + "|".join(type_list) + r"):([^{}]+)\}\}"
    def replace(match):
        key = "{}:{}".format(match.group(1), match.group(2))
        return values.get(key, key)

    formatted_text = re.sub(pattern, replace, text)
    
    formatted_text = replace_continuous_spaces(formatted_text)
    formatted_text = replace_start_spaces(formatted_text)
    formatted_text = merge_citations(formatted_text)
    formatted_text = replace_string_citation_marks(formatted_text)
    formatted_text = replace_number_citation_marks(formatted_text,paper_id)
    return formatted_text

def split_by_indentation(all_text):
    all_text = "".join(all_text)
    all_text = all_text.replace("\n"," ")
    #all_text = all_text.split('[SENTENCE_START]')
    all_text = re.split(r'\s{2,}', all_text)
    return all_text
# concatenate function
def concatenate_text(all_text, body_text, metadata, encoding=None):  
    
    new_text = split_by_indentation(all_text)
    if len(new_text) == 1:
        # this mean indentation split fail. go back normal split
        pass
    else:
        all_text = new_text
        
    sec_name = None


#     if len(all_text) == 0:
#         return [], []
#     else:
#         # concat all the incompleted sentences
#         all_text, sec_name = concat_by_complete_sentence(all_text, sec_name)
    
    # if encoding is None:
    #     encoding = tiktoken.get_encoding("cl100k_base")
    # tokens = [len(encoding.encode(x, disallowed_special=())) for x in all_text]

    #### get the concatenated text lists
    ## do not limit size , we will deal with exceed token problem later
    #cat_text, cat_sec_name = concat_by_token(all_text, sec_name, metadata, tokens)
    cat_text, cat_sec_name = all_text, sec_name
    return cat_text, cat_sec_name

def merge_sentences(sentences):
    merged = []
    for sentence in sentences:
        if merged and sentence[0].islower():
            merged[-1] += ' ' + sentence
        else:
            merged.append(sentence)
    return merged

def concat_by_complete_sentence(sentences, sec_number=None):
    """
     realized function:
         merge this sentence into last sentence if the starting of this sentence is lower alphabeta
    """
    merged = []
    for sentence in sentences:
        if merged and sentence[0].islower():
            merged[-1] += ' ' + sentence
        else:
            merged.append(sentence)
    
    return merged, list(range(len(merged)))   

def concat_by_token(all_text, sec_name, metadata, tokens, min_token = 128, max_token_soft=512):
    # concatenate text to make it
    #cat_text = [metadata.get('abstract', None).replace("\n"," ") or "" ]
    #cat_sec_name = ['abstract']
    cat_text = [] 
    cat_sec_name=[]
    ### we dont need abstract
    
    current_text = ""
    current_sec = sec_name[0]
    current_token = 0
    index = 0
    for i in range(len(all_text)):
        if current_sec != sec_name[i]:
            if current_token < min_token:
                # if too short, append it to the previous paragraph
                cat_text[-1] += current_text
            else:
                cat_sec_name.append(current_sec)
                cat_text.append(current_text)
            current_text  = all_text[i]
            current_token = tokens[i]
            current_sec   = sec_name[i]
            
        if current_sec == sec_name[i] and current_token + tokens[i] <= max_token_soft:
            current_text += "\n"+all_text[i]
            current_token += tokens[i]
            
        else:
            cat_sec_name.append(current_sec)
            cat_text.append(current_text)
            current_text = all_text[i]
            current_token = tokens[i]
            current_sec = sec_name[i]
    
    
    if current_text:
        if current_token < min_token:
            cat_text[-1] += current_text
        else:
            cat_text.append(current_text)
            cat_sec_name.append(current_sec)

    return cat_text, cat_sec_name

import re
def get_name(item_pool):
    if 'ids' not in item_pool:return None
    ids = item_pool['ids']
    if ids['arxiv_id'] !="":
        return f"[ArXiv:{ids['arxiv_id']}]"
    elif ids['doi'] !="":
        return f"[DOI:{ids['doi']}]"
    elif ids['open_alex_id'] !="":
        return f"[ALEX:{ids['open_alex_id'].split('/')[-1]}]"
    else:
        return None

def identify_string_type(s):
    """
    give the unique know of a paper
    """
    pattern1 = r"^\d+\.\d+$"
    pattern2 = r"^[a-zA-Z]+\/\w+$"

    if re.match(pattern1, s):
        return f"ArXiv:{s}"
    elif re.match(pattern2, s):
        return f"ArXiv:{s}"
    else:
        return s

    
def process_a_paper(papers, index=0, encoding=None, use_bib=False):
    """This will change the dataframe `papers` inplace"""
    metadata_i    = papers.loc[index, 'metadata']
    body_text_i   = papers.loc[index, 'body_text']
    bib_entries_i = papers.loc[index, 'bib_entries']
    ref_entries_i = papers.loc[index, 'ref_entries']
    
    # get a dict for format citation/reference data
    insert_data = {}
    type_list = []
    
    # for formula, figure, table
    figure_list =[]
    table_list  =[]
    paper_unique_id  = identify_string_type(metadata_i['id'])
    for id, item in ref_entries_i.items():
        type_list.append(item['type'])
        key = "{}:{}".format(item['type'], id)
        if item['type'] == 'formula':
            value = """${}$""".format(item['latex'])
        elif item['type'] == 'table':
            value = f"""[Table.{len(table_list)} of {paper_unique_id}]"""
            table_list.append(item)
        elif item['type'] == 'figure':
            value = f"""[Figure.{len(table_list)} of {paper_unique_id}]"""
            table_list.append(item)
        else:
            print('='*20)
            print(item)
            print('='*20)
            value = ""
        insert_data[key] = value
        
    # remove duplicate
    type_list = list(set(type_list)) 

    # for citation
    type_list.append('cite')
    
    for i,(_id, item) in enumerate(bib_entries_i.items()):
        key = "{}:{}".format('cite', _id)
        #if use_bib:
        #    value = """[Reference: {}]""".format(item['bib_entry_raw'])
        #else:
        #    value = "[Reference]"
        value = get_name(item)
        value = f"[Ref.{i} of {paper_unique_id}]" if value is None else value
        insert_data[key] = value
    
    all_text = []
    Reference= []
    ReferenceQ= False
    
    for paragraph in body_text_i:
        #print(paragraph.keys())
        text = paragraph['text']
        
        start_string = text.strip()[:20]
        if 'REFERENCES' in start_string or 'Reference' in start_string:
            ReferenceQ=True
            #print(start_string)
        if 'Acknowledgement' in start_string:
            #print(start_string)
            continue
        new_text = format_text_with_values(text, insert_data, type_list,paper_unique_id)
        if len(new_text)==0:
            continue
        
        if all_text and new_text.strip() and (new_text.strip()[0].islower()or new_text.strip()[:5] == 'Proof'):
            all_text[-1]+=' '+new_text.strip()
        elif all_text and all_text[-1].strip() and (all_text[-1].strip()[-1]=="$" or all_text[-1].strip()[-1]==":") and len(all_text[-1].split())<128:
            all_text[-1]+=' '+new_text
        else:
            if ReferenceQ:
                Reference.append(new_text.replace('\n'," "))
            else:
                all_text.append(new_text.replace('\n'," "))
        paragraph['format_text'] = new_text
    
#     for t in all_text:
#         print(len(t.split()))
#         print(t+'\n')
#     raise
    cat_final_i, sec_final_i = concatenate_text(all_text, body_text_i, metadata_i, encoding=encoding)
    Reference = "|.|".join(Reference)
    return all_text, cat_final_i, sec_final_i,Reference

def process_papers(papers, encoding):
    papers['all_text'] = None
    papers['long_text_for_llm'] = None
    papers['long_text_section'] = None
    for i in tqdm.tqdm(range(len(papers)), leave=False, position=1):
        all_text, cat_final_i, sec_final_i,Reference = process_a_paper(papers, i, encoding=encoding)
        papers.at[i, 'all_text'] = all_text
        papers.at[i, 'long_text_for_llm'] = cat_final_i
        papers.at[i, 'long_text_section'] = sec_final_i
        papers.at[i, 'Reference'] = Reference
        
    return papers

def process_and_store(src_path, trg_path, encoding):
    with open(src_path) as f:
        papers = pd.read_json(path_or_buf=f, lines=True)
    papers_new = process_papers(papers, encoding)

    papers_new.to_json(trg_path, orient='records', lines=True)
    
    
def convert_a_file(src_path):
    # trg_path = src_path.replace("unarXive_230324_open_subset", "unarXive_230324_open_subset_new")
    trg_path = src_path.replace("unarXive_230324", "unarXive_clear_20230705")
    trg_dir = os.path.dirname(trg_path)
    pathlib.Path(trg_dir).mkdir(exist_ok=True, parents=True)
    if os.path.exists(trg_path):return
    process_and_store(src_path, trg_path, encoding=encoding)
    
    
def thread_func(all_files, start, end, total_length=5599, show=True, show_iters=5):
    files_done = 0
    with tqdm.tqdm(range(start, end), desc="Main", ncols=100, ascii=True) as pbar:
        for i in pbar:
            file_name = all_files[i]
            convert_a_file(file_name)
            pbar.update(1)
            
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", type=int, default=0)
    parser.add_argument('--check',action='store_true')
    args = parser.parse_args()
    done_file_names = [x.name for x in Path('dataset/unarXive_clear_20230705/').glob('**/*.jsonl')]
    all_raw_files   = list(Path('dataset/unarXive_230324/').glob('**/*.jsonl'))
    total_length    = len(all_raw_files)
    all_files       = [x.as_posix() for x in all_raw_files if x.name not in done_file_names]
    if args.check:
        print(f"remain {len(all_files)} files")
        exit()
    num_threads = 1#min(len(all_files), os.cpu_count())

    # Create a ThreadPoolExecutor and run the conversion function for each file in parallel.
    # with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
    #     results = list(tqdm(executor.map(convert_a_file, all_files), total=len(all_files)))

    num_interval = 30
    interval = int(float(len(all_files)) / num_interval)
    start_end_idx = [i * interval for i in range(num_interval)]
    start_end_idx.append(len(all_files))
    
    
    
    start, end = start_end_idx[args.id], start_end_idx[args.id+1]
    with open("stas.txt", 'a+') as f:
        f.write("begin converting files with id {}, start: {}, end: {}\n".format(args.id, start, end))
    thread_func(all_files, start, end, show=True, show_iters=5, total_length=end - start)    