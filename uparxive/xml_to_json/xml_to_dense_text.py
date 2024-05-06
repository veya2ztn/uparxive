###############
"""
Some known problem:
    - ~~See 0709.2524: The section after \appendix will not be collected into the main content. (The latexml do generate appendix, so we should fix it here)~~

"""
from lxml import etree
from typing import Dict
from copy import deepcopy
import lxml
import logging
import os
from .check_string_is_citation import *
from .utils import *
from ..batch_run_utils import BatchModeConfig, dataclass
from tqdm.auto import tqdm
### set the loger in warning mode
log_level = os.environ.get('LOG_LEVEL', 'WARN')
logging.basicConfig(level=log_level, format='%(asctime)s - %(levelname)s - %(message)s')


enable_checkCiteDontHaveBibRef = False
enable_checkTooManyNote= True

def checkCiteDontHaveBibRef(string):
    if enable_checkCiteDontHaveBibRef:
        logging.info(string)
        raise CiteDontHaveBibRefError
    else:
        logging.info(string)
        return 

def checkTooManyNote(string):
    if enable_checkTooManyNote:
        logging.info(string)
        raise TooManyNoteError
    else:
        logging.info(string)
        return 

def put_ref_back_and_clean_format(sentense,labels_reference,paper_id, refs_that_wont_recovery=[]):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    for ref in sentense.xpath('.//default:ref', namespaces=ns):recovery_ref_in_sentense(ref, labels_reference,paper_id=paper_id)
    for ref in sentense.findall(f'.//default:text', ns):recovery_text_in_sentense(ref)
    for ref in sentense.findall(f'.//default:emph', ns):recovery_text_in_sentense(ref)
    for ref in sentense.findall(f'.//default:break', ns):recovery_text_in_sentense(ref)
    for ref in sentense.xpath('.//default:cite', namespaces=ns):recovery_citation_in_sentense(ref, labels_reference,paper_id=paper_id,refs_that_wont_recovery=refs_that_wont_recovery)
    return sentense

def beauty_each_sentense(tree):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    
    elements = tree.xpath('.//default:p', namespaces=ns)
    for element in elements:
        #put_ref_back_and_clean_format(element,labels_reference,paper_id=paper_id,refs_that_wont_recovery=refs_that_wont_recovery)
        element.text = better_latex_sentense_string(element.text)
    return tree

#################################################################################
########################### build_reference_dictionary###########################
#################################################################################
##### there are two type of tag removing and record
##### Firstly, for those wont have rich context like math/reference, we remove the tag and record the label
def remove_tags_and_record_the_labels(tree, element_name):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    elements = tree.findall(f'.//default:{element_name}', ns)
    labels = {}
    for element_id, element in enumerate(elements):
        tag = element.find('.//default:tags', ns)
        if tag is not None:
            refnum_tag = tag.find('.//default:tag[@role="refnum"]', ns)
            refnum_txt = refnum_tag.text if refnum_tag is not None else f"{element_name}_{element_id}"
            if 'labels' in element.attrib:
                labels_key = element.attrib['labels']
                labels_keys= [t.strip() for t in labels_key.split()]
                for labels_key in labels_keys:
                    labels[labels_key]=refnum_txt
            tag.getparent().remove(tag)
        elif 'labels' in element.attrib:
            labels_key = element.attrib['labels']
            labels_keys= [t.strip() for t in labels_key.split()]
            refnum_tag = element.get('{http://www.w3.org/XML/1998/namespace}id')
            assert refnum_tag is not None
            for labels_key in labels_keys:
                labels[labels_key]=refnum_tag
            
    return tree, labels

def remove_tags_and_record_alllabels(tree, exclude_keys=['figures','figure','tables','table','bibref']):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    elements = tree.xpath('//*[@labels]')
    labels = {}
    exclude_keys = set(exclude_keys)
    for element in elements:
        tagname = element.tag.replace('{http://dlmf.nist.gov/LaTeXML}','').lower()
        if tagname in exclude_keys:continue
        tagname = tagname.capitalize()
        
        if tagname not in labels:
            labels[tagname] = {}
        tag = element.find('.//default:tags', ns)
        if tag is not None:
            refnum_tag = tag.find('.//default:tag[@role="refnum"]', ns)
            if refnum_tag is None:
                autoref = tag.find('.//default:tag[@role="autoref"]', ns)
                typerefnum =tag.find('.//default:tag[@role="typerefnum"]', ns) 
                if autoref is None and typerefnum is None:
                    logging.info(f"""the tag 
                        {view_xml(tag)}
                        has no refnum""")
                    continue
                else:
                    if typerefnum is None:refnum_text = autoref.text
                    elif autoref is None: refnum_text = typerefnum.text
                    else:
                        refnum_text = f"{autoref.text}:{typerefnum.text}" 

            else:
                refnum_text = refnum_tag.text
            if 'labels' in element.attrib:
                labels_key = element.attrib['labels']
                labels_keys= [t.strip() for t in labels_key.split()]
                for labels_key in labels_keys:
                    labels[tagname][labels_key]=refnum_text
            tag.getparent().remove(tag)
        else:
            labels_key = element.attrib['labels']
            labels_keys= [t.strip() for t in labels_key.split()]
            refnum_tag = element.get('{http://www.w3.org/XML/1998/namespace}id')
            assert refnum_tag is not None
            for labels_key in labels_keys:
                labels[tagname][labels_key]=refnum_tag

    return tree, labels


def remove_tags_in_equation_and_record_the_labels(tree):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    equation_elements = tree.findall('.//default:equation', ns)
    equation_labels = {}
    for equation in equation_elements:
        tag = equation.find('.//default:tags', ns)
        if tag is not None:
            refnum_tag = tag.find('.//default:tag[@role="refnum"]', ns)
            
            if 'labels' in equation.attrib:
                labels = equation.attrib['labels']
                equation_labels[labels]=refnum_tag.text
            
            tag.getparent().remove(tag)
    return tree, equation_labels

def parse_bibitem(bibitem,bibindex,filte_out_note,note_ref_labels,note_ref_metadata, bibitem_ref_labels,bibitem_ref_metadata,verbose):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    tag = bibitem.find('.//default:tags', ns)
    if  tag is None and len(bibitem.attrib) == 0:
        logging.warning("empty ref ???")
        return ### 
    if tag is None:
        logging.warning(f"WARNING: the bibitem {bibitem.attrib} has no tag")
        refnum_tag = None
    else:
        refnum_tag = tag.find('.//default:tag[@role="refnum"]', ns)
        
    if 'key' in bibitem.attrib:
        labels = bibitem.attrib['key']
    else:
        labels = bibitem.get('{http://www.w3.org/XML/1998/namespace}id')
        if labels is None:  
            
            logging.info(f"""
                ========== this bibitem dont have label ???? ========
                    {view_xml(bibitem)}
                =====================================================
                """)
            return
    if tag is not None: tag.getparent().remove(tag)
    
    
    bibblocks= bibitem.findall('.//default:bibblock', ns)
    
    bibstring = better_latex_sentense_string(" ".join([" ".join(bibblock.itertext()) for bibblock in bibblocks]))
    iscitationQ = True 
    hardcitationQ = False
    for bibblock in bibblocks:
        if not filte_out_note:continue
        if (bibblock.find('.//default:ref', ns) is not None):
            ref = bibblock.find('.//default:ref', ns)
            if 'labelref' in ref.attrib:
                iscitationQ = False
                hardcitationQ = True
                if verbose:
                    print(f'{labels}:{bibstring} is regard as note since it has `labelref`')
        if (bibblock.find('.//default:cite', ns) is not None):
            cite   = bibblock.find('.//default:cite', ns)
            bibref = cite.find('.//default:bibref', ns)
            if bibref is not None and 'bibrefs' in bibref.attrib and bibref.attrib['bibrefs'].strip() in [labels.strip(),"reprints"]:
                cite.getparent().remove(cite)
            else:
                iscitationQ = False
                hardcitationQ = True
                if verbose:
                    print(f'{labels}:{bibstring} is regard as note since it has `cite`')
        if bibblock.find('.//default:Math', ns) is not None:
            #assert len(bibblocks)==1, f"why this reference string has two bibblocks"
            all_mathblock = bibblock.findall('.//default:Math', ns)
            note_math_count = 0
            for mathblock in all_mathblock:
                if 'tex' not in mathblock.attrib:continue
                # Only search for direct children XMApp blocks
                mathapp_blocks = mathblock.findall('./default:XMath/default:XMApp', ns) 
                for mathapp_block in mathapp_blocks:
                    submathapps = mathapp_block.findall('.//default:XMApp', ns) 
                    #print(len(submathapps))
                    if len(submathapps)<=1:continue
                    note_math_count+=1
                # if len(mathblock.attrib['tex'].strip())<7:continue
                # if bool(re.fullmatch(r'\\ddot\{[a-zA-Z]\}', mathblock.attrib['tex'].strip())):continue
                # if bool(re.fullmatch(r'\\bar\{[a-zA-Z]\}', mathblock.attrib['tex'].strip())):continue
                # if mathblock.attrib['tex'].strip() in ['-']:continue
                
            if note_math_count>0:
                iscitationQ = False
                hardcitationQ = True
                if verbose:
                    print(f'{labels}:{bibstring} is regard as note since it has `long math`')
    if iscitationQ and filte_out_note:
        iscitationQ = not should_the_string_be_regard_as_note(bibstring)
        if verbose and not iscitationQ:
            print(f'{labels}:{bibstring} is regard as note since it has `string judge`')
    if refnum_tag is None:
        refnumtext = f"ref_{bibindex}"
    else:
        refnumtext = " ".join(refnum_tag.itertext())#< this is needed cause some paper will use <tag role="refnum"><text fontsize="90%">(40)</text></tag> like quant-ph_0102079
    if not iscitationQ:
        
        ## then, this block is a note, should save whole xml code in this block and put them into main content
        note_ref_labels[labels]=refnumtext
        bibblock = bibblocks[0]
        if bibblock.text:
            bibblock.text = "[[[Notice: " + bibblock.text
        
        bibblock = bibblocks[-1]
        # Modify the last text part of the bibblock
        last_child_element = None
        for child in bibblock.iterchildren():
            last_child_element = child
        if last_child_element is not None and last_child_element.tail:
            last_child_element.tail += "]]]"
        elif last_child_element is not None:
            last_child_element.tail = "]]]"
        else:
            bibblock.text = (bibblock.text or '') + "]]]"

        note_ref_metadata[labels]= [hardcitationQ, deepcopy(bibitem)]
    else:
        #refnum_int = int(refnumtext)
        bibitem_ref_labels[labels]= refnumtext
        bibitem_ref_metadata[labels]=bibstring

def parse_bibentry(bibitem,bibindex,filte_out_note,note_ref_labels,note_ref_metadata, bibitem_ref_labels,bibitem_ref_metadata,verbose):
    """
    Usually caused by directly write .bib format in .tex file. For example, arxiv: 1004.4054
    """
    """
        <bibentry key="ChildsUniv" type="article" xml:id="bib.bib6">
          <bib-name role="author">
            <surname>Childs</surname>
            <givenname>A. M.</givenname>
          </bib-name>
          <bib-title>Universal computation by quantum walk</bib-title>
          <bib-related role="host" type="journal">
            <bib-title>Physical Review Letters</bib-title>
          </bib-related>
          <bib-part role="volume">102</bib-part>
          <bib-part role="number">180501</bib-part>
          <bib-date role="publication">2009</bib-date>
          <bib-note role="annotation">Also available at <ref class="ltx_href"
              href="http://arxiv.org/abs/0806.1972">arXiv:0806.1972v1</ref></bib-note>
          <bib-data role="self" type="BibTeX">@article{ChildsUniv,
            author = {Childs, A.~M.},
            title = {Universal computation by quantum walk},
            journal = {Physical Review Letters},
            volume = {102},
            number = {180501},
            year = {2009},
            note = {Also available at \href{http://arxiv.org/abs/0806.1972}{arXiv:0806.1972v1}}}
          </bib-data>
        </bibentry>
    """
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}

    ### first, find the ref id
    if 'key' in bibitem.attrib:
        labels = bibitem.attrib['key']
    else:
        labels = bibitem.get('{http://www.w3.org/XML/1998/namespace}id')
        if labels is None:  
            logging.info(f"""
                ========== this bibitem dont have label ???? ========
                    {view_xml(bibitem)}
                =====================================================
                """)
            return
    ### bibentry wont have the refnum tag, so lets use the id  
    refnumtext = bibitem.get('{http://www.w3.org/XML/1998/namespace}id') ## something like "bib.bib19"
    
    ### if we use this, it must be a citation
    bib_origin = bibitem.find('.//default:bib-data[@role="self"]', ns)
    if bib_origin is not None:
        bib_origin.getparent().remove(bib_origin)
        # from python_script.CitationStyleLanguage import CitationStyleLanguage
        # import python_script.bibjson as bibjson
        # bibstring = " ".join(bibstring.itertext())
        # #bibstring = merge_author(bibstring)
        # bibstring = better_latex_sentense_string(bibstring)
        # bibjson_collection = bibjson.collection_from_bibtex_str(bibstring,collection='.bib')
        # if len(bibjson_collection['records']) == 0:
        #     print(bibstring)
        #     print(bibjson_collection)
        #     
        # bibpool   = bibjson_collection['records'][0]
        # citation  = CitationStyleLanguage.from_dict(bibpool)
        # bibstring = citation.to_citation(size='full')
    
    # name  = bibitem.find('.//default:bib-name', ns)
    # title = bibitem.find('.//default:bib-title', ns)
    # type  = bibitem.find('.//default:bib-type', ns)
    # date  = bibitem.find('.//default:bib-date', ns)
    # organization = bibitem.find('.//default:bib-organization', ns)
    # note  = bibitem.find('.//default:bib-note', ns)
    # publisher = bibitem.find('.//default:bib-publisher', ns)
    # volumn= bibitem.find('.//default:bib-part[@role="volume"]', ns)
    # number= bibitem.find('.//default:bib-part[@role="number"]', ns)
    # pages = bibitem.find('.//default:bib-part[@role="pages"]', ns)
    # journel= bibitem.find('.//default:bib-related[@role="host"]', ns)
    bibstring = []
    for child in bibitem:
        bibstring.append(better_latex_sentense_string(" ".join(child.itertext())))
    bibstring = ", ".join(bibstring)
        
    
    bibitem_ref_labels[labels]= refnumtext
    bibitem_ref_metadata[labels]=bibstring

def remove_entire_bibliography_and_build_labels(tree,verbose=False,filte_out_note=True):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}

    # Find all 'Math' elements using the namespace
    bio_elements = tree.findall('.//default:bibliography', ns)
    bibitem_ref_labels = {}
    bibitem_ref_metadata = {}
    note_ref_labels = {}
    note_ref_metadata={}
    none_cited_item = 0

    for bio_element in bio_elements:
        bibitems = list(bio_element.findall('.//default:bibitem', ns))
        for bibindex, bibitem in enumerate(bibitems):
            parse_bibitem(bibitem,bibindex,filte_out_note,note_ref_labels,note_ref_metadata, bibitem_ref_labels,bibitem_ref_metadata,verbose=verbose)
        bibitems = list(bio_element.findall('.//default:bibentry', ns))
        for bibindex, bibitem in enumerate(bibitems):  
            parse_bibentry(bibitem,bibindex,filte_out_note,note_ref_labels,note_ref_metadata, bibitem_ref_labels,bibitem_ref_metadata,verbose=verbose)
        bio_element.getparent().remove(bio_element)
        
    return tree, bibitem_ref_labels, bibitem_ref_metadata, note_ref_labels, note_ref_metadata
##### Secondly, for those have rich context like caption, we remove the tag and record the label and record the caption

def remove_figures_record_the_labels(tree):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}

    # Find all 'Math' elements using the namespace
    elements = tree.findall('.//default:figure', ns)
    
    ref_labels = {}
    ref_metadata = {}
    for i, element in enumerate(elements):
        
        tag = element.find('.//default:tags', ns)
        if tag is not None and tag.find('.//default:tag[@role="refnum"]', ns) is not None:
            refnum_tag = tag.find('.//default:tag[@role="refnum"]', ns).text
        else:
            refnum_tag = i+1
        labels = element.attrib['labels'] if 'labels' in element.attrib else f"Figs_{i+1}"
        labels = labels.split()
        for label in labels:ref_labels[label]=refnum_tag
        caption = element.find('.//default:caption', ns)
        if caption is not None:
            tag_cap = caption.find('.//default:tags', ns)
            if tag_cap is not None:tag_cap.getparent().remove(tag_cap)
            for label in labels:ref_metadata[label]=caption
        else:
            ### if the caption is None, then we will regard all the text in figure tag as caption
            revert_math_into_its_origin_text_in_xml(element)
            for label in labels:ref_metadata[label]=element
            #logging.info(ref_metadata[labels])
        element.getparent().remove(element)
    return tree, ref_labels, ref_metadata

def view_xml(cite):
    return "="*10 + '\n' + etree.tostring(cite, pretty_print=True).decode('utf-8') + '\n' + "="*10 

def remove_tables_record_the_labels(tree):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}

    # Find all 'Math' elements using the namespace
    elements = tree.findall('.//default:tabel', ns)
    ref_labels = {}
    ref_metadata = {}
    for i, element in enumerate(elements):

        tag = element.find('.//default:tags', ns)
        assert tag is not None
        refnum_tag = tag.find('.//default:tag[@role="refnum"]', ns)
        labels = element.attrib['labels'] if 'labels' in element.attrib else f"Tabs_{i}"
        labels = labels.split()
        for label in labels:ref_labels[label]=refnum_tag.text
        caption = element.find('.//default:caption', ns)
        # remove the tag in caption
        tag_cap = caption.find('.//default:tags', ns)
        if tag_cap is not None:caption.remove(tag_cap)
        for label in labels:ref_metadata[label]=caption
        element.getparent().remove(element)
    return tree, ref_labels, ref_metadata

def remove_an_element(element):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}

    text = better_latex_sentense_string((element.tail or ""))
    # If the 'Math' element has a preceding sibling, append the text to the sibling's tail
    # Otherwise, append the text to the parent's text
    previous = element.getprevious()
    if previous is not None:
        if previous.tail:
            previous.tail += text
        else:
            previous.tail = text
    else:
        parent = element.getparent()
        if parent.text:
            parent.text += text
        else:
            parent.text = text

    # Remove the 'Math' element from the tree
    element.getparent().remove(element)


def remove_a_tagblock(tree, name):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}

    # Find all 'Math' elements using the namespace
    elements = tree.findall(f'.//default:{name}', ns)

    # Iterate over all found 'Math' elements
    for element in elements:
        remove_an_element(element)
 

def discard_note(tree):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    name = 'note'
    # Find all 'Math' elements using the namespace
    elements = tree.findall(f'.//default:{name}',ns)
    for element in elements:
        remove_a_tagblock(element, 'tags')
        text = '[[[Notice: '
        previous = element.getprevious()
        if previous is not None:
            if previous.tail:
                previous.tail += text
            else:
                previous.tail = text
        else:
            parent = element.getparent()
            if parent.text:
                parent.text += text
            else:
                parent.text = text


        element_parent = element.getparent()
        append_tex  = (element.tail or "")
        append_tex = ']]] '+ append_tex
        last_child_element = None
        for child in element.iterchildren():
            last_child_element = child
        if last_child_element is not None and last_child_element.tail:
            last_child_element.tail += append_tex
        elif last_child_element is not None:
            last_child_element.tail = append_tex
        else:
            element.text = (element.text or '') + append_tex
        
        for i,child in enumerate(element):
            element_parent.insert(element_parent.index(element), child)
        
        element_parent.remove(element)
#################################################################################



def recovery_text_in_sentense(ref):
    text = ref.text
    
    #     if element.attrib['font'] == 'italic':
    #         text = f"*{text}*"
    if 'font' in ref.attrib and ref.attrib['font'] == 'bold':
        text = f"**{text}**"
    element = ref.getparent()
    prev = ref.getprevious()
    the_reference_label = text if text is not None else ""
    if prev is not None:
        if prev.tail:
            prev.tail += the_reference_label
        else:
            prev.tail = the_reference_label
    else:
        if element.text:
            element.text += the_reference_label
        else:
            element.text = the_reference_label

    # If the reference has a tail, transfer it to the previous element or to the overall element
    if ref.tail:
        if prev is not None:
            if prev.tail:
                prev.tail += ' ' + ref.tail
            else:
                prev.tail = ' ' + ref.tail
        else:
            if element.text:
                element.text += ' ' + ref.tail
            else:
                element.text = ' ' + ref.tail

    # Remove the ref element
    ref.getparent().remove(ref)

### deal with math


def recovery_ref_in_sentense(ref, labels_reference,paper_id):
    element = ref.getparent()
    if 'labelref' not in ref.attrib:
        
        if ref.text is None:
            if 'href' in ref.attrib:return
            if 'idref' in ref.attrib :return
            if 'class' in ref.attrib and('ltx_url' in ref.attrib['class'] or 
                                         'ltx_href'  in ref.attrib['class'] or
                                         'ltx_nolink'  in ref.attrib['class']
                                         ):return
            if len(ref.attrib) == 0: return # this is an empty ref
            logging.warning(f"""ref of element dont have ref??? See
                  {ref.attrib}
                   {view_xml(ref)} """
                   )
            raise 
        else:
            labelref = " ".join(ref.itertext())
            ref_type = "URL"
            label = labelref
    else:
        labelrefs = ref.attrib['labelref'].split(',')
        labels = []
        for labelref in labelrefs:
            try:
                reflabels = labels_reference[labelref]
            except KeyError:
                logging.info(f"we want to use key = {labelref}, but the collect labels pool only have ")
                for key,val in labels_reference.items():
                    logging.info(f"{key} ==> {val}")
                raise
            if len(reflabels)>1:
                logging.info(f'multiple label detected for {labelref} => {reflabels}, we will use the first one')
            ref_type, label_now = reflabels[0]
            labels.append(str(label_now))
        label = ",".join(labels)
    
    isactivated=False
    right = ref.tail.lstrip() if ref.tail else ""
    prev  = ref.getprevious()
    if prev is not None:
        left = prev.tail
        left, right = discard_brackets(left,right)
        
        if left:
            left, label, isactivated = go_ahead_and_add_label(left,label,paper_id)      
        else:
            left = ""
        #isactivated=True
        if not isactivated:
            if ref_type.lower() in ['url']:
                label = label
 
            elif ref_type.lower() not in ['equation','formula']:
                label = f" (See [{ref_type}.{label} of {paper_id}]) "
            else:
                label = f"[{ref_type}.{label} of {paper_id}]"
        left, right = discard_brackets(left,right)
        prev.tail = f"{left} {label} {right}"
    else:
        left = element.text
        left, right = discard_brackets(left,right)

        if left:
            left, label, isactivated = go_ahead_and_add_label(left,label,paper_id)
        else:
            left=""
        #isactivated=True
        if not isactivated:
            
            if ref_type.lower() in ['url']:
                label = label
  
            elif ref_type.lower() not in ['equation','formula']:
                label = f" (See [{ref_type}.{label} of {paper_id}]) "
            else:
                label = f" [{ref_type}.{label} of {paper_id}] "
        element.text = f"{left} {label} {right}"


    # Remove the ref element
    ref.getparent().remove(ref)

def recovery_citation_in_sentense(cite, labels_reference,paper_id,refs_that_wont_recovery=[]):
    
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    bibref = cite.find('.//default:bibref', ns)
    if bibref is None:
        checkCiteDontHaveBibRef(f""" cite of 
              {view_xml(cite)} 
              dont have bibref???
              """)
        cite.getparent().remove(cite)
        return 
    text = bibref.attrib['bibrefs']
    
    refs = [t.strip() for t in text.split(',')]
    refs = [ref for ref in refs if ref not in refs_that_wont_recovery] # if the ref in refs_that_wont_recovery, this mean we directly remove the ref and won't use [See xxxx] formation
    label_list = []
    for ref in refs:
        reflabels = labels_reference[ref]

        if len(reflabels)>1:
            logging.info(f"multiple label detected: {reflabels}, we will use the first one")
        ref_type, label = reflabels[0]
        label_list.append(label)
    right = cite.tail
    do_post_reference_normilization = False
    previous = cite.getprevious()
    if previous is not None:
        # Check if the tail of the previous element ends with "See" or "See Ref."
        left = previous.tail
    else:
        parent = cite.getparent()
        left   = parent.text
    left, right = discard_brackets(left,right)
    
    string = ",".join(label_list)
    string = string.replace('>,<',',') ## if multiple ref together, it will cause <doi:xxx>,<doi:xxx>,.....
    if not string.strip():
        whole_string = f"{left} {right}"
    else:
        label = "[" + string + ']'
        if left:
            left, label, isactivated = go_ahead_and_add_label(left,label,paper_id)      
        else:
            left = ""
        label = format_the_smart_citation(left, label, right, paper_id)
        whole_string = f"{left} {label} {right}"

    #if do_post_reference_normilization: whole_string = replace_number_citation_marks(whole_string,paper_id)
    if previous is not None:    
        previous.tail = whole_string
    else:
        parent.text = whole_string
    # Remove the 'cite' element from the tree
    cite.getparent().remove(cite)

def remove_MathFork_in_equation(tree):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    equation_elements = tree.findall('.//default:equation', ns)
    for equation in equation_elements:
        MathFork = equation.find('.//default:MathFork', ns)
        if MathFork is not None:
            MathBranch = MathFork.find('.//default:MathBranch', ns)
            
            if MathBranch is not None:
                try:
                    MathFork.remove(MathBranch)
                except:
                    logging.warn(f'in the default mode, we will remove the MathBranch(I forget why), it seem the result still good if not remove the Branch')
                    pass
            text = MathFork.text
            #logging.info(text)
            if MathFork.tail:
                text += MathFork.tail
            previous = MathFork.getprevious()
            if previous is not None:
                if previous.tail:
                    previous.tail += text
                else:
                    previous.tail = text
            else:
                parent = MathFork.getparent()
                if parent.text:
                    parent.text += text
                else:
                    parent.text = text
            MathFork.getparent().remove(MathFork)
    return tree

def revert_math_into_its_origin_text_in_xml(tree):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}

    # Find all 'Math' elements using the namespace
    math_elements = tree.findall('.//default:Math', ns)

    # Iterate over all found 'Math' elements
    for math in math_elements:
        # If the 'Math' element has a tail (text after the 'Math' element), 
        # append it to the 'tex' attribute
        if 'tex' in math.attrib:
            text = math.attrib['tex']
        else:
            text = better_latex_sentense_string(" ".join(math.itertext()))
            if not text:
                logging.info(f""" dont have tex??? See
                    {view_xml(math)}
                    {text}
                    ===================
                    """)
                raise MathDontHaveTex("the math element dont have tex??? I guess you are using a SVG ???")
        text = better_latex_math_code(text.strip())
        #logging.info(text)
        text = f"${text}$"
        if math.tail:
            text = text + math.tail
        # If the 'Math' element has a preceding sibling, append the text to the sibling's tail
        # Otherwise, append the text to the parent's text
        previous = math.getprevious()
        if previous is not None:
            if previous.tail:
                previous.tail += text
            else:
                previous.tail = text
        else:
            parent = math.getparent()
            if parent.text:
                parent.text += text
            else:
                parent.text = text

        # Remove the 'Math' element from the tree
        math.getparent().remove(math)
    return tree

def replace_equation_blocks(tree):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    equation_elements = tree.findall('.//default:equation', ns)

    # Iterate over all found 'equation' elements
    for equation in equation_elements:
        p = etree.Element('{%s}p' % ns['default'])
        text = equation.text
        if text is None:
            logging.info(f""" This part dont have equation????
                         {view_xml(equation)}
                         """)
            text = ""
        text = text.strip() 
        p.text = f"${text}$"
        equation.getparent().replace(equation, p)
        
    ## anther operation is replace the equationgroup, we will assume other part like mathmakr has already be correctly deal with.
    equationgroups = tree.findall('.//default:equationgroup', ns)
    for equationgroup in equationgroups:
        parent = equationgroup.getparent()
        p_elements = list(equationgroup)
        index = parent.index(equationgroup)
        for offset, p in enumerate(p_elements):
            parent.insert(index + offset, p)
        parent.remove(equationgroup)
    return tree  
#### Collect and resotre information

def replace_item_block_with_markdown_format(item):
    """
        <itemize xml:id="S5.I1">
            <item xml:id="S5.I1.i1">
              <tags>
                <tag>•</tag>
                <tag role="autoref">item </tag>
                <tag role="typerefnum">1st item</tag>
              </tags>
              <para xml:id="S5.I1.i1.p1">
                <p>Eighty-two percent of users were aged 18 to 34 years.</p>
              </para>
            </item>
            <item xml:id="S5.I1.i2">
              <tags>
                <tag>•</tag>
                <tag role="autoref">item </tag>
                <tag role="typerefnum">2nd item</tag>
              </tags>
              <para xml:id="S5.I1.i2.p1">
                <p>Seventy-five percent of participants reported that they used Twitter at least once a day, whereas 62% of all participants stated that they used it several times a day.</p>
              </para>
            </item>
            <item xml:id="S5.I1.i3">
              <tags>
                <tag>•</tag>
                <tag role="autoref">item </tag>
                <tag role="typerefnum">3rd item</tag>
              </tags>
              <para xml:id="S5.I1.i3.p1">
                <p>What option best describes what you use Twitter for?: The most popular answer (with a frequency of 51%) among 10 options was that participants used Twitter to keep up with or share the news in general.</p>

              </para>
            </item>
          </itemize>

        to
        <itemize xml:id="S5.I1">
            <p>
            - Eighty-two percent of users were aged 18 to 34 years.
            - Seventy-five percent of participants reported that they used Twitter at least once a day, whereas 62% of all participants stated that they used it several times a day.
            - What option best describes what you use Twitter for?: The most popular answer (with a frequency of 51%) among 10 options was that participants used Twitter to keep up with or share the news in general.
            </p>
        </itemize>
        
    """
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    elements = item.findall('.//default:item', ns)
    for element in elements:
        tag = element.find('.//default:tags', ns)
        prefix="- "
        if tag is not None:
            prefix = tag.find('.//default:tag', ns)
            if prefix is not None:
                prefix = prefix.text
                if prefix: prefix = prefix.strip('•') 
                prefix = f"- {prefix} "
            tag.getparent().remove(tag)
        ### if tag is a number then add this number at begining
        
        #all_p = element.findall('.//default:p', ns)
        ### merge all p content into one
        new_p = etree.Element('{%s}p' % ns['default'])
        new_p.text = prefix + better_latex_sentense_string(" ".join(element.itertext()))
        element.getparent().replace(element, new_p)
    return item

def remove_entire_partition_and_collect(tree, partition_name):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}

    # Find all 'Math' elements using the namespace
    elements = tree.findall(f'.//default:{partition_name}', ns)
    metadata = ""
    for element in elements:
        metadata += better_latex_sentense_string(" ".join(element.itertext()))
        element.getparent().remove(element)
        
    return tree, better_latex_sentense_string(metadata)

def collect_whole_sentense_into_one_paragraph(paragraph):
    ns       = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    elements = paragraph.findall(f'.//default:p', ns)
    whole_sentense = []
    for element in elements:
        whole_sentense.append(better_latex_sentense_string(" ".join(element.itertext())))
    return whole_sentense
    
def collect_whole_paragraph_into_one_section(section):
    ns       = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    whole_paragraph = {}
    title    = section.find(f'.//default:title', ns)
    if title is not None:
        tag = title.find(f'.//default:tag', ns)
        if tag is not None:
            if tag.tail:
                # If the tag has a tail, append it to the text of the preceding sibling or the parent
                prev = tag.getprevious()
                if prev is not None:
                    if prev.tail:
                        prev.tail += tag.tail
                    else:
                        prev.tail = tag.tail
                else:
                    if title.text:
                        title.text += tag.tail
                    else:
                        title.text = tag.tail
            # Remove the tag
            #title.remove(tag)
            whole_paragraph['tag'] =tag.text
        text = ''.join((c.tail or '') for c in title)
        whole_paragraph['section_title'] =better_latex_sentense_string(text)
    whole_paragraph['section_content']=[]
    elements = section.findall(f'.//default:para', ns)
    for element in elements:
        whole_paragraph['section_content'].append(collect_whole_sentense_into_one_paragraph(element))
    return whole_paragraph

def collect_whole_section_into_one_paper(paper, section_type='section'):
    ns       = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    elements = paper.findall(f'.//default:{section_type}', ns)
    if len(elements)==0:
        logging.info(f"Warning: the paper has no {section_type}, we then use directly paragraph")
        elements =[paper]
    
    whole_sections = []
    for element in elements:
        whole_sections.append(collect_whole_paragraph_into_one_section(element))
    
    return whole_sections 

def put_note_string_back_into_each_sentence(tree, ref_count: Dict[str, int], note_ref_metadata: Dict[str, etree._Element]):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    #all_sentences = tree.xpath('.//default:p', namespaces=ns)
    #count_whole_citation =  
    #for sentence in all_sentences:
    put_back_keys  = set()
    for cite in tree.xpath('.//default:cite', namespaces=ns):
        bibref = cite.find('.//default:bibref', ns)
        if bibref is None:continue
        text = bibref.attrib['bibrefs']
        texts = text.split(',')
        for ref in texts:
            ref = ref.strip()
            if ref in note_ref_metadata:
                hardcitationQ, bibblock = note_ref_metadata[ref]
                put_back_keys = put_back_keys|set([ref])
                if ref_count[ref]>1 and (not hardcitationQ):
                    logging.info(f"key {ref} skip, dual to many counts and its not a hardcitation")
                    continue # only when it is not type math and ref > 1 case, we dont insect note into contextf    
                #assert len(texts) == 1, f"Only single citation replacement is supported per cite element.{ref} appear more than once"
                logging.info(f"put back {ref}")
                bibblock_contents = [node for node in bibblock.iterchildren()]
                bibblock_text = bibblock.text  # Copy any leading text
                #logging.info(cite)
                parent = cite.getparent()
                if parent is not None:
                    #logging.info(parent)
                    # Find the index of the cite element
                    cite_index = parent.index(cite)
                    # Save the tail text
                    cite_tail = (cite.tail or '')

                    # Remove the cite element from its parent
                    parent.remove(cite)
                    # If there's leading text in the bibblock, add it first
                    if bibblock_text:
                        previous = parent[cite_index - 1] if cite_index > 0 else None
                        if previous is not None and previous.tail:
                            previous.tail += bibblock_text
                        elif previous is not None:
                            previous.tail = bibblock_text
                        else:
                            parent.text = (parent.text or '') + bibblock_text
#                     # Insert the deep-copied contents of bibblock at the position of the old cite
                    for node in reversed(bibblock_contents):
                        #logging.info(f"Element: {etree.tostring(node, pretty_print=True).decode('utf-8')}")
                        parent.insert(cite_index, node)
                # Append the saved tail to the last inserted node
                if bibblock_contents:
                    # If there are nodes, add tail to the last node's tail
                    last_node = bibblock_contents[-1]
                    last_node.tail = (last_node.tail or '') + cite_tail
                else:
                    # If there are no nodes, append the tail to the previous element's tail or the parent's text
                    if parent is not None: ## then we dont put it back ?????
                        if cite_index > 0:
                            prev_elem = parent[cite_index - 1]
                            prev_elem.tail = (prev_elem.tail or '') + cite_tail
                        else:
                            parent.text = (parent.text or '') + cite_tail
    for key in put_back_keys:
        del note_ref_metadata[key]
    return tree, put_back_keys


def cleanup_xml(tree, whole_ref_to_labels,paper_id,refs_that_wont_recovery):
    tree = revert_math_into_its_origin_text_in_xml(tree)
    tree = remove_MathFork_in_equation(tree)
    put_ref_back_and_clean_format(tree,whole_ref_to_labels,paper_id=paper_id,refs_that_wont_recovery=refs_that_wont_recovery)
    tree = beauty_each_sentense(tree)
    tree = replace_equation_blocks(tree)
    tree = replace_item_block_with_markdown_format(tree)
    return tree

def cleanup_reference_string(string, whole_ref_to_labels,paper_id, refs_that_wont_recovery):
    string= cleanup_xml(string, whole_ref_to_labels, paper_id, refs_that_wont_recovery = refs_that_wont_recovery)
    string = " ".join(string.itertext())
    string = string.replace("[[[Notice:","").replace("]]]","")
    
    return better_latex_sentense_string(string)
    
def retreive_all_cite(tree):
    ns = {'default': 'http://dlmf.nist.gov/LaTeXML'}
    ref_count = {}
    for bibref in tree.xpath('.//default:bibref', namespaces=ns):
        #bibref = cite.find('.//default:bibref', ns)
        if bibref is None:
            xmlstring = view_xml(bibref)
            logging.info(f"""this cite:
                  {xmlstring} 
                  wont have bibref????, we will skip it """)
            continue
        if 'bibrefs' not in bibref.attrib:
            logging.info(f"this cite:{bibref.attrib} wont have bibref????, we will remove it ")
            remove_an_element(bibref)
            continue
        text = bibref.attrib['bibrefs']
        
        texts = text.split(',')
        for ref in texts:
            ref = ref.strip()
            if ref not in ref_count:ref_count[ref]=0
            ref_count[ref]+=1
    for bibref in tree.xpath('.//default:ref', namespaces=ns):
        if 'labelref' not in bibref.attrib:continue
        text = bibref.attrib['labelref']
        texts = text.split(',')
        
        for ref in texts:
            ref = ref.strip()
            if ref not in ref_count:ref_count[ref]=0
            ref_count[ref]+=1
    return ref_count


def ensure_unique_ids(xml_content):
    tree = etree.fromstring(xml_content)
    ids_seen = set()
    id_counter = {}
    
    for element in tree.iter():
        id_value = element.get('id')
        if id_value:
            if id_value in ids_seen:
                # Increment a counter for the ID and append to make unique
                if id_value in id_counter:
                    id_counter[id_value] += 1
                else:
                    id_counter[id_value] = 1
                new_id = f"{id_value}_{id_counter[id_value]}"
                element.set('id', new_id)
            else:
                ids_seen.add(id_value)
    
    return etree.tostring(tree, pretty_print=True).decode('utf-8')


import json
def deal_with_xml_file(tmp_xml_path, output_dir, reterive_result_mode=False,verbose = False, filte_out_note=True,use_count_type_ref=False):
    reterive_result_mode = bool(reterive_result_mode)
    _paper_id = os.path.basename(os.path.dirname(tmp_xml_path))
    paper_id = f"ArXiv.{_paper_id}"
    #paper_id = identify_string_type(_paper_id.replace('_',"/"))
    parser = etree.XMLParser(remove_comments=True,recover=True, collect_ids=False)
    with open(tmp_xml_path) as f:
        tree = etree.parse(f, parser)  # get tree of XML hierarchy


    discard_note(tree)
    ref_count = retreive_all_cite(tree)
    new_tree = deepcopy(tree)
    new_tree,reference_labels,bibitem_ref_metadata,note_ref_labels, note_ref_metadata= remove_entire_bibliography_and_build_labels(new_tree,verbose=verbose, filte_out_note=filte_out_note)
    if len(note_ref_metadata)>5:
        for key,val in note_ref_metadata.items():
            logging.info(f"{key} ==> [ {better_latex_sentense_string(' '.join(val[1].itertext()))} ]")
        checkTooManyNote(f'the note_ref_metadata num={len(note_ref_metadata) } is too much , please check the file {tmp_xml_path}')
        logging.warning('WARNING:Too Many note, we roll back to no note mode')
        tree,reference_labels,bibitem_ref_metadata,note_ref_labels, note_ref_metadata= remove_entire_bibliography_and_build_labels(tree,verbose=verbose, filte_out_note=False)
    else:
        tree = new_tree
    # print(print_namespace_tree(reference_labels))
    # print("============================================")
    # print(print_namespace_tree(note_ref_labels))
    # raise
    #ref_count = retreive_all_cite(tree)
    ### now, we need divide the ref dict into two part, 1. The ref used in the tex 2. The ref note used in the tex
    reference_labels, reference_labels_not_in_context = divide_the_dict_into_two_part_by_keys(reference_labels, ref_count)
    note_ref_labels, note_ref_labels_not_in_context = divide_the_dict_into_two_part_by_keys(note_ref_labels,ref_count)
    bibitem_ref_metadata, bibitem_ref_metadata_not_in_context = divide_the_dict_into_two_part_by_keys(bibitem_ref_metadata,ref_count)
    note_ref_metadata, note_ref_metadata_not_in_context = divide_the_dict_into_two_part_by_keys(note_ref_metadata,ref_count)
    
    #if len(bibitem_ref_metadata)>0, f"Error: this file [{tmp_xml_path}] donts have bib???"

    tree,put_back_keys = put_note_string_back_into_each_sentence(tree,ref_count,note_ref_metadata)
    # notice, after this line, the key in note_ref_metadata and note_ref_labels is different
    
    tree,figures_labels, figures_metadata = remove_figures_record_the_labels(tree)
    tree,tables_labels, tables_metadata   = remove_tables_record_the_labels(tree)
    tree,equation_labels                  = remove_tags_and_record_the_labels(tree,'equation')
   
    tree,equation_group_labels            = remove_tags_and_record_the_labels(tree,'equationgroup')
    tree, labels = remove_tags_and_record_alllabels(tree, exclude_keys=['figures','figure','tables','table','bibref','equation','equationgroup'])

    all_citation_keys = set(ref_count.keys())
    all_reference_keys= (set(reference_labels.keys())|
                         set(note_ref_labels.keys())|
                         set(figures_labels.keys())|
                         set(tables_labels.keys())|
                         set(equation_labels.keys())|
                         set(equation_group_labels.keys()))

    for val_pool in labels.values():
        all_reference_keys = all_reference_keys | set(val_pool)
    missing_citation = all_citation_keys - all_reference_keys
    missing_citation_labels = {missing_citation_label:f'MissingCite_{i}' for i,missing_citation_label in enumerate(missing_citation)}

    
    #assert len(bibitem_ref_metadata)>0, f"Error: this file [{tmp_xml_path}] donts have bib???"
    
    if reterive_result_mode:
        ReferenceDir= os.path.join(output_dir, "Reference")
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


    whole_ref_to_labels = collect_whole_reference({
        'Figure':figures_labels,
        'Table':tables_labels,
        'Reference':reference_labels,
        'Equation':equation_labels,
        'Equationgroup':equation_group_labels,
        'Missing':missing_citation_labels
        }|labels, use_count_type_ref=use_count_type_ref)

    lack_ref = list(set(ref_count) - (set(all_reference_keys)|set(whole_ref_to_labels)))
    #print(set(ref_count))
    #print(set(all_reference_keys)|set(whole_ref_to_labels))
    if len(lack_ref)>0:
        logging.info(f'you have {len(lack_ref)} ref lacks, such as {lack_ref[:4]}, please check the file {tmp_xml_path}')
        raise MisMatchRefError
    
    ## now, the left note metadata is those string looks like a citation, and we will put them back into the bibitem information
    for remain_key, remain_val in note_ref_metadata.items():
        reference_labels[remain_key]=note_ref_labels[remain_key]
        string = cleanup_reference_string(remain_val[1], whole_ref_to_labels,paper_id, refs_that_wont_recovery=put_back_keys)
        bibitem_ref_metadata[remain_key]=better_latex_sentense_string(string)

    
    
    whole_ref_to_labels = collect_whole_reference({

            'Figure':figures_labels,
            'Table':tables_labels,
            'Reference':reference_labels,
            'Equation':equation_labels,
            'Equationgroup':equation_group_labels,
            'Missing':missing_citation_labels
             }|labels, use_count_type_ref=use_count_type_ref)

    tree = cleanup_xml(tree, whole_ref_to_labels,paper_id, put_back_keys)
    
    tree, abstract     = remove_entire_partition_and_collect(tree,'abstract')
    tree, acknowledge  = remove_entire_partition_and_collect(tree,'acknowledgements')


    for remain_key, remain_val in note_ref_metadata_not_in_context.items():
        string = cleanup_reference_string(remain_val[1], whole_ref_to_labels,paper_id, refs_that_wont_recovery=put_back_keys)
        note_ref_metadata_not_in_context[remain_key]=better_latex_sentense_string(string)
        ## do this again since we modify the bibitem_ref_metadata
    
    for remain_key, remain_val in figures_metadata.items():
        string = cleanup_reference_string(remain_val, whole_ref_to_labels,paper_id, refs_that_wont_recovery=put_back_keys)
        figures_metadata[remain_key]=better_latex_sentense_string(string)

    for remain_key, remain_val in tables_metadata.items():
        string = cleanup_reference_string(remain_val, whole_ref_to_labels,paper_id, refs_that_wont_recovery=put_back_keys)
        tables_metadata[remain_key]=better_latex_sentense_string(string)
        ## do this again since we modify the bibitem_ref_metadata
    
    whole_metadata = {'figures_metadata':figures_metadata,
                      'tables_metadata':tables_metadata,
                      'bibitem_ref_metadata':bibitem_ref_metadata}
        
    output_dict = {'abstract':abstract,
                     'acknowledge':acknowledge,
                     'sections':collect_whole_section_into_one_paper(tree, section_type='section'),
                     'appendix':collect_whole_section_into_one_paper(tree, section_type='appendix'),
                     'metadata':whole_metadata,
                     'paper_id':paper_id,
                     'whole_ref_to_labels':whole_ref_to_labels,
                     'missing_citation_labels':missing_citation_labels}
    os.makedirs(output_dir, exist_ok=True)
    ReferenceDir= os.path.join(output_dir, "Reference")
    os.makedirs(ReferenceDir, exist_ok=True)
    Content_Path = os.path.join(output_dir, f'{_paper_id}.retrieved.json') if reterive_result_mode else os.path.join(output_dir, f'{_paper_id}.json')
    with open(Content_Path, 'w') as f:json.dump(output_dict, f, indent=2)
    
    
    #logging.info(Content_Path)
    if not reterive_result_mode:
        keys  = list(bibitem_ref_metadata.keys())
        citation_string = [bibitem_ref_metadata[key] for key in keys]

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

import traceback
@dataclass
class XMLtoJsonConfig(BatchModeConfig):
    task_name = 'xml_to_json'
    reterive_result_mode : bool = False
    passManyNote : bool = False
    passNote : bool = False
    use_origin_ref_number : bool = False
    verbose: bool = False
from typing import Tuple
def xml_to_json_one_path(file_path, args:XMLtoJsonConfig)->Tuple[str,str]:
    file_path = file_path.strip()
    arxivid   = os.path.basename(os.path.dirname(file_path))
    if not os.path.exists(file_path):
        return file_path, 'NoXML'
    if os.path.getsize(file_path) < 100:
        return file_path, 'XMLtooSmall'
    output_root = os.path.dirname(file_path).replace('_xml','_json')
    if os.path.exists(output_root) and not args.redo:
        return arxivid, 'Skip'
    output_dir  = os.path.join(output_root, 'uparxive')
    try:
        deal_with_xml_file(file_path, output_dir,args.reterive_result_mode,
        verbose = args.verbose,
        filte_out_note = not args.passNote,
        use_count_type_ref=not args.use_origin_ref_number)
        return arxivid,'Finish'
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
        if args.verbose == 1:traceback.print_exc()
        #logging.info(f"fail ===> {file_path}")
        return arxivid,'Fail'
    
def xml_to_json_one_path_wrapper(args):
    arxiv_path, args = args
    return xml_to_json_one_path(arxiv_path, args)



if __name__ == '__main__':
    import os
    import sys
    from tqdm.auto import tqdm
    import numpy as np
    import traceback
    parser = argparse.ArgumentParser()
    parser.add_argument("--root_path", type=str)
    parser.add_argument("--index_part", type=int, default=0)
    parser.add_argument('--num_parts', type=int, default=1)
    parser.add_argument('--reterive_result_mode', action='store_true', help='', default=False)
    parser.add_argument('--redo', action='store_true', help='', default=False)
    parser.add_argument('--passManyNote','-p', action='store_true', help='', default=False)
    parser.add_argument('--passNote','-n', action='store_true', help='', default=False)
    parser.add_argument('--use_origin_ref_number','-r', action='store_true', help='', default=False)
    
    args = parser.parse_args()
    enable_checkTooManyNote = not args.passManyNote
    verbose = False
    ROOT_PATH = args.root_path# '/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/successed_xml.filelist'
    if os.path.isfile(ROOT_PATH):
        if ROOT_PATH.endswith('.xml'):
            alread_processing_file_list = [ROOT_PATH]
        else:
            with open(ROOT_PATH,'r') as f:
                alread_processing_file_list = [t.strip() for t in f.readlines()]
            
    elif os.path.isdir(ROOT_PATH):
        alread_processing_file_list = os.listdir(ROOT_PATH)
    else:
        raise NotImplementedError
    index_part= args.index_part
    num_parts = args.num_parts 
    reterive_result_mode=args.reterive_result_mode
    totally_paper_num = len(alread_processing_file_list)
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
    alread_processing_file_list = alread_processing_file_list[start_index:end_index]

    analysis = {'MathDontHaveTex':[], 'TooManyNoteError':[], 'CiteDontHaveBibRefError':[], 'MisMatchRefError':[], 'fail':[], 'badxml':[]}
    for file_path in tqdm(alread_processing_file_list):
        file_path = file_path.strip()
        if not os.path.exists(file_path):
            continue
        if os.path.getsize(file_path) < 100:continue

        output_root = os.path.dirname(file_path).replace('_xml','_json')
        if os.path.exists(output_root) and not args.redo:continue
        output_dir  = os.path.join(output_root, 'uparxive')
        try:
            deal_with_xml_file(file_path, output_dir,reterive_result_mode,verbose = verbose,filte_out_note = not args.passNote,use_count_type_ref=not args.use_origin_ref_number)
        except KeyboardInterrupt:
            raise
        except MathDontHaveTex:
            logging.info(f"MathDontHaveTex ===> {file_path}")
            analysis['MathDontHaveTex'].append(file_path)
            continue
        except lxml.etree.XMLSyntaxError:
            logging.info(f"bad xml file ===> {file_path}")
            analysis['badxml'].append(file_path)
            continue
        except TooManyNoteError:
            logging.info(f"too many note ===> {file_path}")
            analysis['TooManyNoteError'].append(file_path)
            #raise
            continue
        except CiteDontHaveBibRefError:
            logging.info(f"cite dont have bibref ===> {file_path}")
            analysis['CiteDontHaveBibRefError'].append(file_path)
            continue
        except MisMatchRefError:
            logging.info(f"mismatch ref ===> {file_path}")
            analysis['MisMatchRefError'].append(file_path)
            continue
        except:
            if totally_paper_num == 1:traceback.print_exc()
            logging.info(f"fail ===> {file_path}")
            continue
    if totally_paper_num == 1:
        logging.info(output_root)

    root_path = '/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/analysis.xml_to_json/convert_status/'
    if num_parts > 1:
        for key, val in analysis.items():
            print(f"{key}=>{len(val)}")
            fold = os.path.join(root_path,f"tex_to_xml.{key.lower()}.filelist.split")
            os.makedirs(fold, exist_ok=True)
            with open(os.path.join(fold,f"{start_index}-{end_index}"), 'w') as f:
                for line in (val):
                    f.write(line+'\n')
    else:
        #print(analysis)
        for key, val in analysis.items():
            print(f"{key}=>{len(val)}")
            # with open(os.path.join(root_path,f"tex_to_xml.{key.lower()}.filelist"), 'w') as f:
            #     for line in set(val):
            #         f.write(line+'\n')
