
import os
from pathlib import Path
import sys
module_dir = str(Path(__file__).resolve().parent.parent)
if module_dir not in sys.path:sys.path.append(module_dir)

from uparxive.xml_to_json.clean_unarXive_data import identify_string_type, get_name,format_text_with_values
from uparxive.xml_to_json.xml_to_dense_text import better_latex_sentense_string
from uparxive.reference_reterive.Reference import UniqueID
from uparxive.batch_run_utils import BatchModeConfig, obtain_processed_filelist, process_files,dataclass,save_analysis
import json
from simple_parsing import ArgumentParser


@dataclass
class UnarxivetoUparxiveConfig(BatchModeConfig):
    savepath: str
    task_name = 'unarxive_to_uparxive'
    reterive_result_mode : bool = False
    

def processing_data_from_unarxive_into_uparxive(data, args:UnarxivetoUparxiveConfig):
    root_dir = args.savepath
    reterive_result_mode = args.reterive_result_mode
    metadata_i    = data['metadata']
    body_text_i   = data['body_text']
    bib_entries_i = data['bib_entries']
    ref_entries_i = data['ref_entries']
    paper_id = data['paper_id']
    paper_id = paper_id.replace('/',"_")
    output_dir = os.path.join(root_dir, paper_id, 'unarxive_clean')
    Content_Path = os.path.join(output_dir, f'{paper_id}.retrieved.json') if reterive_result_mode else os.path.join(output_dir, f'{paper_id}.json')
    
    #if os.path.exists(Content_Path):return
    os.makedirs(os.path.dirname(Content_Path),exist_ok=True)
    # get a dict for format citation/reference data
    insert_data = {}
    type_list = []

    # for formula, figure, table
    figure_ref  = {}
    table_ref   = {}
    equation_ref= {}
    figures_metadata ={}
    tables_metadata  ={}

    paper_unique_id  = identify_string_type(metadata_i['id'])
    for _id, item in ref_entries_i.items():
        type_list.append(item['type'])
        key = "{}:{}".format(item['type'], _id)
        if item['type'] == 'formula':
            value = """${}$""".format(item['latex'])
        elif item['type'] == 'table':
            value = f"""[Table.{len(tables_metadata)} of {paper_unique_id}]"""
            tables_metadata[_id] = item
            table_ref[_id] =[ 'Table', len(tables_metadata)]
        elif item['type'] == 'figure':
            value = f"""[Figure.{len(figures_metadata)} of {paper_unique_id}]"""
            figures_metadata[_id] = item
            figure_ref[_id]  = ['Figure',len(figures_metadata)]
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
        value = get_name(item)
        value = f"[Ref.{i} of {paper_unique_id}]" #if value is None else value
        insert_data[key] = value

    all_text = []
    Reference= []
    ReferenceQ= False
    acknowledgement = None
    for paragraph_id, paragraph in enumerate(body_text_i):
        #print(paragraph.keys())
        text = paragraph['text']

        start_string = text.strip()
        
        if start_string.lower().startswith('appendix') or start_string.lower().startswith('supplementary'):
            ReferenceQ=False
        if start_string.lower().startswith('reference'):
            ReferenceQ=True
            # print(f"fail at paragraph {paragraph_id}")
            # print(paragraph)
            # with open('fail.json','w') as f:
            #     json.dump(data, f)
            # raise

        new_text = format_text_with_values(text, insert_data, type_list,paper_unique_id)
        if start_string.startswith('Acknowledgement'):
            acknowledgement = new_text
            continue
        if len(new_text)==0: continue
        if not ReferenceQ:   
            paragraph['format_text'] = new_text
        else:
            Reference.append(new_text)

    sections = []
    structued_paragraph = {}
    for flatten_paragraph in body_text_i:
        section_num  = flatten_paragraph['sec_number']
        section_num  = section_num.strip()
        if section_num not in structued_paragraph:
            structued_paragraph[section_num] = {'section_content':[]}

        section_name = flatten_paragraph['section']
        section_name = better_latex_sentense_string(section_name)
        if section_name and "{{" in section_name:
            section_name = format_text_with_values(section_name, insert_data, type_list,paper_unique_id)
        if section_name in structued_paragraph[section_num]:
            assert section_name == structued_paragraph[section_num], f"why we get two different section name for [{section_name}] and ]"
        structued_paragraph[section_num]['section_name'] = section_name
        if 'format_text' not in flatten_paragraph:
            #print(flatten_paragraph)
            continue
        new_text = flatten_paragraph['format_text']
        all_text = structued_paragraph[section_num]['section_content']
        
        if all_text and new_text.strip() and (new_text.strip()[0].islower() or new_text.strip().startswith('Proof')):
            all_text[-1]+= ' ' + new_text.strip()
        elif all_text and all_text[-1].strip() and (all_text[-1].strip()[-1]=="$" or all_text[-1].strip()[-1]==":") and len(all_text[-1].split())<128:
            all_text[-1]+= ' ' + new_text
        else:
            all_text.append(new_text.replace('\n'," "))
        structued_paragraph[section_num]['section_content'] = all_text


    sections = []
    appendix = []
    section_num_keys = list(structued_paragraph.keys())
    
    # print("\n"*3)
    # print("=========>",section_num_keys)
    # section_num_keys = sort_section_numbers(section_num_keys)
    

    for section_num in section_num_keys:
        section_pool  = structued_paragraph[section_num]
        section_name   = section_pool['section_name']
        appendex_mode = False
        if (section_name and section_name.lower() in ['appendix','supplementary'] )or '-' in section_num:
            appendex_mode = True
        
        if not section_name: 
            if not appendex_mode:
                section_name = f'Section {section_num}'
            else:
                section_name = f"Appendix {section_num.replace('-','')}"
        now_section = {'section_title':section_name}|{'section_content':section_pool['section_content'],#split_by_indentation(section_pool['section_content']),
                                                      'section_num':section_num}
        if not appendex_mode:
            sections.append(now_section)
        else:
            appendix.append(now_section)

    #cat_final_i, sec_final_i = concatenate_text(all_text, body_text_i, metadata_i, encoding=encoding)
    #Reference = "|.|".join(Reference)

    undo_citation_keys   = []
    undo_citation_string = []
    done_citation_keys   = []
    done_citation_string = []
    done_citation_doi    = []
    for key, valpool in data['bib_entries'].items():

        citation = valpool.get('bib_entry_raw',"")
        if not citation:continue

        ids = valpool.get('ids',{})
        unique_id = UniqueID.from_dict(ids)
        if unique_id.is_nan():
            undo_citation_keys.append(key)  
            undo_citation_string.append(citation)  
        else:
            done_citation_keys.append(key)  
            done_citation_string.append(citation)
            done_citation_doi.append({k:val for k,val in unique_id.to_dict().items() if val})

    bibitem_ref_metadata = {k:v for k,v in zip(undo_citation_keys, undo_citation_string)}
    bibitem_ref_metadata = bibitem_ref_metadata| {k:v for k,v in zip(done_citation_keys, done_citation_string)}
    whole_metadata = {'figures_metadata':figures_metadata,
                      'tables_metadata':tables_metadata,
                      'bibitem_ref_metadata':bibitem_ref_metadata}
    whole_ref_to_labels = table_ref|figure_ref
    abstract = better_latex_sentense_string(data.get('abstract')['text'])
    output_dict = {'abstract':abstract,
                   'acknowledge':acknowledgement,
                   'sections':sections,
                   'appendix':[],
                   'metadata':whole_metadata,
                   'paper_id':paper_id,
                   'whole_ref_to_labels':whole_ref_to_labels,
                   'missing_citation_labels':{}}
    
    with open(Content_Path, 'w') as f:json.dump(output_dict, f, indent=2)
    if not reterive_result_mode:
        keys  = list(bibitem_ref_metadata.keys())
        citation_string = [bibitem_ref_metadata[key] for key in keys]
        with open(os.path.join(output_dir, f'reference.keys'), 'w') as f:
            for key in keys:f.write(key+'\n')
        with open(os.path.join(output_dir, f'reference.txt'), 'w') as f:
            for string in citation_string:f.write(string+'\n')
        # with open(os.path.join(output_dir, f'bibitem_ref_metadata_not_in_context.json'), 'w') as f:
        #     json.dump(bibitem_ref_metadata_not_in_context, f, indent=2)
        # with open(os.path.join(output_dir, f'note_ref_metadata_not_in_context.json'), 'w') as f:
        #     json.dump(note_ref_metadata_not_in_context, f, indent=2)

def processing_data_from_unarxive_into_uparxive_wrapper(args):
    arxiv_path, args = args
    return processing_data_from_unarxive_into_uparxive(arxiv_path, args)

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_arguments(BatchModeConfig, dest="config")
    args = parser.parse_args()
    args = args.config

    alread_processing_file_list = obtain_processed_filelist(args)
    results = process_files(processing_data_from_unarxive_into_uparxive_wrapper, alread_processing_file_list, args)
    #print(results)
    analysis= {}
    for arxivid, _type in results:
        if _type not in analysis:
            analysis[_type] = []
        analysis[_type].append(arxivid)
    
    totally_paper_num = len(alread_processing_file_list)
    save_analysis(analysis, totally_paper_num==1, args)