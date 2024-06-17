from ..batch_run_utils import BatchModeConfig, dataclass
from .nougat.dataset.parser.latexml_parser import parse_latexml
from .html_to_dense_text import *
from .nougat.dataset.parser.latexml_parser import *
from .nougat.dataset.parser.html2md import *
from .nougat.dataset.parser.markdown import *
import copy
@dataclass
class HTMLtoMDConfig(HTMLtoJsonConfig):
    task_name = 'html_to_md'
    outputmd:bool = False
    do_not_generate_reference: bool = False
import json

def collect_sections_to_content(soup:BeautifulSoup, args:HTMLtoMDConfig):
    doc = Document()
    parse_latexml_children(soup, doc)
    parts = []
    parts.extend(format_children(doc, True, not args.outputmd))
    parts=get_good_content(parts)

    return parts



def deal_with_html_file(tmp_html_path, output_dir, args:HTMLtoJsonConfig)->str:
    

    use_count_type_ref  = not args.use_origin_ref_number
    reterive_result_mode=args.reterive_result_mode
    _paper_id =os.path.basename(tmp_html_path.replace('.html',''))
    paper_id = f"ArXiv.{_paper_id}"
    with open(tmp_html_path,'r',encoding='utf-8', errors='ignore') as f:
        soup_whole = BeautifulSoup(
            htmlmin.minify(
                f.read().replace("\xa0", " "),
                remove_all_empty_space=1,
            ),
            features="html.parser",
            )

    
    soup = soup_whole.article
    if not soup: return 'NoArticle'
    ReferenceDir= os.path.join(output_dir, "Reference")
    

    ref_count = retrieve_all_cite(soup)
    new_soup = deepcopy(soup)
    new_soup,reference_labels,bibitem_ref_metadata,note_ref_labels, note_ref_metadata= remove_entire_bibliography_and_build_labels(new_soup,ref_count, args)
    if len(note_ref_metadata)>5:
        for key,val in note_ref_metadata.items():
            logging.info(f"{key} ==> [ {better_latex_sentense_string(' '.join(val[1].text))} ]")
        checkTooManyNote(f'the note_ref_metadata num={len(note_ref_metadata) } is too much , please check the file {tmp_html_path}')
        logging.warning('WARNING:Too Many note, we roll back to no note mode')
        args.passNote = True
        soup,reference_labels,bibitem_ref_metadata,note_ref_labels, note_ref_metadata= remove_entire_bibliography_and_build_labels(soup,ref_count,args)
    else:
        soup= new_soup

    reference_labels, reference_labels_not_in_context = divide_the_dict_into_two_part_by_keys(reference_labels, ref_count)
    note_ref_labels, note_ref_labels_not_in_context = divide_the_dict_into_two_part_by_keys(note_ref_labels,ref_count)
    bibitem_ref_metadata, bibitem_ref_metadata_not_in_context = divide_the_dict_into_two_part_by_keys(bibitem_ref_metadata,ref_count)
    note_ref_metadata, note_ref_metadata_not_in_context = divide_the_dict_into_two_part_by_keys(note_ref_metadata,ref_count)

    footnote_labels, footnote_metadata = remove_note_and_record_the_infomration(soup)
    note_ref_labels=note_ref_labels|footnote_labels
    note_ref_metadata=note_ref_metadata|footnote_metadata

    put_back_keys = put_note_string_back_into_each_sentence(soup,ref_count,note_ref_metadata)
    ## since we put those key back into content, we never need those key anymore and wont save them in the reference.txt
    for key in put_back_keys:
        del note_ref_labels[key]
        del note_ref_metadata[key]
    # notice, after this line, the key in note_ref_metadata and note_ref_labels is different
    
    figures_labels, figures_metadata = remove_figures_record_the_labels(soup)
    tables_labels, tables_metadata   = remove_tables_record_the_labels(soup)
    floats_labels, floats_metadata   = remove_floats_record_the_labels(soup)
    equation_group_labels = {}
    equation_labels = {}

    in_content_ref_labels = {
        'Figure':figures_labels,
        'Table':tables_labels,
        'Equation':equation_labels,
        'Equationgroup':equation_group_labels,
        'Floats':floats_labels
    }
    labels               = collect_tags_and_record_all_labels(soup)## like section and so one
    
    
    all_citation_keys = set(ref_count)
    all_reference_keys= (set(reference_labels)|
                         set(note_ref_labels)|
                         set(figures_labels)|
                         set(tables_labels)|
                         set(equation_labels)|
                         set(equation_group_labels)|
                         set(equation_group_labels)|
                         set(floats_labels))

    for val_pool in labels.values():
        all_reference_keys = all_reference_keys | set(val_pool)
    missing_citation = all_citation_keys - all_reference_keys
    missing_citation_labels = {missing_citation_label:f'MissingCite_{i}' for i,missing_citation_label in enumerate(missing_citation)}

    
    #assert len(bibitem_ref_metadata)>0, f"Error: this file [{tmp_xml_path}] donts have bib???"
    
    if reterive_result_mode:
        assert os.path.exists(os.path.join(ReferenceDir,'reference.keys.done'))
        assert os.path.getsize(os.path.join(ReferenceDir,'reference.txt')) == 0, "if you want to inject the reterive result, please make sure all the element is reterived"
        with open(os.path.join(ReferenceDir,'reference.keys.done'),'r') as f:
            reference_keys = [t.strip() for t in f]
        with open(os.path.join(ReferenceDir,'reference.es_retrived_citation.json.done'),'r') as f:
            reference_reterives = json.load(f)
        assert len(reference_keys) == len(reference_reterives), "the reterive result should have the same length as the keys"
        new_label_mapping = {}
        for key, reterive_result in zip(reference_keys,reference_reterives):
            if key not in new_label_mapping:new_label_mapping[key] = []
            new_label_mapping[key].append(get_unique_id_from_reterive_result(reterive_result))
        for key in new_label_mapping.keys():
            new_label_mapping[key] = "<"+ ",".join(new_label_mapping[key]) + ">"
        reference_labels = new_label_mapping


    whole_ref_to_labels = collect_whole_reference(in_content_ref_labels|
                                                  {'Reference':reference_labels,'Missing':missing_citation_labels}|
                                                  labels, 
                                                  use_count_type_ref=use_count_type_ref)

    lack_ref = list(set(ref_count) - (set(all_reference_keys)|set(whole_ref_to_labels)))
    if len(lack_ref)>0:
        logging.info(f'you have {len(lack_ref)} ref lacks, such as {lack_ref[:4]}, please check the file {tmp_html_path}')
        raise MisMatchRefError
    
    ## now, the left note metadata is those string looks like a citation, and we will put them back into the bibitem information
    for remain_key, remain_val in note_ref_metadata.items():
        
        reference_labels[remain_key]=note_ref_labels[remain_key]
        string = cleanup_reference_string(remain_val[1], whole_ref_to_labels,paper_id, refs_that_wont_recovery=put_back_keys)
        bibitem_ref_metadata[remain_key]=better_latex_sentense_string(string)

    
    whole_ref_to_labels = collect_whole_reference(in_content_ref_labels|
                                                  {'Reference':reference_labels,'Missing':missing_citation_labels}|
                                                  labels, 
                                                  use_count_type_ref=use_count_type_ref)

    recovery_whole_citation_complete(soup,whole_ref_to_labels, paper_id,refs_that_wont_recovery=[])


    for remain_key, remain_val in note_ref_metadata_not_in_context.items():
        string = cleanup_reference_string(remain_val[1], whole_ref_to_labels,paper_id, refs_that_wont_recovery=put_back_keys)
        note_ref_metadata_not_in_context[remain_key]=better_latex_sentense_string(string)
        ## do this again since we modify the bibitem_ref_metadata
    
    for metadatapool in [figures_metadata, tables_metadata, floats_metadata]:
        for remain_key, remain_val in metadatapool.items():
            string = cleanup_reference_string(remain_val, whole_ref_to_labels,paper_id, refs_that_wont_recovery=put_back_keys)
            metadatapool[remain_key]=better_latex_sentense_string(string)

    
    whole_metadata = {'figures_metadata':figures_metadata,
                      'tables_metadata':tables_metadata,
                      'floats_metadata':floats_metadata,
                      'bibitem_ref_metadata':bibitem_ref_metadata,}
        
    content_soup = copy.deepcopy(soup)
    appendix_content = []
    if content_soup.find(class_='ltx_appendix'):
        appendix_soup = content_soup.find(class_='ltx_appendix')
        appendix_content = collect_sections_to_content(appendix_soup, args)
        appendix_soup.decompose()
    elif content_soup.find(class_='ltx_part'):
        appendix_soup = content_soup.find(class_='ltx_part')
        appendix_content = collect_sections_to_content(appendix_soup, args)
        appendix_soup.decompose()
    
    #index_content    =  collect_specific_section_and_remove(content_soup,name='ltx_index')
 
    sections_contnet = collect_sections_to_content(content_soup, args)
    if len(appendix_content) > 0 and len(sections_contnet)==0:
        ### if we only have appendix, we will treat the appendix as the main content ## the tex source may a supplementary
        sections_contnet = appendix_content
        appendix_content = []
    #assert len(content_soup.find_all('section')) ==0, f"why the html wont have ltx section but have another section type, please check"
    output_dict = {'appendix':appendix_content,
                   'sections':sections_contnet,
                   #'index':index_content,
                   'metadata':whole_metadata,
                   'paper_id':paper_id,
                   'whole_ref_to_labels':whole_ref_to_labels,
                   'missing_citation_labels':missing_citation_labels}
    os.makedirs(output_dir, exist_ok=True)
    
    
    if args.outputmd:
        Content_Path = os.path.join(output_dir, f'{_paper_id}.retrieved.md') if reterive_result_mode else os.path.join(output_dir, f'{_paper_id}.md')
        with open(Content_Path, 'w') as f:
            f.write(sections_contnet[0])
           
    else:
        Content_Path = os.path.join(output_dir, f'{_paper_id}.retrieved.json') if reterive_result_mode else os.path.join(output_dir, f'{_paper_id}.json')
        with open(Content_Path, 'w') as f:json.dump(output_dict, f, indent=2)
    #logging.info(Content_Path)
    if not reterive_result_mode and not args.do_not_generate_reference:
        keys  = list(bibitem_ref_metadata.keys())
        citation_string = [bibitem_ref_metadata[key] for key in keys]
        ReferenceDir= os.path.join(output_dir, "Reference")
        os.makedirs(ReferenceDir, exist_ok=True)
        with open(os.path.join(ReferenceDir, f'reference.keys'), 'w') as f:
            for key in keys:f.write(key+'\n')
        with open(os.path.join(ReferenceDir, f'reference.txt'), 'w') as f:
            for string in citation_string:f.write(string+'\n')
        with open(os.path.join(ReferenceDir, f'bibitem_ref_metadata_not_in_context.json'), 'w') as f:
            json.dump(bibitem_ref_metadata_not_in_context, f, indent=2)
        with open(os.path.join(ReferenceDir, f'note_ref_metadata_not_in_context.json'), 'w') as f:
            json.dump(note_ref_metadata_not_in_context, f, indent=2)
    
        # for section in collect_whole_section_into_one_paper(tree):
        #     logging.info(f"=========> {section['section_title']} <============")
        #     for paragraph in section['section_content']:
        #         logging.info("=======================")
        #         for sentense in paragraph:
        #             logging.info(sentense)
    return 'Finish'

def html_to_json_one_path(file_path, args:HTMLtoMDConfig)->Tuple[str,str]:
    file_path = file_path.strip()
    if not os.path.exists(file_path):
        return file_path, 'NoFile'
    if os.path.getsize(file_path) < 50_000:
        return file_path, 'toosmall'
    arxivid   = os.path.basename(file_path.replace('.html',''))
    arxivid_parent = os.path.basename(os.path.dirname(file_path))
    if not os.path.exists(file_path):
        return file_path, 'NoHTML'
    if args.savepath:
        output_root = os.path.join(args.savepath,arxivid_parent,arxivid)
    else:
        output_root = os.path.dirname(file_path.replace("archive_html","archive_json")) #os.path.dirname(file_path)
    
    
    
    output_dir  = os.path.join(output_root, 'uparxive_V3')
    if args.outputmd:
        target_file = os.path.join(output_dir, arxivid+'.md')
    else:
        target_file = os.path.join(output_dir, arxivid+'.json')

    if os.path.exists(target_file) and not args.redo:
        return arxivid, 'Skip'
    try:
        code = deal_with_html_file(file_path, output_dir, args)
        return arxivid,code
    except KeyboardInterrupt:
        raise
    except MathDontHaveTex:
        logging.info(f"MathDontHaveTex ===> {file_path}")
        return arxivid,'MathDontHaveTex'
    except lxml.etree.XMLSyntaxError:
        logging.info(f"bad xml file ===> {file_path}")
        if args.verbose:traceback.print_exc()
        return arxivid,'badxml'
    except TooManyNoteError:
        #logging.info(f"too many note ===> {file_path}")
        #analysis['TooManyNoteError'].append(file_path)
        return arxivid,'TooManyNoteError'
    except CiteDontHaveBibRefError:
        #logging.info(f"cite dont have bibref ===> {file_path}")
        #analysis['CiteDontHaveBibRefError'].append(file_path)
        return arxivid,'CiteDontHaveBibRefError'
    except MisMatchRefError:
        #logging.info(f"mismatch ref ===> {file_path}")
        #analysis['MisMatchRefError'].append(file_path)
        return arxivid,'MisMatchRefError'
    except:
        
        if args.verbose == 1:
            traceback.print_exc()
        #tqdm.write(f"fail ===> {file_path}")
        if args.debug:
            logging.error(f"fail ===> {file_path}")
            raise
        return file_path,'Fail'
    
def html_to_json_one_path_wrapper(args):
    arxiv_path, args = args
    
    return html_to_json_one_path(arxiv_path, args)
