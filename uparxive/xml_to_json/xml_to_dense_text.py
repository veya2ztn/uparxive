###############
"""
Some known problem:
    - ~~See 0709.2524: The section after \appendix will not be collected into the main content. (The latexml do generate appendix, so we should fix it here)~~

"""
from bs4 import BeautifulSoup, NavigableString
from typing import Dict
from copy import deepcopy
import lxml
import logging
import os
from .check_string_is_citation import *
from .utils import *
from ..batch_run_utils import BatchModeConfig, dataclass
from tqdm.auto import tqdm
from typing import List, Dict,Tuple
from tqdm.contrib.logging import logging_redirect_tqdm

### set the loger in warning mode
log_level = os.environ.get('LOG_LEVEL', 'WARN')
#logging.basicConfig(level=log_level, format='Paper ID: %(paper_id)s - %(message)s')
logging.basicConfig(level=log_level, format='%(message)s')
import traceback
enable_checkCiteDontHaveBibRef = False
enable_checkTooManyNote= True


@dataclass
class XMLtoJsonConfig(BatchModeConfig):
    task_name = 'xml_to_json'
    reterive_result_mode : bool = False
    passManyNote : bool = False
    passNote : bool = False
    use_origin_ref_number : bool = False
    verbose: bool = False
    use_plain_citation:bool = False

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

def remove_and_collect(soup: BeautifulSoup, name):
    if soup is None:return 
    element = soup.find(name)
    if element:
        obj = copy.deepcopy(element)
        element.decompose()
        return obj

def get_latex_from_math(math:BeautifulSoup):
    latex = math.get('tex')
    if not latex:
        logging.warning(f"it seem we find a nothing math at \n {math}")
    return better_latex_math_code(latex)

def is_inline_math(tag):
    return tag.name.lower() == 'math' and tag.get('mode')=='inline'

def revert_all_the_inline_math_to_latex(soup:BeautifulSoup):
    for math in soup.find_all(is_inline_math):
        math.replace_with(f" ${get_latex_from_math(math)}$ ")

def revert_all_the_math_to_latex(soup:BeautifulSoup):
    for math in soup.find_all('Math'):
        math.replace_with(f" ${get_latex_from_math(math)}$ ")


def discard_text_format_in_sentense(soup: BeautifulSoup, cleanmode=False):
    text_flag_pool = set(['text','emph'])
    def is_italic(tag):
        return tag.name in text_flag_pool and tag.get('font')=="italic"
    for italic_text in soup.find_all(is_italic):
        if cleanmode:
            italic_text.replace_with(f"{better_latex_sentense_string(italic_text.text.strip('*'))}")
        else:
            italic_text.replace_with(f"*{better_latex_sentense_string(italic_text.text.strip('*'))}*")
    def is_bold(tag):
        return tag.name in text_flag_pool and tag.get('font')=="bold"
    for bold_text in soup.find_all(is_bold):
        if cleanmode:
            bold_text.replace_with(f"{better_latex_sentense_string(bold_text.text.strip('*'))}")
        else:
            bold_text.replace_with(f"**{better_latex_sentense_string(bold_text.text.strip('*'))}**")
    
    for text in soup.find_all('text','emph'):
        if 'fontsize' not in text.attrs:
            pass
            #logging.warning(f"it seem we find a none register special txt like \n {text.prettify()}")
        text.replace_with(*text.contents)

def get_label_of_the_element(soup: BeautifulSoup):
    return soup.get('key') or soup.get('labels') or soup.get('xml:id')

def get_id_else_to_its_parent(soup: BeautifulSoup, max_depth=5,return_father= False):
    parent = soup
    deepath=0
    while parent is not None and get_label_of_the_element(parent) is None:
        parent = parent.parent
        deepath+=1
        if deepath>max_depth:break
    if return_father:
        return get_label_of_the_element(parent), parent
    else:
        return get_label_of_the_element(parent)

def obtain_tag_of_one_element(soup: BeautifulSoup):
    tags        = soup.find('tags', recursive=False)
    tags_string = get_tag_string_from_tag_and_remove_it(tags)
    if tags_string is None:
        ## we check tag
        tag = soup.find('tag', recursive=False)
        if tag:
            tags_string = tag.text
    return tags_string

def identify_bibblock_is_note_or_citation(bibblock:BeautifulSoup, args)->Tuple[bool,bool]:
    iscitationQ = True 
    hardcitationQ = False

    for ref_in_bib  in bibblock.find_all('ref'):
        if ref_in_bib.get('labelref') and len(bibblock.text.strip())>10: 
            iscitationQ   = False
            hardcitationQ = True
            reason        = 'has_ref'
            return iscitationQ, hardcitationQ, reason
    
        #raise NotImplementedError(f"Lets have a look ==> {bibblock}")
        
    for math_in_bib in bibblock.find_all('math'):
        latex = get_latex_from_math(math_in_bib)
        if count_activate_latex_character(latex)>15:
            logging.warning(latex + " is regard as note")
            iscitationQ = False
            hardcitationQ = True
            reason = 'has_long_math'
            return iscitationQ, hardcitationQ, reason
        #raise NotImplementedError(f"Lets have a look ==> {bibblock}")
    
    return iscitationQ, hardcitationQ, None
                   

def get_tag_string_from_tag_and_remove_it(tags:BeautifulSoup):
    """
    A typical tag is like
        <tags>
            <tag>
                2
            </tag>
            <tag role="autoref">
                footnote 2
            </tag>
            <tag role="refnum">
                2
            </tag>
            <tag role="typerefnum">
                footnote 2
            </tag>
        </tags>
    we extract the tag string a.k.a the label via order typerefnum -> refnum -> autoref
    """
    if tags is None:return None
    order   = {'typerefnum':9, 'refnum':8, 'autoref': 7, 'number':6, 'refnum':5, 'key':0}
    alltags = [[order.get(tag.get('role',''), 3),tag] for tag in tags.find_all('tag')]
    if len(alltags) ==0:
        string = None
    alltags.sort(key=lambda x:x[0])
    string = alltags[0][1].text
    tags.decompose()
    return string

def discard_note(soup: BeautifulSoup,filte_out_note:bool):
    note_ref_metadata = {}
    note_ref_labels   = {}
    for note_id, note in enumerate(soup.find_all('note')):
        #print(note)
        tags       = note.find('tags', recursive=False)
        count_label=f"Note_{note_id}"
        tag_label  = get_label_of_the_element(note) or count_label
        tag_ref_o  = get_tag_string_from_tag_and_remove_it(tags)
        tag_ref    = tag_ref_o or count_label
        note_ref_labels[tag_label]  =tag_ref
        note_ref_metadata[tag_label]=[True, deepcopy(note)]
        
        if filte_out_note and tag_ref_o is None:
            note_contents = note.contents
            note_contents = ["(See "]+note_contents +[")"]
            # Replace the <note> tag with its contents
            note.replace_with(*note_contents)
        else:
            note.decompose()
    return note_ref_labels,note_ref_metadata

def retrieve_all_cite(soup:BeautifulSoup):
    """
    Retrieve all the citation in the soup
        - Type 1: bib ==> <a class="ltx_ref" href="#bib.bib1" title="">1</a>
        - Type 2: fig ==> <a class="ltx_ref" href="#S2.F2" title="Figure 2 ‣ 2 THE QUADRUPOLE TRANSITION TO THE Δ⁢(1232) ‣ Probing the Structure of Nucleons in the Resonance region with CLAS at Jefferson Lab"><span class="ltx_text ltx_ref_tag">2</span></a>,
        - Type 3: tab ==> [TODO]: please give a check
        - Type 3: math==> [TODO]: please give a check
    """
    ref_count = {}
    for bibref in soup.find_all('bibref'):
        assert bibref is not None, f"""this cite:\n {bibref.prettify()}\n wont have bibref????, we will skip it """
        bibrefs_text = bibref.get('bibrefs')
        if bibrefs_text:
            ref_keys = bibrefs_text.strip().split(',')
            for ref in ref_keys:
                ref = ref.strip()
                if ref not in ref_count:ref_count[ref]=0
                ref_count[ref]+=1
        else:
            logging.info(f"this cite:\n{bibref.prettify()} \n wont have bibref????, we will remove it ")
            bibref.decompose()
            continue
    for singleref in soup.find_all('ref'):
        assert singleref is not None, f"""this cite:\n {singleref.prettify()}\n wont have bibref????, we will skip it """
        singleref_text = singleref.get('labelref')
        if singleref_text:
            ref_keys = singleref_text.strip().split(',')
            for ref in ref_keys:
                ref = ref.strip()
                if ref not in ref_count:ref_count[ref]=0
                ref_count[ref]+=1
        else:
            logging.info(f"this cite:\n{singleref.prettify()} \n wont have bibref????, we will remove it ")
            #singleref.decompose()
            continue
    return ref_count


def parse_bibitem(bibitem: BeautifulSoup, 
                  bibindex:int, 
                  note_ref_labels:Dict[str, str], 
                  note_ref_metadata:Dict[str, str], 
                  bibitem_ref_labels:Dict[str, str], 
                  bibitem_ref_metadata:Dict[str, str], 
                  refcount: Dict[str, int],
                  args):
    """
        <bibitem key="Fu2008" xml:id="bib.bib1">
                <tags>
                    <tag role="number">
                        1
                    </tag>
                    <tag role="refnum">
                        (1)
                    </tag>
                    <tag role="key">
                        Fu2008
                    </tag>
                </tags>
                <bibblock> L. Fu and C. Kane, “Superconducting Proximity Effect and Majorana
                    Fermions at the Surface of a Topological Insulator,” <text font="italic">
                    Physical Review Letters
                    </text> , vol. 100, p. 096407, mar 2008. </bibblock>
            </bibitem>
    """

    #### Identify the ref_key and the tag of the bibitem
    filte_out_note = not args.passNote
    verbose        = args.verbose
    tags           = bibitem.find('tags', recursive=False)
    
    if tags is None:
        if len(refcount)>0: logging.warning(f"WARNING: the bibitem {bibitem.prettify()} has no tag")
        return ### 
    tag_count = f"ref_{bibindex}"
    tag_of_bib   = get_tag_string_from_tag_and_remove_it(tags) or tag_count
    label_of_bib = get_label_of_the_element(bibitem) or tag_of_bib
    if not label_of_bib:
        logging.info(f" this bibitem={bibitem} dont have label ???? ")
        return
    if tags is not None:
        # remove the tag now
        tags.decompose()
    
    #### now we will analysis whether the content of the bib is a note or citation
    #print(bibitem)

    bibitem_new = copy.deepcopy(bibitem)
    revert_all_the_inline_math_to_latex(bibitem)
    discard_text_format_in_sentense(bibitem)
    bibblocks = bibitem_new.find_all('bibblock')
    bibstring = better_latex_sentense_string(" ".join([bibblock.text for bibblock in bibblocks]))
    #assert len(bibblocks)==1, f"why this reference string ==> {bibitem} <== has more then one bibblocks ==>{bibblocks}"
    iscitationQ  = True
    hardcitationQ= True
    reason       = None
    if filte_out_note:
        for bibblock in bibblocks:
            iscitationQ, hardcitationQ, reason = identify_bibblock_is_note_or_citation(bibblock,args) #<---the origin bibblock
            if not iscitationQ:break

        if iscitationQ:
            iscitationQ = not should_the_string_be_regard_as_note(bibstring)
            if not iscitationQ:reason = 'content analysis'
            if verbose and not iscitationQ:
                logging.info(f'{bibblocks} is regard as note via [string judge]')
        
    if not iscitationQ:
        ## then, this block is a note, should save whole xml code in this block and put them into main content
        note_ref_labels[label_of_bib]  =  tag_of_bib
        note_ref_metadata[label_of_bib]= [hardcitationQ, deepcopy(bibitem), reason]
    else:
        #refnum_int = int(refnumtext)
        bibitem_ref_labels[label_of_bib]  = tag_of_bib
        bibitem_ref_metadata[label_of_bib]=bibstring

def remove_entire_bibliography_and_build_labels(soup: BeautifulSoup , refcount: Dict[str, int],args):

    bibitem_ref_labels = {}
    bibitem_ref_metadata = {}
    note_ref_labels = {}
    note_ref_metadata={}
    for bio_element in soup.find_all('bibliography'):
        for bio_ul in bio_element.find_all('biblist'):
            for bibindex, bio_li in enumerate(bio_ul.find_all('bibitem')):
                parse_bibitem(bio_li,bibindex,note_ref_labels,note_ref_metadata, bibitem_ref_labels,bibitem_ref_metadata,refcount,args)
            for bibindex, bio_li in enumerate(bio_ul.find_all('bibentry')):
                parse_bibentry(bio_li,bibindex,note_ref_labels,note_ref_metadata, bibitem_ref_labels,bibitem_ref_metadata,refcount,args)
        bio_element.decompose()
    return soup, bibitem_ref_labels, bibitem_ref_metadata, note_ref_labels, note_ref_metadata

def put_note_string_back_into_each_sentence(soup: BeautifulSoup, 
                                            ref_count: Dict[str, int], 
                                            note_ref_metadata: Dict[str, Tuple[bool, BeautifulSoup]],
                                            always_put_back_note=False):
    """
    When put note back into the main content, we always think the <ref> must be in <cite>
    """
    put_back_keys  = set()
    for cite in soup.find_all('cite'):
        all_refs_of_one_cite = cite.find_all('ref')
        put_ref_backQ = False
        for bibref in all_refs_of_one_cite:
            ref = bibref.get('bibrefs', "").strip().split()
            put_ref_backQ = False
            
            if ref in note_ref_metadata:
                put_ref_backQ = True
                hardcitationQ, bibblock, reason = note_ref_metadata[ref]
                if ref_count[ref]>2 and (not hardcitationQ) and not always_put_back_note:
                    logging.info(f"key {ref} skip, dual to many counts and its not a hardcitation")
                    continue # only when it is not type math and ref > 1 case, we dont insect note into contextf    
                #assert len(texts) == 1, f"Only single citation replacement is supported per cite element.{ref} appear more than once"
                put_back_keys = put_back_keys|set([ref])
                logging.warning(f"put back {ref} due to {reason}")
                cite.insert_before(extract_bibblock_html_soup(copy.deepcopy(bibblock)))
                bibref.decompose()
        if put_ref_backQ and len(cite.find_all('bibref'))==0:
            cite.decompose()     
    return put_back_keys

def figure_to_markdown(figure: BeautifulSoup):
    markdown_input = []
    for graphic in figure.find_all('graphics'):
        source = graphic.get('graphic')
        sourceid=get_label_of_the_element(graphic) or 'Figure'
        if source:
            markdown_input.append(f"![{sourceid}]({source})")
    markdown_input  = "\n".join(markdown_input)
    return markdown_input

def remove_figures_record_the_labels(soup: BeautifulSoup):
    """
        A figure example looks like
        <figure inlist="lof" labels="LABEL:Fig1" placement="htpb" xml:id="S1.F1">
            <tags>
                <tag> Figure 1 </tag>
                <tag role="autoref"> Figure 1 </tag>
                <tag role="refnum">  1 </tag>
                <tag role="typerefnum"> Figure 1 </tag>
            </tags>
            <graphics class="ltx_centering" graphic="Fig1.pdf" options="width=369.88582pt,keepaspectratio=true" xml:id="S1.F1.g1" />
            <toccaption class="ltx_centering">
                <tag close=" ">1</tag> 
                Electronic structure of pristine Cr ${}_{0.15}$ (Bi ${}_{0.1}$ Sb${}_{0.9}$ ) ${}_{1.85}$ Te ${}_{3}$ . (a) Fermi surface. (b) Electronic dispersions alongthe $\bar{M}-\bar{\Gamma}-\bar{M}$ momentum line. (c) Electronic dispersions along the$\bar{K}-\bar{\Gamma}-\bar{K}$ momentum line. (d) Fermi surface on a large momentum scale.The dotted hexagon represents the first surface Brillouin zone (SBZ). All the spectra aretaken at 70 eV photon energy at 12 K. </toccaption>
            <caption class="ltx_centering">
                <tag close=": ">Figure 1</tag> 
                Electronic structure of pristine Cr ${}_{0.15}$ (Bi ${}_{0.1}$ Sb${}_{0.9}$ ) ${}_{1.85}$ Te ${}_{3}$ . (a) Fermi surface. (b) Electronic dispersions alongthe $\bar{M}-\bar{\Gamma}-\bar{M}$ momentum line. (c) Electronic dispersions along the$\bar{K}-\bar{\Gamma}-\bar{K}$ momentum line. (d) Fermi surface on a large momentum scale.The dotted hexagon represents the first surface Brillouin zone (SBZ). All the spectra aretaken at 70 eV photon energy at 12 K. </caption>
        </figure>
    """

    ### firstly, we located the deepest <figure> tag that contain the <figcaption>
    ### then, we will collect the tag (which will used in cite) and remove the whole figures 
    ## find whole the figures that has nest caption
    primary_labels = {}
    primary_metadata = {}
    primary_source   = {}
    figure  = soup.find('figure')
    counter = LoopCounter(len(soup.find_all('figure'))+10)
    while counter.increment() and  figure is not None:
        #print("="*20+"\n"+figure.prettify()+"\n"+"="*20)
        captions   = figure.find_all('caption') 
        count_label = f"Figure_{len(primary_labels)}"
        tag_label   = get_label_of_the_element(figure) or count_label
        tag_ref     = obtain_tag_of_one_element(figure) or count_label
        if len(captions) == 0: ### no caption, lets just check the tags
            primary_labels[tag_label] = tag_ref
            primary_metadata[tag_label] = figure.text
            
        elif len(captions) == 1:
            primary_labels[tag_label] = tag_ref
            primary_metadata[tag_label] = copy.deepcopy(captions[0])
            
        else:# len(captions) > 1:
            for caption in captions:
                count_label = f"Figure_{len(primary_labels)}" 
                tag_label   = get_id_else_to_its_parent(caption) or count_label
                tag_ref     = obtain_tag_of_one_element(figure) or count_label ### <--- usually there only has one tag under a caption.
                primary_labels[tag_label] = tag_ref
                primary_metadata[tag_label] = copy.deepcopy(caption)
        ### ------------------- next, we collect the resource collect from this image
        markdown_input = figure_to_markdown(figure)
        primary_source[tag_label] = markdown_input
        markdown_element = BeautifulSoup(f"<para><p>\n<--Figure:{tag_label}-->\n<\p><\para>",features='xml')
        #print(markdown_input)
        figure.replace_with(markdown_element)
        figure  = soup.find('figure')
    return primary_labels, primary_metadata,primary_source

def tabular_into_markdown(soup:BeautifulSoup):
    def is_regard_as_table(tag):
        return tag.name in set(['table', 'tbody', 'tabular'])
    revert_all_the_math_to_latex(soup)
    tables = soup.find_all(is_regard_as_table)
    tables.reverse()
    markdown_outputs = []
    for table in tables:

        rows = table.find_all('tr')
        markdown_table = []
    
        # Process each row
        for row in rows:
            cells = row.find_all('td')
            if not cells:
                continue
            # Extract text from each cell
            extracted_cells = [cell.get_text(strip=True) for cell in cells]
            markdown_table.append(extracted_cells)

        # Build the Markdown table
        markdown_output = ""
        headers = markdown_table[0]
        alignment_row = ["---"] * len(headers)
        
        # Create the header row
        header_row = "| " + " | ".join(headers) + " |"
        markdown_output += header_row + "\n"
        
        # Create the alignment row
        alignment_row = "| " + " | ".join(alignment_row) + " |"
        markdown_output += alignment_row + "\n"
        
        # Add the rest of the data rows
        for data_row in markdown_table[1:]:
            row = "| " + " | ".join(data_row) + " |"
            markdown_output += row + "\n"    
        markdown_outputs.append(markdown_output)
    return markdown_output

def remove_tables_record_the_labels(soup: BeautifulSoup):
    """
        A table example looks like
        <table inlist="lot" labels="LABEL:tab:plain_vs_shortcut" placement="t" xml:id="S4.T2">
            <tags> 
                <tag> Table 2 </tag>
                <tag role="autoref"> Table 2 </tag>
                <tag role="refnum"> 2 </tag>
                <tag role="typerefnum"> Table 2 </tag>
            </tags>
            <tabular class="ltx_centering ltx_guessed_headers" colsep="8.0pt" rowsep="0.9pt" vattach="middle">
                <thead>
                    <tr>
                        <td border="r t" thead="column"/>
                        <td align="justify" border="r t" thead="column" vattach="top">
                            <inline-block vattach="top"> <p width="42.0pt"> plain </p> </inline-block>
                        </td>
                        <td align="center" border="t" thead="column">
                            ResNet
                        </td>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td align="left" border="r t"> 18 layers </td>
                        <td align="justify" border="r t" vattach="top">
                            <inline-block vattach="top">
                                <p width="42.0pt">
                                27.94
                                </p>
                            </inline-block>
                        </td>
                        <td align="center" border="t"> 27.88 </td>
                    </tr>
                    <tr>
                        <td align="left" border="b r"> 34 layers </td>
                        <td align="justify" border="b r" vattach="top">
                            <inline-block vattach="top">
                                <p width="42.0pt">
                                28.54
                                </p>
                            </inline-block>
                        </td>
                        <td align="center" border="b"> **25.03** </td>
                    </tr>
                </tbody>
            </tabular>
            <toccaption>
                <tag close=" "> 2 </tag>
                Top-1 error (%, 10-crop testing) on ImageNet validation. Here the ResNets have no extra parameter compared to their plain counterparts. Fig. <ref labelref="LABEL:fig:imagenet"/> shows the training procedures.
            </toccaption>
            <caption> 
                <tag close=": "> Table 2 </tag> Top-1 error (%, 10-crop testing) on ImageNet validation. Here the ResNets have no extra parameter compared to their plain counterparts. Fig.<ref labelref="LABEL:fig:imagenet"/> shows the training procedures.
            </caption>
        </table>
    """

    ### firstly, we located the deepest <table> tag that contain the <figcaption>
    ### then, we will collect the tag (which will used in cite) and remove the whole figures 
    ## find whole the figures that has nest caption
    primary_labels = {}
    primary_metadata = {}
    primary_source   = {}
    table  = soup.find('table')
    counter = LoopCounter(len(soup.find_all('table'))+10)
    while counter.increment() and  table is not None:
        #print("="*20+"\n"+table.prettify()+"\n"+"="*20)
        captions   = table.find_all('caption') 
        count_label = f"Figure_{len(primary_labels)}"
        tag_label   = get_label_of_the_element(table) or count_label
        tag_ref     = obtain_tag_of_one_element(table) or count_label
        if len(captions) == 0: ### no caption, lets just check the tags
            primary_labels[tag_label] = tag_ref
            primary_metadata[tag_label] = table.text
            
        elif len(captions) == 1:
            primary_labels[tag_label] = tag_ref
            primary_metadata[tag_label] = copy.deepcopy(captions[0])
            
        else:# len(captions) > 1:
            for caption in captions:
                count_label = f"Table_{len(primary_labels)}" 
                tag_label   = get_id_else_to_its_parent(caption) or count_label
                tag_ref     = obtain_tag_of_one_element(table) or count_label ### <--- usually there only has one tag under a caption.
                primary_labels[tag_label] = tag_ref
                primary_metadata[tag_label] = copy.deepcopy(caption)
        ### ------------------- next, we collect the resource collect from this image
        
        markdown_input  = tabular_into_markdown(table)
        primary_source[tag_label] = markdown_input
        markdown_element= BeautifulSoup(f"<para><p>\n<--Table:{tag_label}-->\n<\p><\para>",features='xml')
        table.replace_with(markdown_element)
        table  = soup.find('table')
    return primary_labels, primary_metadata,primary_source
    

def remove_floats_record_the_labels(soup: BeautifulSoup):
    ### firstly, we located the deepest <float> tag that contain the <figcaption>
    ### then, we will collect the tag (which will used in cite) and remove the whole figures 
    ## find whole the figures that has nest caption
    primary_labels = {}
    primary_metadata = {}

    float  = soup.find('float')
    counter = LoopCounter(len(soup.find_all('float'))+10)
    while counter.increment() and  float is not None:
        raise NotImplementedError
        #print("="*20+"\n"+float.prettify()+"\n"+"="*20)
        captions   = float.find_all('caption') 
        count_label = f"Figure_{len(primary_labels)}"
        tag_label   = float.get('xml:id',count_label)
        tag_ref     = obtain_tag_of_one_element(float) or count_label
        if len(captions) == 0: ### no caption, lets just check the tags
            primary_labels[tag_label] = tag_ref
            primary_metadata[tag_label] = float.text
            
        elif len(captions) == 1:
            primary_labels[tag_label] = tag_ref
            primary_metadata[tag_label] = copy.deepcopy(captions[0])
            
        else:# len(captions) > 1:
            for caption in captions:
                count_label = f"Table_{len(primary_labels)}" 
                tag_label   = get_id_else_to_its_parent(caption) or count_label
                tag_ref     = obtain_tag_of_one_element(float) or count_label ### <--- usually there only has one tag under a caption.
                primary_labels[tag_label] = tag_ref
                primary_metadata[tag_label] = copy.deepcopy(caption)
        ### ------------------- next, we collect the resource collect from this image
        
        # markdown_input = []
        # for graphic in float.find_all('graphics'):
        #     source = graphic.get('graphic')
        #     sourceid=graphic.get('xml:id','float')
        #     if source:
        #         markdown_input.append(f"![{sourceid}]({source})")
        #markdown_input  = "\n".join(markdown_input)
        markdown_input = "===> Here is a float. <==="
        markdown_element= BeautifulSoup(f"<p>\n{markdown_input}\n<p>",features='xml')
        float.replace_with(markdown_element)
        float  = soup.find('float')
    return primary_labels, primary_metadata

def revert_the_block_equation_into_latex(soup,primary_labels,replace_mode=False):
    equations         = soup.find_all('equation')
    equation_all_lines= ""
    
    if len(equations) > 0: 
        equation_all_lines = []
        for equation in equations:
            equation_this_line = revert_single_equation_into_latex(equation, primary_labels,replace_mode=replace_mode)
            equation_all_lines.append(equation_this_line.strip().strip("$").strip())
        equation_all_lines = " \\\\ \n".join(equation_all_lines)
        equation_all_lines = f"\n$$\n{equation_all_lines.strip()}\n$$\n"
    return equation_all_lines

def revert_the_block_equationgroup_into_latex(soup:BeautifulSoup):
    """
       See 0505/astro-ph0505533
           1305/1305.6106
        
        One equationgroup may have many equation/equationgroup
    """
    primary_labels = {}
    equationgroups = soup.find_all('equationgroup')
    equationgroups.reverse()
    for equationgroup in equationgroups:
        count_label = f"Equ_{len(primary_labels)}"
        tag_label   = get_label_of_the_element(equationgroup) or count_label
        tag_ref     = obtain_tag_of_one_element(equationgroup) or count_label
        primary_labels[tag_label] = tag_ref
        mathlatex = revert_the_block_equation_into_latex(equationgroup,primary_labels)
        newtag  = BeautifulSoup(f"<equation><directlymath> {mathlatex} </directlymath></equation>",features='xml')
        equationgroup.replace_with(newtag)
    return primary_labels

def revert_single_equation_into_latex(equation:BeautifulSoup, primary_labels, replace_mode=False):
    assert equation.find('equation') is None, "equation in equation?"
    directlymath = equation.find('directlymath')
    if directlymath:
        if replace_mode:
            directlymath = BeautifulSoup(f"<para><p>{directlymath.text} </p></para>",features='xml')
            equation.replace_with(directlymath)
            print(directlymath)
        return directlymath.text
    count_label = f"Equ_{len(primary_labels)}"
    tag_label   =  get_label_of_the_element(equation) or count_label
    tag_ref     = obtain_tag_of_one_element(equation) or count_label
    primary_labels[tag_label] = tag_ref
    for MathBranch in equation.find_all('MathBranch'):
        if MathBranch :MathBranch.decompose()
   # MathForks   = equation.find_all('MathFork')
    # if len(MathForks)==0:
    #     ## we find after revert_the_block_equationgroup_into_latex, the equation will also get un excepted converted
    #     ## I dont find why, thus we pass here
    #     equation_text = equation.text.strip()
    #     assert equation_text.startswith("$"), f"what is your equation?? \n{equation}"
    #     equation.replace_with(equation_text)
    #     return equation_text
    # assert len(MathForks)==1, f"check the status that len(MathForks)=={len(MathForks)} case, \n{equation}"
    # mathfork    = MathForks[0]
    whole_math = []
    for math in equation.find_all('Math'):
        #print(math)
        math_latex = f"{get_latex_from_math(math)}" 
        #math.replace_with()
        whole_math.append(math_latex)
    
    whole_math_latex = " ".join(whole_math)
    whole_math_latex = f"\n$$\n{whole_math_latex.strip()}\n$$\n"
    whole_math_latex_element = whole_math_latex
    if replace_mode:
        whole_math_latex_element = BeautifulSoup(f"<para><p>{whole_math_latex} </p></para>",features='xml')
    equation.replace_with(whole_math_latex_element)
    
    return whole_math_latex

def check_no_figure_and_table_left(soup:BeautifulSoup):
    
    extra_figure_label = {}
    extra_figure_metadata = {}
    extra_figure_source = {}
    # paper like 0505/astro-ph0505154.html has double tag like <figure><figure><table>xxxxxxxxx</table></figure></figure>
    for remain_figure in soup.find_all('figure'):
        if remain_figure is None:continue
        if len(remain_figure.text.strip())==0:
            remain_figure.decompose()
        else:
            logging.info(f"There are still figure left, seem a plain table, we store it")
            key = label = f'extra_figure_{len(extra_figure_label)}'
            extra_figure_label[key] = label
            extra_figure_metadata[key]={}
            extra_figure_source[key]= figure_to_markdown(copy.deepcopy(remain_figure))
            markdown_element= BeautifulSoup(f"<para><p>\n<--Figure:{key}-->\n</p></para>",features='xml')
            remain_figure.replace_with(markdown_element)
            #remain_figure.decompose()
            #raise NotImplementedError(f"why there are still figure left, what left now is \n{pretty_view(remain_figure)})")

    extra_table_label   = {}
    extra_table_metadata = {}
    extra_table_source   = {}
    for remain_table in soup.find_all('table'):
        if remain_table is None:continue
        if len(remain_table.text.strip())==0:
            remain_table.decompose()
        elif remain_table.find('tag'):
            revert_all_the_math_to_latex(remain_table)
            raise NotImplementedError(f"why there are still table left, what left now is \n{remain_table}")
        else:
            logging.info(f"There are still table left, seem a plain table, we store it")
            key = label = f'extra_table_{len(extra_table_label)}'
            extra_table_label[key]     = label
            extra_table_metadata[key]  = {}
            extra_table_source[key]    = tabular_into_markdown(copy.deepcopy(remain_table))
            markdown_element= BeautifulSoup(f"<para><p>\n<--Table:{key}-->\n</p></para>",features='xml')
            remain_table.replace_with(markdown_element)
            #remain_table.decompose()
    # paper like quant-ph0003093.html will list the caption information in a table at the end of main content.
    # since it doesnt have any ref in code, we just delete the table directly
    # if len(soup.find_all('table'))>0:
    #     logging.warning(f"there are still table left, we just remove them ======> ")
    #     for table in soup.find_all('table'):
    #         if table:table.decompose()
    #assert len(soup.find_all('table'))==0, "why there are still table left"
    return (extra_figure_label, extra_figure_metadata, extra_figure_source,
            extra_table_label,extra_table_metadata, extra_table_source)

def collect_tags_and_record_all_labels(soup: BeautifulSoup):
    ### please make sure you remove the figure, table, equation 
    otherslabels={}
    for tags in soup.find_all('tags'):
        parent      = tags.find_parent()
        tags_string = get_tag_string_from_tag_and_remove_it(tags)
        tag_label,parent   = get_id_else_to_its_parent(parent,return_father= True)
        label_type  = parent.name.lower().capitalize()
        
        if tag_label:
            if label_type not in otherslabels:otherslabels[label_type]={}
            otherslabels[label_type][tag_label] =tags_string
        if tags:tags.decompose()
    for tag in soup.find_all('tag'):
        parent      = tag.find_parent()
        tags_string = tag.text
        tag_label,parent   = get_id_else_to_its_parent(parent,return_father= True)
        label_type  = parent.name.lower().capitalize()
        
        if tag_label:
            if label_type not in otherslabels:otherslabels[label_type]={}
            otherslabels[label_type][tag_label] =tags_string
        if tag:tag.decompose()
    return otherslabels

def recovery_citation_in_sentense(cite: BeautifulSoup, labels_reference: Dict[str, str], paper_id: str, refs_that_wont_recovery=[],config:XMLtoJsonConfig=None):
    bibref = cite.find('bibref')
    if bibref is None:
        checkCiteDontHaveBibRef(f""" cite of  {cite.prettfy()}  dont have bibref??? """)
        cite.decompose()
        return 
    text = bibref.get('bibrefs')
    refs = [t.strip() for t in text.split(',')]
    refs = [ref for ref in refs if ref not in refs_that_wont_recovery] # if the ref in refs_that_wont_recovery, this mean we directly remove the ref and won't use [See xxxx] formation
    label_list = []
    for ref in refs:
        reflabels = labels_reference[ref]

        if len(reflabels)>1:
            logging.warning(f"multiple label detected: {reflabels}, we will use the first one")
            raise
        ref_type, label = reflabels[0]
        label_list.append(label)
            
    
    label = ",".join(label_list)    
    label = "[" + label.strip('[]()') + "]"
    next_string = cite.next_sibling 
    prev_string = cite.previous_sibling
    
    right       = next_string.strip() if next_string and isinstance(next_string,NavigableString) else ""
    left        = prev_string.strip() if prev_string and isinstance(prev_string,NavigableString) else ""
    left, right = discard_brackets(left,right)
    
    #leftbrace   = "" if left and left.strip()[-1] in ['[','(','{']  else "["
    #rightbrace  = "" if right and right.strip()[0] in [']',')','}'] else "]"
    #label = leftbrace + label + rightbrace
    isactivated = False
    if left:
        left, label, isactivated = go_ahead_and_add_label(left, label, paper_id,config.use_plain_citation)         
    else:
        left = ""
    label = format_the_smart_citation(left, label, right, paper_id, automative_end = isinstance(next_string,NavigableString),use_plain_citation = config.use_plain_citation)         
    # print(f"""{left} |||||| {label} |||||| {right}""")
    # print("==============================")
    if prev_string and isinstance(next_string,NavigableString):prev_string.replace_with(NavigableString(left))
    cite.replace_with(label)
    if next_string and isinstance(prev_string,NavigableString):next_string.replace_with(NavigableString(right))

    #new_tag = BeautifulSoup(f"<span>{label}</span>", 'html.parser').span

def format_ref(ref_type:str, label:str,paper_id:str, config:XMLtoJsonConfig):
    if config.use_plain_citation:
        return label
    if ref_type.lower() in ['url']:
        label = label

    elif ref_type.lower() not in ['equation','formula']:
        label = f" (See [{ref_type}.{label} of {paper_id}]) "
    else:
        label = f"[{ref_type}.{label} of {paper_id}]"
    return label

def recovery_ref_in_sentense(ref: BeautifulSoup, labels_reference: Dict[str, str], paper_id: str,refs_that_wont_recovery=[],config:XMLtoJsonConfig=None):
    labelrefs = ref.get('labelref')
    if not labelrefs:
        if ref.text is None:
            if ref['href']:return ref.decompose() # ref.replace_with(ref.text)
            if ref['idref']:return ref.decompose()
            if len(set(ref.get('class',[]))&set(['ltx_url','ltx_href','ltx_nolink']))>0:return ref.decompose()
            if len(ref.text).strip() == 0: return ref.decompose()
            logging.warning(f"""ref of element dont have ref??? See {ref.prettify()} """ )
            raise 
        else:
            labelref = " ".join(ref.text)
            ref_type = "URL"
            label    = labelref
    else:
        labelrefs = labelrefs.split(',')
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
    
    #ref_type, label = reflabels[0]
    next_string = ref.next_sibling 
    prev_string = ref.previous_sibling
    
    right       = next_string.strip() if next_string and isinstance(next_string,NavigableString) else ""
    left        = prev_string.strip() if prev_string and isinstance(prev_string,NavigableString) else ""
    left, right = discard_brackets(left,right)
    
    isactivated = False
    if left:
        left, label_new, isactivated = go_ahead_and_add_label(left, label, paper_id,config.use_plain_citation)      
    else:
        left = ""
    if not isactivated:
        label = format_ref(ref_type, label,paper_id,config)
    else:
        label = label_new

    if prev_string and isinstance(next_string,NavigableString):prev_string.replace_with(NavigableString(left))
    ref.replace_with(label)
    if next_string and isinstance(prev_string,NavigableString):next_string.replace_with(NavigableString(right))

def recovery_whole_citation_complete(soup: BeautifulSoup,whole_ref_to_labels, paper_id,refs_that_wont_recovery=[],config:XMLtoJsonConfig=None):
    """
        firstly deal with <ref> in <cite>
        then deal with <ref> for figure. math. table, and so on

        ## you must use a counter = LoopCounter()
    while counter.increment() and  loop since the sibling information may changed, try [cond-mat0003294.html]
        ## the for loop will get failed when continues <cite> tag such as 
        <cite class="ltx_cite ltx_citemacro_cite">[<a href="#bib.bib1" title="" class="ltx_ref">1</a>]</cite><cite class="ltx_cite ltx_citemacro_cite">[<a href="#bib.bib2" title="" class="ltx_ref">2</a>]</cite><cite class="ltx_cite ltx_citemacro_cite">[<a href="#bib.bib3" title="" class="ltx_ref">3</a>]</cite>.
    """
    cites = soup.find_all('cite')
    cites.reverse()
    for cite in cites:
        recovery_citation_in_sentense(cite, whole_ref_to_labels, paper_id,refs_that_wont_recovery=refs_that_wont_recovery, config = config)

    refs = soup.find_all('ref')
    refs.reverse()
    for ref in refs:
        recovery_ref_in_sentense(ref, whole_ref_to_labels, paper_id,refs_that_wont_recovery=refs_that_wont_recovery, config = config)


def beautify_sentence(soup: BeautifulSoup):
    for p in soup.find_all('p'):
        new_content = []
        for element in p.contents:
            if isinstance(element, NavigableString):
                new_content.append(better_latex_sentense_string(str(element)))
            else:
                new_content.append(str(element))
        p.clear()
        p.append(' '.join(new_content))

def deal_with_itermize(soup):
    for ul in soup.find_all('itemize'):
        raise NotImplementedError
        for li in ul.find_all('li'):
            li.replace_with("- "+f"{better_latex_sentense_string(li.text)}")

def cleanup_html(soup: BeautifulSoup, whole_ref_to_labels,paper_id,refs_that_wont_recovery=[]):
    revert_the_block_equationgroup_into_latex(soup)
    revert_the_block_equation_into_latex(soup,{})
    #recovery_whole_citation_simple(soup)
    recovery_whole_citation_complete(soup,whole_ref_to_labels, paper_id,refs_that_wont_recovery)
    revert_all_the_math_to_latex(soup)
    discard_text_format_in_sentense(soup)
    beautify_sentence(soup)
    deal_with_itermize(soup)
    #beautify_section_title(soup)
    #tree = replace_item_block_with_markdown_format(tree)

def cleanup_reference_string(soup: BeautifulSoup, whole_ref_to_labels,paper_id, refs_that_wont_recovery, config:XMLtoJsonConfig=None):
    for tags in soup.find_all('tags'):
        tags.decompose()
    for tag in soup.find_all('tag'):
        tag.decompose()
    recovery_whole_citation_complete(soup,whole_ref_to_labels, paper_id,refs_that_wont_recovery, config = config)
    revert_all_the_math_to_latex(soup)
    discard_text_format_in_sentense(soup)
    beautify_sentence(soup)
    deal_with_itermize(soup)
    #cleanup_html(soup, whole_ref_to_labels, paper_id, refs_that_wont_recovery = refs_that_wont_recovery)
    string = soup.text.replace("[[[Notice:","").replace("]]]","")
    return better_latex_sentense_string(string)


def collect_specific_section_and_remove(soup, name='appendix'):
    whole_sections = []
    for section in soup.find_all(class_=name):
        whole_sections.append(section_to_json(section))
        section.decompose()
    return whole_sections

def is_content_content(tag):
        tagpool = set(['chapter', 'section', 'subsection', 'subsubsection', 'paragraph', 'para', 'glossary','slide', 'p'])
        return tag.name in tagpool


def collect_sections_to_content(soup):
    """
        Version Beta: 
            Lets just scan the soup level by level, possible top level 
            - <section class='ltx_section'>
            - <section class='ltx_subsection'>
            - <section class='ltx_subsubsection'>
            - <section class="ltx_paragraph">
            - <div class="ltx_para">
            
    """
    section = {'title': None, 'content' : []}
    title = soup.find('title',recurive=False)
    if title: section['title']= better_latex_sentense_string(title.text)
    contetn_section = soup.find(is_content_content)
    counter = LoopCounter(len(soup.find_all(is_content_content))+10)
    while counter.increment() and  contetn_section is not None:
        if contetn_section.name in ['p', 'ul']:
            content_section_text = contetn_section.text
            if content_section_text.strip().startswith("$$"):
                section['content'].append(content_section_text)
            else:
                section['content'].append(better_latex_sentense_string(content_section_text))
        else:
            section['content'].append(collect_sections_to_content(copy.deepcopy(contetn_section)))
        contetn_section.decompose()
        contetn_section = soup.find(is_content_content)
    
    return section


def section_to_json(soup):
    '''
    <h2 class="ltx_title ltx_title_section"> 
        <span class="ltx_tag  ltx_tag_section"> 1 </span> INTRODUCTION 
    </h2>
    <div class="ltx_para" id="S1.p1">
    </div>
    '''
    section = {'title': None, 'paragraph' : []}
    title = soup.find('title')
    if title: section['title']= better_latex_sentense_string(title.text)
    for para in soup.find_all('para'):
        section['paragraph'].append(para_to_json(para))
    return section

def para_to_json(soup):
    sentenses = []
    for p in soup.find_all(['p','ul']):
        sentenses.append(better_latex_sentense_string(p.text))
    return sentenses

def collect_abstract(soup,whole_ref_to_labels, paper_id,refs_that_wont_recovery, config:XMLtoJsonConfig=None):
    if soup is None:return
    revert_the_block_equation_into_latex(soup,{})
    revert_all_the_math_to_latex(soup)
    recovery_whole_citation_complete(soup,whole_ref_to_labels, paper_id,refs_that_wont_recovery,config=config)
    discard_text_format_in_sentense(soup)
    beautify_sentence(soup)
    
    content = []
    for p in soup.find_all('p'):
        content.append(p.text)
    return "\n".join(content)

def collect_author(soup):
    """
    We only take the name 
    <div class="ltx_authors">
        <span class="ltx_creator ltx_role_author">
        <span class="ltx_personname">Chao-Ran Cai </span>
        <span class="ltx_author_notes">
        <span class="ltx_contact ltx_role_affiliation">School of Physics, Northwest University,Xi’an 710127, China</span>
        <span class="ltx_contact ltx_role_affiliation">Shaanxi Key Laboratory for Theoretical Physics Frontiers, Xi’an 710127, China </span></span></span>
        <span class="ltx_author_before"></span><span class="ltx_creator ltx_role_author">
        <span class="ltx_personname">Yuan-Yuan Nie </span><span class="ltx_author_notes">
        <span class="ltx_contact ltx_role_affiliation">School of Physics, Northwest University, Xi’an 710127, China </span></span></span>
        <span class="ltx_author_before"></span><span class="ltx_creator ltx_role_author">
        <span class="ltx_personname">Petter Holme </span><span class="ltx_author_notes">
        <span class="ltx_contact ltx_role_email"><a href="mailto:petter.holme@aalto.fi">petter.holme@aalto.fi</a> </span>
        <span class="ltx_contact ltx_role_affiliation">Department of Computer Science, Aalto University, Espoo, Finland </span>
        <span class="ltx_contact ltx_role_affiliation">Center for Computational Social Science, Kobe University, Kobe, Japan </span></span></span>
    </div>
    """
    if soup is None: return
    revert_all_the_math_to_latex(soup)
    authors = []
    for author_name in soup.find_all(class_='ltx_personname'):
        authors.append(better_latex_sentense_string(author_name.text))
    return authors

def collect_acknowledgements(soup):
    """
    <div class="ltx_acknowledgements">
        <h6 class="ltx_title ltx_title_acknowledgements">Acknowledgements.</h6>
        This work was supported by the Shaanxi Fundamental Science Research Project for Mathematics and
        Physics (Grant No. 22JSQ003). PH was supported by JSPS KAKENHI Grant Number JP 21H04595.
    <div>
    
    """
    if soup is None: return
    ### remove the title
    for title in soup.find_all(class_='ltx_title'):title.decompose()
    revert_all_the_math_to_latex(soup)
    return better_latex_sentense_string(soup.text)

def simple_cleanup_html(soup):
    revert_all_the_math_to_latex(soup)
    discard_text_format_in_sentense(soup)
    beautify_sentence(soup)
    deal_with_itermize(soup)


import logging



class ContextFilter(logging.Filter):
    def __init__(self, paper_id):
        super().__init__()
        self.paper_id = paper_id

    def filter(self, record):
        record.paper_id = self.paper_id
        return True
import json
def deal_with_xml_file(tmp_xml_path, output_dir, args:XMLtoJsonConfig):
    reterive_result_mode  = args.reterive_result_mode
    verbose               = args.verbose
    filte_out_note    = not args.passNote
    use_count_type_ref= not args.use_origin_ref_number
    use_smart_citation= not args.use_plain_citation
    reterive_result_mode = bool(reterive_result_mode)
    _paper_id = os.path.basename(os.path.dirname(tmp_xml_path))
    paper_id = f"ArXiv.{_paper_id}"
    with open(tmp_xml_path,'r',encoding='utf-8', errors='ignore') as f:
        soup_whole = BeautifulSoup(f,'xml')
    soup = soup_whole #.find('article')
    #if not soup: return 'NoArticle'
    ReferenceDir= os.path.join(output_dir, "Reference")
    
    ref_count = retrieve_all_cite(soup)
    discard_text_format_in_sentense(soup)
    footnote_labels, footnote_metadata = discard_note(soup,filte_out_note=False)
    author  = remove_and_collect(soup, 'creator')
    abstract= remove_and_collect(soup, 'abstract')
    acknowledgements= remove_and_collect(soup, 'acknowledgements')
    

    new_soup = deepcopy(soup)
    new_soup,reference_labels,bibitem_ref_metadata,note_ref_labels, note_ref_metadata= remove_entire_bibliography_and_build_labels(new_soup,ref_count, args)
    if len(note_ref_metadata)>5:
        for key,val in note_ref_metadata.items():
            logging.info(f"{key} ==> [ {better_latex_sentense_string(' '.join(val[1].text))} ]")
        checkTooManyNote(f'the note_ref_metadata num={len(note_ref_metadata) } is too much , please check the file {tmp_xml_path}')
        logging.warning('WARNING:Too Many note, we roll back to no note mode')
        args.passNote = True
        soup,reference_labels,bibitem_ref_metadata,note_ref_labels, note_ref_metadata= remove_entire_bibliography_and_build_labels(soup,ref_count,args)
    else:
        soup= new_soup

    note_ref_labels=note_ref_labels|footnote_labels
    note_ref_metadata=note_ref_metadata|footnote_metadata
    reference_labels, reference_labels_not_in_context = divide_the_dict_into_two_part_by_keys(reference_labels, ref_count)
    note_ref_labels, note_ref_labels_not_in_context = divide_the_dict_into_two_part_by_keys(note_ref_labels,ref_count)
    bibitem_ref_metadata, bibitem_ref_metadata_not_in_context = divide_the_dict_into_two_part_by_keys(bibitem_ref_metadata,ref_count)
    note_ref_metadata, note_ref_metadata_not_in_context = divide_the_dict_into_two_part_by_keys(note_ref_metadata,ref_count)


    put_back_keys = put_note_string_back_into_each_sentence(soup,ref_count,note_ref_metadata)
    ## since we put those key back into content, we never need those key anymore and wont save them in the reference.txt
    for key in put_back_keys:
        del note_ref_labels[key]
        del note_ref_metadata[key]
    # notice, after this line, the key in note_ref_metadata and note_ref_labels is different
    
    figures_labels, figures_metadata,figures_source = remove_figures_record_the_labels(soup)
    tables_labels ,  tables_metadata, tables_source = remove_tables_record_the_labels(soup)
    floats_labels, floats_metadata   = remove_floats_record_the_labels(soup)
    equation_labels =revert_the_block_equationgroup_into_latex(soup)
    _=revert_the_block_equation_into_latex(soup,equation_labels,replace_mode=True)

    
    
    in_content_ref_labels = {
        'Figure':figures_labels,
        'Table':tables_labels,
        'Equation':equation_labels,
        'Floats':floats_labels
    }
    labels               = collect_tags_and_record_all_labels(soup)## like section and so one
    (extra_figure_label, extra_figure_metadata, extra_figures_source,
     extra_table_label,extra_table_metadata,extra_table_source) = check_no_figure_and_table_left(soup)
    assert len(set(in_content_ref_labels)&set(labels))==0, f"the remain tag should not include those collect before. \n collect before:{in_content_ref_labels.keys()}\n now:{labels.keys()}"
    figures_labels   =   figures_labels | extra_figure_label
    figures_metadata = figures_metadata | extra_figure_metadata
    figures_source   =   figures_source | extra_figures_source

    tables_labels    = tables_labels    | extra_table_label
    tables_metadata  =  tables_metadata | extra_table_metadata
    tables_source    =  tables_source   | extra_table_source

    all_citation_keys = set(ref_count)
    all_reference_keys= (set(reference_labels)|
                    set(note_ref_labels)|
                    set(figures_labels)|
                    set(tables_labels)|
                    set(equation_labels)|
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
        string = cleanup_reference_string(remain_val[1], whole_ref_to_labels,paper_id, refs_that_wont_recovery=put_back_keys,config=args)
        bibitem_ref_metadata[remain_key]=better_latex_sentense_string(string)

    
    whole_ref_to_labels = collect_whole_reference(in_content_ref_labels|
                                                  {'Reference':reference_labels,'Missing':missing_citation_labels}|
                                                  labels, 
                                                  use_count_type_ref=use_count_type_ref)

    #cleanup_html(soup, whole_ref_to_labels,paper_id,refs_that_wont_recovery=[])
    recovery_whole_citation_complete(soup,whole_ref_to_labels, paper_id,refs_that_wont_recovery=[],config=args)
    revert_all_the_math_to_latex(soup)
    discard_text_format_in_sentense(soup)
    beautify_sentence(soup)
    deal_with_itermize(soup)

    for remain_key, remain_val in note_ref_metadata_not_in_context.items():
            string = cleanup_reference_string(remain_val[1], whole_ref_to_labels,paper_id, refs_that_wont_recovery=put_back_keys,config=args)
            note_ref_metadata_not_in_context[remain_key]=better_latex_sentense_string(string)
            ## do this again since we modify the bibitem_ref_metadata
    
    for metadatapool in [figures_metadata, tables_metadata, floats_metadata]:
        for remain_key, remain_val in metadatapool.items():
            string = cleanup_reference_string(remain_val, whole_ref_to_labels,paper_id, refs_that_wont_recovery=put_back_keys,config=args)
            metadatapool[remain_key]=better_latex_sentense_string(string)

    
    whole_metadata = {'figures_metadata':figures_metadata,
                      'tables_metadata':tables_metadata,
                      'floats_metadata':floats_metadata,
                      'tables_source':tables_source,
                      'figures_source':figures_source,
                      'bibitem_ref_metadata':bibitem_ref_metadata,}
        
    content_soup = copy.deepcopy(soup)
    appendix_content = collect_specific_section_and_remove(content_soup,name=['appendix','part'])
    index_content    =  collect_specific_section_and_remove(content_soup,name='index')
    sections_content = collect_sections_to_content(content_soup)
    assert len(content_soup.find_all('section')) ==0, f"why the html wont have ltx section but have another section type, please check"
    output_dict = {'abstract':collect_abstract(abstract, whole_ref_to_labels,paper_id, refs_that_wont_recovery=put_back_keys,config=args),
                   'acknowledge':collect_acknowledgements(acknowledgements),
                   'author': collect_author(author),
                   'appendix':appendix_content,
                   'sections':sections_content,
                   'index':index_content,
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
    return 'Finish'

def xml_to_json_one_path(file_path, args:XMLtoJsonConfig)->Tuple[str,str]:
    file_path = file_path.strip()
    arxivid   = os.path.basename(file_path.replace('.html',''))
    arxivid_parent = os.path.basename(os.path.dirname(file_path))
    if not os.path.exists(file_path):
        return file_path, 'NoHTML'
    if args.savepath:
        output_root = os.path.join(args.savepath,arxivid_parent,arxivid)
    else:
        output_root = os.path.dirname(file_path)
    
    
    output_dir  = os.path.join(output_root, 'upar5iv')
    target_file = os.path.join(output_dir, arxivid+'.json')
    if os.path.exists(target_file) and not args.redo:
        return arxivid, 'Skip'
    try:
        code = deal_with_xml_file(file_path, output_dir, args)
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
    
def xml_to_json_one_path_wrapper(args):
    arxiv_path, args = args
    
    return xml_to_json_one_path(arxiv_path, args)