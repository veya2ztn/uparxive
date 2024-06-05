from nougat.dataset.parser.html2md import format_document,htmlmin
from .nougat_parser_with_color import parse_latexml,get_color_from_style
from nougat.dataset.utils import unicode_to_latex
import fitz, math,re,json, os,difflib
from collections import OrderedDict
from .utils import *
import logging
from pathlib import Path
from bs4 import BeautifulSoup
from ..batch_run_utils import BatchModeConfig, dataclass
import logging
def set_log_level(log_level):
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % log_level)
    logging.basicConfig(level=numeric_level)

# Set the log level to 'DEBUG'
set_log_level('ERROR')
from TexSoup.utils import Token
from TexSoup.data import BraceGroup,TexCmd

@dataclass
class MarkdownPDFalignedConfig(BatchModeConfig):
    verbose : bool = False
    redo : bool = False
    task_name = 'md_pdf_aligned'
    debug  : bool = False
def discard_color_block(html):
    def is_colored_part(tag):
        return tag.name == 'span' and tag.get('style') 
    spans = html.find_all(is_colored_part)
    spans.reverse()
    for span in spans:
        color  = get_color_from_style(span.get('style'))
        if color:
            span.replace_with(' ['+color+']'+span.text.lstrip()+'  ')
    return html

def better_latex_math_code(latex_strings):
    normalized_strings = []
    for latex_string in latex_strings.split('\n'):
        latex_string = latex_string.replace("\displaystyle","")
        latex_string = latex_string.replace("\%", "<escaped_percent>")
        # # Remove all comments
        latex_string = re.sub(r"%\n", "", latex_string)
        latex_string = re.sub(r"%.*", "", latex_string)
        # # Restore escaped percents
        latex_string = latex_string.replace("<escaped_percent>", "\%")
        pattern = r"(?<!\\)%.*?\n"
        # Substitute each match with a newline character
        normalized_string = re.sub(pattern, '\n', latex_string)
        # Remove all newline characters
        normalized_string = normalized_string.replace('\n', ' ')
        # Remove multiple whitespace characters
        normalized_string = re.sub(r'\s+', ' ', normalized_string)
        # Remove the additional space we added at the start if it's still there
        normalized_string = normalized_string.strip()
        normalized_strings.append(normalized_string)
    normalized_strings = " ".join(normalized_strings)
    return normalized_strings

def read_and_standardlize_html(html_path): #"/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/archive_tex/1912/1912.02670/temp/colorful.html"
    html = BeautifulSoup(
        htmlmin.minify(
            open(html_path, "r", encoding="utf-8").read().replace("\xa0", " "),
            remove_all_empty_space=1,
        ),
        features="html.parser",
    )

    # for note in html.find_all("span", class_='ltx_note'):
    #     for sup in note.find_all('sup'):
    #         sup.insert(0, "[000000]")
        
    #     ltx_note_content = note.find(class_='ltx_note_content')
    #     if ltx_note_content:
    #         ltx_tag = ltx_note_content.find(class_='ltx_tag')
    #         ltx_tag.decompse()
    #         ltx_note_content.insert(0, '\n|footnote_start|\n')
    #         ltx_note_content.append('\n|footnote_end|\n')
    #     else:
    #         ltx_tag = note.find(class_='ltx_tag')
    #         ltx_tag.decompse()
    #         note.insert(0, '\n|footnote_start|')
    #         note.append('\n|footnote_end|')
        
    
    
    def is_colored_float_part(tag):
        return tag.name == 'span' and "ltx_framed_rectangle" in tag.get('class',[]) and tag.get('style')
    spans = html.find_all(is_colored_float_part)
    spans.reverse()
    for span in spans:
        colorconfig = span.get('style').split(';')
        colorconfig = [t for t in colorconfig if 'background-color' in t]
        color = colorconfig[0]
        assert len(colorconfig)==1
        new_content = ' ['+color.replace('background-color:#',"").rstrip(';')+']'+ "FLOATSELEMENT" +'  '
        span.replace_with(BeautifulSoup(f"""<figcaption> |floats_start| {new_content} |floats_end| </figcaption>""",'html.parser').figcaption)

    def is_colored_part(tag):
        return tag.name == 'span' and tag.get('style') 

    # spans = html.find_all(is_colored_part)
    # spans.reverse()
    # for span in spans:
    #     color  = get_color_from_style(span.get('style'))
    #     if color:
    #         span.replace_with(' ['+color+']'+span.text.lstrip()+'  ')
        


    captions = html.find_all(class_='ltx_caption')
    captions.reverse()
    for caption in captions:
        caption = discard_color_block(caption)
        caption.replace_with(BeautifulSoup(f"""<figcaption> |caption_start| {caption.text} |caption_end| </figcaption>""",'html.parser').figcaption)

    floats = html.find_all(['figure','table','floats'])
    floats.reverse()
    for float_obj in floats:
        whole_figcaptions = float_obj.find_all('figcaption')
        if len(whole_figcaptions)==0:
            #print(float_obj)
            continue
        contents = []
        for i,t in enumerate(whole_figcaptions):
            contents.append(t.text)
        contents = "\n".join(contents)
        whole_figcaptions[0].replace_with(BeautifulSoup(f"""<figcaption> |fig_caption_start| {contents} |fig_caption_end| </figcaption>""",'html.parser').figcaption)
        for t in whole_figcaptions[1:]:t.decompose()

    for math in html.find_all('math'):
        if 'alttext' in math.attrs:
            math['alttext'] = better_latex_math_code(math['alttext'])
            
        else:
            math['alttext'] = math.text
        math['class']='ltx_Math'# in some case like 2112.09383, it may use ltx_math_unparse which can not recoginized by nougat
    def is_blocked_math(tag):
        return tag.name == 'math' and tag.find(lambda x:x.get('mathcolor') is not None) is not None and "rgb" not in tag.get('alttext',"") #tag.get('display')=='block'
    
    blocks = html.find_all(is_blocked_math)
    blocks.reverse()
    for block_math in blocks:
        if 'alttext' not in block_math.attrs: 
            block_math['alttext'] = block_math.text ## case like 2102/2102.01680
        the_color = block_math.find(lambda x:x.get('mathcolor') is not None)
        the_color = the_color.get('mathcolor')
        block_math['alttext'] = f"[{the_color.strip('#')}]{block_math['alttext']}"


    return html

def extract_captions(text):
    # Regular expression pattern to match content between |caption_start| and |caption_end|
    pattern      = r'\|fig_caption_start\|(.*?)\|fig_caption_end\|'
    fig_captions = re.findall(pattern, text, re.DOTALL)
    pattern      = r'\|fig_caption_start\|.*?\|fig_caption_end\|'
    text         = re.sub(pattern, "", text, flags=re.DOTALL)
    fig_cap_list = []
    for fig_caption in fig_captions:
        figures = re.findall(r'\|floats_start\|(.*?)\|floats_end\|', fig_caption, re.DOTALL)
        captions= re.findall(r'\|caption_start\|(.*?)\|caption_end\|', fig_caption, re.DOTALL)
        fig_cap_list.append([figures,captions])
    return text,fig_cap_list

def extract_footnote(text):
    # Regular expression pattern to match content between |caption_start| and |caption_end|
    pattern      = r'\|footnote_start\|(.*?)\|footnote_end\|'
    footnote_list= re.findall(pattern, text, re.DOTALL)
    pattern      = r'\|footnote_start\|.*?\|footnote_end\|'
    text         = re.sub(pattern, "", text, flags=re.DOTALL)
    return text,footnote_list

# def extract_captions_new(pool):
#     text = "\n".join([v for v in pool.values()])
#     return extract_captions(text)

def extract_captions_new(pool):
    output = []
    for key, val in pool.items():
        if key.lower().startswith('footnote'):
            output.append([["[000000]FOOTNOTE"],[val]])
        else:
            #print(extract_captions(val))
            output.extend(extract_captions(val)[1])
    output = [t for t in output if t ]
    return None, output

def smart_unicode_to_latex(content):
    new_content = []
    blocks = blockwise_content(content,blocks= [(r'\\\(.*?\\\)', 'equation'),(r'\\\[.*?\\\]', 'equation')])
    for _type, block_content in blocks:
        if _type == 'text':
            new_content.append(unicode_to_latex(block_content))
        elif _type == 'equation':
            new_content.append(block_content)
        else:
            raise NotImplementedError(f"not implement for _type={_type}")
    return " ".join(new_content)

### convert to the markdown text
def soup2mdtext(html):

    doc = parse_latexml(html)

    
    
    mmd, fig = format_document(doc, keep_refs=True)
    #### the latest nougat version will shrink below part in to a single line
    mmd = re.sub(r"\\definecolor(\s*\[.*?\])?\s*\{[^}]*\}\s*\{\s*rgb\s*}\s*\{[^}]*\}", "", mmd)
    fig = {k:smart_unicode_to_latex(v) for k,v in fig.items()}
    #mmd = unicode_to_latex(mmd)
    #mmd = mmd.replace(" '","'")
    
    mmd = mmd.replace('[000000]','')
    # mmd,footnote = extract_footnote(mmd)
    # footnote = [unicode_to_latex(v) for v in footnote]
    #### the latest nougat version will shrink below part in to a single line
    mmd = re.sub(r'\[TABLE.*?\[ENDTABLE\]', "", mmd, flags=re.DOTALL)
    mmd = re.sub(r'\[FIGURE.*?\[ENDFIGURE\]', "", mmd, flags=re.DOTALL)
    mmd = re.sub(r'\[FLOAT.*?\[ENDFLOAT\]', "", mmd, flags=re.DOTALL)
    mmd = re.sub(r'\[FOOTNOTE.*?\[ENDFOOTNOTE\]', "", mmd, flags=re.DOTALL)
    

    
    return mmd, fig


import re

def partition_latex_blocks(latex_input):
    
    pattern = r'\{\\color'
    matches = list(re.finditer(pattern, latex_input))

    blocks = []
    last_index = 0

    for match in matches:
        start = match.start()

        # Add the text between the last block and this block
        if last_index < start:
            blocks.append(latex_input[last_index:start])

        # Initialize the stack and determine the block
        stack = []
        i = start
        while i < len(latex_input):
            if latex_input[i] == '{':
                stack.append('{')
            elif latex_input[i] == '}':
                if stack:
                    stack.pop()
                if not stack:  # If the stack is empty, we found the end of the block
                    blocks.append(latex_input[start:i+1])
                    last_index = i + 1
                    break
            i += 1

    # Add any remaining text after the last match
    if last_index < len(latex_input):
        blocks.append(latex_input[last_index:])

    return blocks

def simple_math_color_format(latex_input):
    # Partition into blocks
    blocks = partition_latex_blocks(latex_input)
    pattern = r'\\color\s*\[\s*rgb\s*\]\{\s*([^}]+?)\s*\}([^}]*)\}'
    # Print the results
    colored_text_tuple = []
    for block in blocks:
        match = re.search(pattern, block)
        if not match:
            color = None
            colored_text_tuple.append((color,block))
        else:
            rgb_string, text = match.groups()
            rgb_values = rgb_string.split(',')
            R, G, B = (round(float(value) * 255) for value in rgb_values)
            colored_text_tuple.append(((R, G, B), text))
    return colored_text_tuple

def blockwise_content(content, blocks):
    # Combine all block patterns into one regex
    combined_pattern = '|'.join(f'({pattern})' for pattern, _ in blocks)
    combined_regex = re.compile(combined_pattern, re.DOTALL)

    # List to store the blocks in order of appearance
    latex_blocks = []

    # Find all matches in the content
    last_index = 0
    for match in combined_regex.finditer(content):
        # Capture the content before the current match
        if match.start() > last_index:
            between_content = content[last_index:match.start()].strip()
            if between_content:
                latex_blocks.append(['text', between_content])

        # Determine which pattern matched
        for i, (pattern, name) in enumerate(blocks):
            if match.group(i + 1):
                latex_blocks.append([name, match.group(i + 1).strip()])
                break

        last_index = match.end()

    # Capture any remaining content after the last match
    if last_index < len(content):
        remaining_content = content[last_index:].strip()
        if remaining_content:
            latex_blocks.append(['text', remaining_content])
    return latex_blocks

#
def color_dct_text(line, color):
    dct_color = OrderedDict()
    # Split the line at each color code and any following non-space characters
    parts = re.split(r'(\[[0-9A-Fa-f]{6}\])', line.strip())
    current_color = color  # Start with the provided default color
    if current_color == (0,0,0):
        current_color= add_rgb(current_color)
    buffer_text = ''
    for i, part in enumerate(parts):
        match = re.match(r'\[([0-9A-Fa-f]{6})\]', part)
        
        if match:
            # Handle the buffer before switching to a new color
            if buffer_text:
                # Adding previous buffered text to the dictionary
                if current_color in dct_color:
                    dct_color[current_color] += buffer_text
                else:
                    dct_color[current_color] = buffer_text
                buffer_text = ''  # Reset the buffer

            # Update current color
            current_color = hex_to_rgb(match.group(1))
        else:
            # Split the non-color-code part at spaces for further processing
            subparts = part.split()
            for j, subpart in enumerate(subparts):
                if j == 0:
                    # The first part stays with the current color
                    buffer_text += subpart + ' '
                else:
                    # Subsequent parts get a new incremented color
                    if buffer_text:
                        # Store the current buffer before changing color
                        if current_color in dct_color:
                            dct_color[current_color] += buffer_text
                        else:
                            dct_color[current_color] = buffer_text
                    current_color = add_rgb(current_color)  # Change to a new color
                    buffer_text = subpart + ' '  # Start new buffer with the subpart
    # Add the last buffer if any
    if buffer_text:
        if current_color in dct_color:
            dct_color[current_color] += buffer_text
        else:
            dct_color[current_color] = buffer_text
    return dct_color

def color_dct_line(line,color,keep_structure):
    dct_color=OrderedDict()
    blocks = blockwise_content(line,blocks= [(r'\\\(.*?\\\)', 'inline_equation') ])
    for _type, block_content in blocks:
        if _type == 'text':
            partition = re.split(r'(\[[0-9A-Fa-f]{6}\][^\s]+|\s)', block_content.strip())
            partition = [t for t in partition if t.strip()]
            for part in partition:

                if not part.strip():continue
                part = unicode_to_latex(part)
                res = re.match(r'\[([0-9A-Fa-f]{6})\](.*)', part)
                if res:
                    hex_code, text = res.groups()
                    color = hex_to_rgb(hex_code)
                    #if color not in dct_color:dct_color[color]=[]
                    if color in dct_color:
                        #print(f"{color} => {text}")
                        if len(text.strip())>0:
                            logging.debug(f"color = {color} ==> part{part}, replicate to {dct_color[color]}")
                    else:
                        #print(f"{i}/{length}=>{text}")
                        dct_color[color] = text 
                else:   

                    # not included：对上一个color进行递增，目的是避免键的重复
                    color = add_rgb(color)
                    #if color not in dct_color:dct_color[color]=[]
                    dct_color[color] = part 
        elif _type == 'inline_equation':
            block_content = block_content.strip()
            dct_color[add_rgb(color)] = ["<inline_math>",block_content[:2]]
            for c,text in simple_math_color_format(block_content[2:-2]):
                if c and c!=(0,0,0):
                    assert c not in dct_color or len(text.strip())==0, f"color should be unique {c}"
                    dct_color[c] = ["<inline_math>",text]
                    color = c
                else:
                    color = add_rgb(color)
                    dct_color[color] = ["<inline_math>",text]
            dct_color[add_rgb(color)] = ["inline_<math>",block_content[-2:]]
        else:
            raise NotImplementedError(f"not implement for _type={_type}")
        
    if keep_structure:
        if isinstance(dct_color[color],str):
            dct_color[color] += "\n\n"
        # inline math does not need do \n\n
    return dct_color

def   colored_dct(mmd,keep_structure=True):
    dct_color = OrderedDict()
    mmd = re.sub(r'\u2062','',mmd)  # 删除多余的不可见Unicode编码
    # for view_symbol, latex_code in dct_greek2math.items(): ### since we have unicode_to_latex, dont need this anymore 
    #     if view_symbol in mmd:
    #         #print(view_symbol,'->',dct_greek2math[view_symbol]) ### markdown 
    #         mmd = mmd.replace(view_symbol,dct_greek2math[view_symbol])
    mmd = re.sub(r'\[RGB\](\d{3}),(\d{3}),(\d{3})',"",mmd) ### <-- filter data like [RGB]111,222,333dadsa
    
    assert len([t for t in re.split(r'(\[[0-9A-Fa-f]{6}\][^\s]+|\s)', mmd) if t.strip()])< 256*256*256
    color = (0,0,0)
    block_equation_color_map = OrderedDict()
    blocks = blockwise_content(mmd,blocks= [(r'\\\[.*?\\\]', 'block_equation') ])
    for _type, block_content in blocks:
        if _type == 'text':
            for line in block_content.splitlines():
                if not line.strip():continue
                line_dct_color = color_dct_line(line,color,keep_structure)
                dct_color = dct_color|line_dct_color
        elif _type == 'block_equation':
            block_content = block_content.strip()
            dct_color[add_rgb(color)] = ["<block_math>",block_content[:2]]
            text = block_content[2:-2]
            matches = re.findall(r'\[([0-9A-Fa-f]{6})\]([^\[]*)', text)
            if matches:
                if len(set([c for c, _ in matches]))!=1:
                    logging.info(f"why a block equation has more than one color as {matches}")
                for color, text in matches:
                    color  = hex_to_rgb(color)
                    dct_color[color] = dct_color.get(color,'') + " " + text
                    block_equation_color_map[color]= block_equation_color_map.get(color,'') + " " + text
                dct_color[color] += '\n'
                block_equation_color_map[color] += '\n'
            else:
                dct_color[add_rgb(color)] = ["<block_math>", text]

            dct_color[add_rgb(color)] = ["<block_math>",block_content[-2:]]
        else:
            raise NotImplementedError(f"not implement for _type={_type}")
    dct_color_cleaned =  OrderedDict()
    for k,v in dct_color.items():
        if isinstance(v,list):
            md_type, md_text = v
        else:
            md_type = '<text>'
            md_text = v
        if len(md_text.strip())==0:continue
        dct_color_cleaned[k]=(md_text, md_type)
    
    return dct_color_cleaned,block_equation_color_map

def get_markdown_text_with_colored(html_path):
    html = read_and_standardlize_html(html_path)
    mmd,fig = soup2mdtext(html)
    _,fig_captions = extract_captions_new(fig)
    mmd_color_dct,block_equation_color_map = colored_dct(mmd)

    color_figid_map   = {}
    cap_color_dct     = {}
    fig_color_dct     = {}
    fig_captions_list = []
    for fig,cap in fig_captions:
        now_cap_color_dct,_ = colored_dct("\n".join(cap),keep_structure=False)    
        now_fig_color_dct,_ = colored_dct("\n".join(fig),keep_structure=False) 
        
        cap_color_dct = cap_color_dct|now_cap_color_dct
        fig_color_dct = fig_color_dct|now_fig_color_dct
        for color in now_cap_color_dct.keys():
            if color != (0,0,0) and color !=0 :
                color_figid_map[color] = len(fig_captions_list)
        for color in now_fig_color_dct.keys():
            if color != (0,0,0) and color !=0 :
                color_figid_map[color] = len(fig_captions_list)
        fig_captions_list.append(
            {'caption':now_cap_color_dct,'figure':now_fig_color_dct}
        )
    return mmd,mmd_color_dct,cap_color_dct,fig_color_dct,fig_captions_list,color_figid_map,block_equation_color_map

def deal_with_color_text_with_break_line(color_to_text_list):

    for color, text_bbox_list in color_to_text_list.items():
        assert color != 0 and color!=(0,0,0)
        text = " ".join([text for text, _ in text_bbox_list])
        bbox = merge_bboxes([bbox for _, bbox in text_bbox_list])
        if bbox is None:
            logging.debug(f"bbox is None for color {color}, usually because this caption has line break ")
            bbox = text_bbox_list[0][1]

        color_to_text_list[color]= (text,bbox)
    return color_to_text_list

#### tier1 match: via color
def get_information_from_this_pdfcolor(pdf_color,sequence2boxed,color_table_seq_pdf):
    """
    it may line break like color-ful, and we consider those
    """
    all_indexes = color_table_seq_pdf[pdf_color]
    pdf_text_list = []
    bbox_list = []
    for pdf_box_index in all_indexes:
        pdf_color, pdf_text, bbox = sequence2boxed[pdf_box_index]
        pdf_text_list.append(pdf_text)
        bbox_list.append(bbox)
    pdf_text = " ".join(pdf_text_list)
    bbox = merge_bboxes(bbox_list)
    return pdf_color, pdf_text, bbox

import numpy as np
from typing import List,Tuple,Dict,Any
def rough_split_by_color_pair(sequence_1:List[Tuple[Tuple[int,int,int],str, Any]], sequence_2:List[Tuple[Tuple[int,int,int],str,Any]], level=0):
    color_position_map_1 = {c: i for i, (c,_,_) in enumerate(sequence_1) if c != (0,0,0) and is_meaningful_markdonw_color(c)}
    color_position_map_2 = {c: i for i, (c,_,_) in enumerate(sequence_2) if c != (0,0,0) and is_meaningful_markdonw_color(c)}
    
    pair = []
    last_record_sequence_2_start = 0
    last_record_sequence_1_start = 0
    sequence_2_index = 0
    sequence_1_index = 0
    color_once_matched = {}
    for sequence_1_index in range(len(sequence_1)):
        color, text_1, _ = sequence_1[sequence_1_index]
        # Skip if color is not found in Markdown color table or is 0 or black
        if color not in color_position_map_2:continue
        
        sequence_2_index = color_position_map_2[color]
        _ , text_2, _ = sequence_2[sequence_2_index]
        if text_2.strip().lower() == text_1.strip().lower():
            if ((last_record_sequence_2_start <= sequence_2_index and last_record_sequence_1_start <= sequence_1_index) and
                not (last_record_sequence_2_start==sequence_2_index and last_record_sequence_1_start==sequence_1_index)): 
                pair.append(["need", last_record_sequence_2_start, sequence_2_index, last_record_sequence_1_start, sequence_1_index])
            last_record_sequence_2_start = sequence_2_index + 1
            last_record_sequence_1_start = sequence_1_index + 1
            pair.append(["aligned" , sequence_2_index, last_record_sequence_2_start, sequence_1_index, last_record_sequence_1_start])
            color_once_matched[color] = (sequence_2_index,sequence_1_index)
    if ((last_record_sequence_2_start <= sequence_2_index and last_record_sequence_1_start <= sequence_1_index) and
    not (last_record_sequence_2_start==sequence_2_index and last_record_sequence_1_start==sequence_1_index)): 
        sequence_2_index = last_record_sequence_2_start + sequence_1_index - last_record_sequence_1_start
        pair.append(["need", last_record_sequence_2_start, sequence_2_index, last_record_sequence_1_start, sequence_1_index])
        
    ### below case may produce extra need match since it cannot handle later match before case 
    ### in such a case, all the before word in sequence 2 will get deleted mark since it wont match at that monoment
    ### lets do a post fix, it may have a more efficient code way
    new_pair = []
    for tag, i1,i2,j1,j2 in pair:
        if tag =='aligned':
            new_pair.append((tag, i1,i2,j1,j2))
        else:
            ### we just pop out those keys that has matched in old case
            i1_start = i1 
            i2 = min(len(sequence_2)-1, i2)
            matched_i = [i1_end for i1_end in range(i1, i2) if sequence_2[i1_end][0] in color_once_matched]
            if len(matched_i) > 0:
                new_pair.append((tag, i1_start,min(matched_i),j1,j2 ))
            else:
                new_pair.append((tag, i1,i2,j1,j2))
    
    return new_pair

#### tier2 match: via text score
def match_score(a, b):
    """ Concatenate list b and compare with string a to determine match score. """
    if a == ''.join(b):

        return len(a)  # Reward longer matches more
    else:
        return 0  # No partial matches allowed for simplicity

def align_sequences(seq1, seq2):
    m, n = len(seq1), len(seq2)
    # Create a DP table with dimensions (m+1) x (n+1)
    dp = [[(0, ())] * (n + 1) for _ in range(m + 1)]
    
    # Initialize gaps
    for i in range(1, m + 1):
        dp[i][0] = (dp[i-1][0][0] - 1, (i-1, 0))  # Gap penalty for seq1
    for j in range(1, n + 1):
        dp[0][j] = (dp[0][j-1][0] - 1, (0, j-1))  # Gap penalty for seq2
    
    # Fill the DP table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            # Check matches for different lengths of sequences from seq2
            max_score = dp[i-1][j][0] - 1  # Gap in seq2
            max_index = (i-1, j)
            for k in range(1, j + 1):
                score = match_score(seq1[i-1], seq2[j-k:j])
                if max_score < dp[i-1][j-k][0] + score:
                    max_score = dp[i-1][j-k][0] + score
                    max_index = (i-1, j-k)
            dp[i][j] = (max_score, max_index)
    
    # Backtrack to find the best alignment
    alignment = []
    i, j = m, n
    while i > 0 or j > 0:
        prev_i, prev_j = dp[i][j][1]
        if prev_i == i-1:
            # seq1[i-1] was aligned with seq2[prev_j:j]
            alignment.append(((i-1,i), [prev_j,j] if prev_j != j else ['-']))
        if prev_j == j:
            # Gap in seq2
            alignment.append(((i-1,i), ['-']))
        i, j = prev_i, prev_j
    
    alignment.reverse()
    return alignment

def get_real_match(sequence1, sequence2):
    """
    Match along sequence1, 
    """
    real_match = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, sequence1, sequence2).get_opcodes():
        if tag == 'replace':
            seq1 = sequence1[i1:i2]
            seq2 = sequence2[j1:j2]
            alignment = align_sequences(seq1, seq2)
            alignment = OrderedDict({a:b for a,b in alignment})
            for (a1,a2), b12 in alignment.items():
                if len(b12)==1:
                    tag = 'delete'
                    b1 = b2 = 0
                else:
                    tag = 'equal'
                    b1,b2 = b12
                i1_now = i1+a1
                i2_now = i1+a2
                j1_now = j1+b1
                j2_now = j1+b2
                real_match.append((tag, i1_now, i2_now,j1_now, j2_now))
                # print('{:7}   seq1[{}:{}] --> {}'.format(tag, i1_now, i2_now, sequence1[i1_now:i2_now]))
                # print('          seq2[{}:{}] --> {}\n'.format(j1_now, j2_now, sequence2[j1_now:j2_now]))
        else:
            i1_now = i1
            i2_now = i2
            j1_now = j1
            j2_now = j2
            if tag == 'equal':
                assert (i2_now - i1_now) == (j2_now - j1_now)
                for i, j in zip(range(i1_now, i2_now),range(j1_now,j2_now)):
                    real_match.append((tag, i, i+1,j, j+1))
            else:
                real_match.append((tag, i1_now, i2_now,j1_now, j2_now))
            # print('{:7}   seq1[{}:{}] --> {}'.format(tag, i1_now, i2_now, sequence1[i1_now:i2_now]))
            # print('          seq2[{}:{}] --> {}\n'.format(j1_now, j2_now, sequence2[j1_now:j2_now]))
    return real_match

############# append fig/tab and there caption #########
def convert_color_1_to_255(rgb):
    """ Convert RGB from 0-255 scale to 0-1 scale. """
    return tuple([round(value*255) for value in rgb])


def find_colored_rectangles(page,colors):
    drawings = page.get_drawings()
    colored_rectangles = []

    for item in drawings:
        
        if item['fill'] and item['fill'][0:3] not in  [(1, 1, 1),(0,0,0)] and convert_color_1_to_255(item['fill'][0:3]) in colors:
            # Check for non-white fill; RGB (1, 1, 1) is white
            colored_rectangles.append(item)
    
    return colored_rectangles

from typing import Tuple
def check_the_bbox_is_out_of_the_region(bbox:Tuple[float, float,float, float], bbox_region:Tuple[float, float,float, float]):
    """ Check if the bounding box is out of the region. """
    x1, y1, x2, y2 = bbox
    x1_region, y1_region, x2_region, y2_region = bbox_region
    return x2 < x1_region or y2 < y1_region or x1 > x2_region or y1 > y2_region

def get_pdf_text_with_colored(page,block_equation_color_map,cap_color_dct,fig_color_dct,color_figid_map,fig_captions_list):
    colored_rectangles = find_colored_rectangles(page,fig_color_dct.keys())
    pdf_draw_color_bbox_map = {}
    for now_draw in colored_rectangles:
        color = convert_color_1_to_255(now_draw['fill'][0:3])
        a,b,c,d  = now_draw['rect']
        pdf_draw_color_bbox_map[color] = (a,b,c,d)
        
    ### lets remove the content in the image box,

    sequence2boxed=[]
    color_to_position = {}
    caption_matched_in_this_page = OrderedDict()
    last_color = ["main_content", (0,0,0)]
    for b in page.get_textpage().extractDICT()['blocks']:
        for l in b['lines']:
            for s in l['spans']:
                s['text']= text =unicode_to_latex(s['text'])
                if len(text.strip())==0:continue
                bbox     = s['bbox']
                s['color'] = color = get_color(s['color'])
                
                in_image_box = False
                for image_color, bbox_region in pdf_draw_color_bbox_map.items():
                    if not check_the_bbox_is_out_of_the_region(bbox, bbox_region):
                        #print(f"bbox for {s['text']} is in the the region of image color = {image_color}")
                        in_image_box = True
                if in_image_box:continue
                if color!=0 and  color != (0,0,0) and color in fig_color_dct:continue
                if color!=0 and  color != (0,0,0) and color in cap_color_dct:
                    caption_matched_in_this_page[color] = (s['text'],s['bbox'])
                    last_color = ["caption", color]
                    continue
                if color==0 or color == (0,0,0) and last_color[0] == "caption":
                    color = last_color[1]
                    caption_matched_in_this_page[add_rgb(color)] = (s['text'],s['bbox'])
                    last_color = ["caption", color]
                else:
                    last_color = ["main_content", color]
                    if (text.lower().startswith('tab') or text.lower().startswith('fig')) and (color==0 or color == (0,0,0)):
                        logging.debug(f"seem tag: {text} we skip")
                    elif color==0 or color == (0,0,0):
                        sequence2boxed.append(s)
                    else:
                        if color not in color_to_position:
                            position = color_to_position[color] = len(sequence2boxed)
                            sequence2boxed.append([s])
                        elif position != len(sequence2boxed)-1:
                            ## this means the same color word and get splited by line break and also breaked via page break
                            sequence2boxed.append(s)
                        else:
                            position = color_to_position[color]
                            sequence2boxed[position].append(s)
    
    for color,val in block_equation_color_map.items():
        if color not in color_to_position:continue
        position = color_to_position[color]
        poollist = sequence2boxed[position]
        bbox     = merge_bboxes([t['bbox'] for t in poollist],tolerance=10000000)
        assert bbox is not None
        sequence2boxed[position] ={
            'text':val,
            'color':poollist[0]['color'],
            'bbox': bbox
        }
    
    for position in range(len(sequence2boxed)):
        part = sequence2boxed[position]
        if isinstance(part,list):
            text = "".join([t['text'].strip().strip("-") for t in part]) ## should be one word
            color= part[0]['color']
            bbox = merge_bboxes([t['bbox'] for t in part],tolerance=1)
            if bbox is None:
                bbox = part[0]['bbox']
            sequence2boxed[position] ={
                'text': text,
                'color':color,
                'bbox': bbox
            }
        assert isinstance(sequence2boxed[position],dict)
        

    
    figid_from_figure  = set([color_figid_map[key] for key in pdf_draw_color_bbox_map.keys() if key in pdf_draw_color_bbox_map])

    figid_from_caption = set([color_figid_map[key] for key in caption_matched_in_this_page.keys() if key in color_figid_map])
    should_fig_color = []
    for figid in figid_from_caption:
        should_fig_color.extend([c for c in fig_captions_list[figid]['figure'].keys()])


    should_cap_color = []
    for figid in figid_from_figure:
        should_cap_color.extend([c for c in fig_captions_list[figid]['caption'].keys() if is_meaningful_markdonw_color(c)])     
    
#     assert set(should_fig_color) - set(pdf_draw_color_bbox_map.keys()) == set()
#     assert set(should_cap_color) - set(caption_matched_in_this_page.keys()) == set() 
    sequence2boxed =    [(cb['color'], cb['text'], cb['bbox']) for cb in sequence2boxed]
    return sequence2boxed,caption_matched_in_this_page, figid_from_figure, figid_from_caption, pdf_draw_color_bbox_map,color_to_position

def sequence_sequence_alignment(current_mmd_color_dct,sequence2boxed, align_side='left'):
    
    sequence1o = [(color, text, dtype) for color, (text, dtype) in current_mmd_color_dct.items()]

    color_indexes_map = {color:i for i,(color, text, dtype) in enumerate(sequence1o) if color!=(0,0,0) and is_meaningful_markdonw_color(color)}
    sequence_pdf = sequence2boxed
    color_index_in_pdf = [color_indexes_map[color] for color,_,_ in sequence_pdf if color !=(0,0,0) and color in color_indexes_map] ### some color may appear in caption, then pass
    if len(color_index_in_pdf)==0:
        return None, None
    sequence_mmd = [(color, text, dtype) for color, text, dtype in sequence1o[max(0,min(color_index_in_pdf)-1):max(color_index_in_pdf)+1]]

    sequence_mmd = sequence1o

    sequence1=sequence_mmd
    sequence2=sequence_pdf

    
    pair = rough_split_by_color_pair(sequence2, sequence1)
    fail_to_match = False
    

    while len(pair)>0 and pair[-1][0] == 'need':
        pair.pop(-1)  ### this while totally remove the last sequence match ability but make more accuracte when color is applied properly
    if len(pair)==0:
        fail_to_match = True

    # for tag, i1,i2,j1,j2 in pair:
    #     print('{:7}   seq1[{}:{}] --> {}'.format(tag, i1, i2, sequence1[i1:i2]))
    #     print('          seq2[{}:{}] --> {}\n'.format(j1, j2, sequence2[j1:j2]))
    sequence1_text = [t[1] for t in sequence1]
    sequence2_text = [t[1] for t in sequence2]

    true_match = []
    for tag, i1,i2,j1,j2 in pair:
        if tag == 'need':
            seq1 = sequence1_text[i1:i2]
            seq2 = sequence2_text[j1:j2]
            for tag, i1_now, i2_now, j1_now, j2_now in get_real_match(seq1, seq2):
                true_match.append([tag,i1+i1_now, i1+i2_now,j1+j1_now, j1+j2_now])
        else:
            true_match.append([tag,i1, i2,j1, j2])
    if fail_to_match:
        return None, true_match
    # for tag, i1, i2, j1, j2 in true_match:
    #     print('{:7}   seq1[{}:{}] --> {}'.format(tag, i1, i2, sequence1[i1:i2]))
    #     print('          seq2[{}:{}] --> {}\n'.format(j1, j2, sequence2[j1:j2]))    

    ### remove the delete case from end which due to the len(marddown) > len(currentpage)
    if align_side == 'left':
        while true_match[-1][0] == 'delete':
            true_match.pop(-1)
    else:
        while true_match[-1][0] != 'aligned':
            true_match.pop(-1)

    ############## final match align ##################

    verbose_level=1
    pretext_and_prompts = []
    color_table_seq_pdf = {c: i for i, (c,_,_) in enumerate(sequence_pdf) if c != (0,0,0) and is_meaningful_markdonw_color(c)}
    for tag, i1, i2, j1, j2 in true_match:

        markdown_text = sequence1o[i1:i2]
        pdf_color_box = sequence2boxed[j1:j2]
        merged_text= " ".join([t[1] for t in pdf_color_box])
        if len(markdown_text)==0:
            if len(merged_text.strip())==0:continue
            if not all([sum(t[0])==0 for t in pdf_color_box]):

                logging.debug(f"({tag}, {i1}, {i2}, {j1}, {j2})This an empty markdown text but not empty pdf color box, throw it: the pdf box data is:")
                for data in pdf_color_box:
                    logging.debug(f"color={data[0]}, text= {data[1]}")
                logging.debug("=========================")
            else:
                logging.info(f"safe throw: markdown_text={markdown_text} merged_text={merged_text}")
            continue
        
        if len(pdf_color_box) == 0:
            for c, text, _type in markdown_text:
                if len(text.strip())==0:continue
                if invisable_symbol(text,_type):
                    pretext_and_prompts.append([text,['mask']])
                else:
                    
                    if verbose_level>0:
                        if is_meaningful_markdonw_color(c):
                            logging.debug(f"[Important] why you throw a meaningful markdown color={c} text={text}")
                        else:
                            logging.info(f"it seem you have to throw a text to match. The text={text} with color={c}")
            continue
        if len(markdown_text)>1:
            raise NotImplementedError(f"seem has problem for this mardown text: {markdown_text} ")
            
            
        (color,markdown_text, markdown_type) =  markdown_text[0]

        if tag in ['equal','aligned']:
            merged_bbox   = merge_bboxes([t[2] for t in pdf_color_box])
            if merged_bbox is None:merged_bbox = pdf_color_box[0][2]
            char_markdown = re.sub(r'[ -]+', '', markdown_text).lower()
            char_pdf = re.sub(r'[ -]+', '', "".join(merged_text)).lower()
            if  (char_markdown != char_pdf and 
                not  char_markdown.startswith(char_pdf) and 
                not  char_pdf.startswith(char_markdown) and
                not  char_markdown.endswith(char_pdf) and
                not  char_pdf.endswith(char_markdown) and
                not  invisable_symbol(markdown_text,markdown_type)
                ):

                if any([isinstance(c,float) for c in color]) :
                    pretext_and_prompts.append([markdown_text,['throw']])
                    logging.info(f"bad match!!! throw {markdown_type}:{markdown_text.strip()}<=>{merged_text.strip()} char level is {char_markdown}<=>{char_pdf} {[int(l) for l in merged_bbox]}")
                else:
                    pretext_and_prompts.append([markdown_text,['mask']])
                    logging.info(f"bad match!!! but {markdown_text.strip()} is a unvisable sign, skip")
                continue
            if merged_bbox is None:
                ### is may due to the Line breaks such as 
                ###  xxxxxxxxxx out-
                ###  side xxxxxxxxxx
                ###  xxxxxxxxxxxxxxx
                ### for those case, lets divide the markdown_text
                if char_markdown != char_pdf:
                    logging.info(f"mismatch?? [{markdown_text}] <=> [{merged_text}]")
                for color_box in pdf_color_box:
                    markdown_text = merged_text = color_box[1]
                    merged_bbox   = color_box[2]
                    pretext_and_prompts.append([markdown_text,merged_bbox])
                    logging.info(f"{tag:7s} {markdown_text.strip():20s} {merged_text.strip():20s} {[int(l) for l in merged_bbox]}")

            else:
                pretext_and_prompts.append([markdown_text,merged_bbox])
                logging.info(f"{tag:7s} {markdown_text.strip():20s} {merged_text.strip():20s} {[int(l) for l in merged_bbox]}")

        elif tag == 'delete':
            if is_this_part_is_invisable_symbol_in_markdown(markdown_text):
                logging.info("this is the invisable markdown text", markdown_text.strip(),merged_text.strip() )
                pretext_and_prompts.append([markdown_text,"[mask]"])
            elif any([isinstance(c,float) for c in color]):

                if all([t['color']==0 for t in pdf_color_box]):
                    ### this mean there is symbol in markdown is not get colored by pdf engine like µ
                    ### lets put it back to last markdown slot

                    ##### since we pre caption already, this still should not appear here 
                    if pretext_and_prompts and pretext_and_prompts[-1][1]!='throw':
                        pretext_and_prompts[-1][0]+=' '+markdown_text
                    logging.info("put the symbol to last markdone slot", markdown_text.strip(),merged_text.strip() )
                else:
                    logging.info(f"safe throw as it is a black symbol but no markdown source: markdown_text={markdown_text.strip()} merged_text={merged_text.strip()}")
            elif color in color_table_seq_pdf:
                target_j = color_table_seq_pdf[color]
                merged_text = sequence2boxed[target_j]['text']
                merged_bbox = sequence2boxed[target_j]['bbox']
                # but it should not match here since we pre match caption already, lets throw
                logging.debug(f"==> [this should not appear] color match {target_j} <===",markdown_text.strip(),merged_text.strip(), [int(l) for l in merged_bbox])

            else:
                logging.debug("==> unsave throw <===",markdown_text.strip(),merged_text.strip() )
                ## then we will use color find the correct part
        else:

            logging.debug(tag,markdown_text,merged_text )


    return pretext_and_prompts, true_match

def invisable_symbol(text,_type):
    return _type in ['<inline_math>', '<block_math>', '<blockmath>'] or is_this_part_is_invisable_symbol_in_markdown(text)

def is_this_part_is_invisable_symbol_in_markdown(part):
    if part.startswith('#'):
        return True
    if part in ['\\)','\\(','\\[','\\]']:
        return True
    return False


def deal_with_single_page(page,current_mmd_color_dct,block_equation_color_map,cap_color_dct,fig_color_dct,color_figid_map,fig_captions_list):
    
    sequence2boxed,caption_matched_in_this_page,figid_from_figure, figid_from_caption, pdf_draw_color_bbox_map,color_to_position = get_pdf_text_with_colored(page,block_equation_color_map,cap_color_dct,fig_color_dct,color_figid_map,fig_captions_list)

    pretext_and_prompts,true_match = sequence_sequence_alignment(current_mmd_color_dct,sequence2boxed)
    #all_keys = [k for k in current_mmd_color_dct.keys()]
    #all_keys = all_keys[true_match[-1][2]:]
    #next_current_mmd_color_dct = OrderedDict({k:current_mmd_color_dct[k] for k in all_keys})
    #### add figure/table caption at end 
    if pretext_and_prompts is None:
        return None, true_match
    caption_start_position = 0
    pretext_and_prompts[-1][0]+='\n\n'
    caption2boxed=[(c,t,b) for c,(t,b) in caption_matched_in_this_page.items()]
    for figid in figid_from_caption:
        caption2boxed_now = caption2boxed[caption_start_position:]
        fig_cap = fig_captions_list[figid]
        fig = fig_cap['figure']
        cap = fig_cap['caption']
        for c, v in fig.items():
            if v[0] == "FOOTNOTE":
                pretext_and_prompts.append((f"<footnote>{v}</footnote>\n",['mask']))
            else:
                pretext_and_prompts.append((f"<fig>{v}</fig>\n",pdf_draw_color_bbox_map[c]))
        if len(cap)>0:
            pretext_and_prompts.append((f"<cap>",'[mask]'))
            pretext_and_prompts2,true_match_caption = sequence_sequence_alignment(cap,caption2boxed_now, align_side='right')
            caption_start_position = 0 #true_match_caption[-1][-1]
            pretext_and_prompts.extend(pretext_and_prompts2)
            pretext_and_prompts.append((f"</cap>",'[mask]'))
    
    return pretext_and_prompts,true_match

from PIL import Image, ImageDraw
def deal_with_one_pdf_file(html_path, pdf_file_path,args):
    if args.verbose: print(f"we start reading coloed markdown from {html_path}")
    (mmd,
    mmd_color_dct,
    cap_color_dct,
    fig_color_dct,
    fig_captions_list,
    color_figid_map,block_equation_color_map) = get_markdown_text_with_colored(html_path)
    
    now_table_figure_masked_pdf = pdf_file_path.replace('.colorful.pdf','.colorful_text_colored.pdf')
    #pdf_file_path = pdf_file_path.replace('.colorful.pdf','.colorful_all_colored.pdf')
    
    if args.verbose: 
        print(f"we start reading full coloed pdf from {pdf}")
        print(f"we start reading normal coloed pdf from {now_table_figure_masked_pdf}")
    pdf      = fitz.open(pdf_file_path)
    pdf0     = fitz.open(now_table_figure_masked_pdf)
    png_dir  = os.path.join(os.path.dirname(os.path.dirname(pdf_file_path)),'boxed_pdf_image')
    os.makedirs(png_dir,exist_ok=True)
    
    whole_markdown=""
    start_position = 0
    for page_idx in range(len(pdf)):
        page = pdf[page_idx]
        page0=pdf0[page_idx]
        clean_png_path = os.path.join(png_dir, 'clean',f"page_{page_idx}.png")
        os.makedirs(os.path.dirname(clean_png_path),exist_ok=True)
        with open(clean_png_path, "wb") as f:
            f.write(page0.get_pixmap(dpi=300).pil_tobytes(format="PNG"))      
        all_keys = [k for k in mmd_color_dct.keys()]
        all_keys = all_keys[start_position:]
        current_mmd_color_dct = OrderedDict({k:mmd_color_dct[k] for k in all_keys})
        try:
            pretext_and_prompts,true_match = deal_with_single_page(page,current_mmd_color_dct,block_equation_color_map,cap_color_dct,fig_color_dct,color_figid_map,fig_captions_list)
            start_position = 0
        
            # if len(true_match) > 0:start_position += true_match[-1][2]

            if pretext_and_prompts == None:
                logging.warning(f""" ============ fail to processing page {page_idx} ======================= """)
            else:
                _,_,page_w,page_h = page.rect
                normed_pretext_and_prompts = []
                for text, bbox in pretext_and_prompts:
                    if isinstance(bbox,tuple) and len(bbox)==4:
                        bbox  = norm_box(bbox,page_h,page_w)
                    normed_pretext_and_prompts.append([text, bbox])
                if args.verbose:
                    logging.info(f""" ============= for page {page_idx}, we get {len(normed_pretext_and_prompts)} box =================== """)
                img = Image.open(clean_png_path)

                for text_and_box in normed_pretext_and_prompts:
        
                    if len(text_and_box)!=2:logging.debug(text_and_box)
                    text, box = text_and_box
                    if box is None:logging.debug(text_and_box)
                    if len(box[0])!=2 or len(box[1])!=2: continue
                    bbox = box
                    width, height = img.size

                    # Convert bbox from normalized to pixel coordinates
                    pixel_bbox = [
                        bbox[0][0] * width,  # xmin
                        bbox[0][1] * height, # ymin
                        bbox[1][0] * width,  # xmax
                        bbox[1][1] * height  # ymax
                    ]

                    # Create a draw object
                    draw = ImageDraw.Draw(img)

                    # Draw the rectangle
                    draw.rectangle(pixel_bbox, outline='red', width=2)
                    
                boxed_image = os.path.join(png_dir, 'boxed',f"boxed_page_{page_idx}.png")
                os.makedirs(os.path.dirname(boxed_image),exist_ok=True)
                img.save(boxed_image)
                boxed_info  = os.path.join(png_dir, 'text_bbox',f"page_{page_idx}.jsonl")
                os.makedirs(os.path.dirname(boxed_info),exist_ok=True)
                boxed_dict  = [{'text':t, 'bbox':b} for t,b in normed_pretext_and_prompts]
                with open(boxed_info,'w') as f:
                    json.dump(boxed_dict, f)

                for text, _ in normed_pretext_and_prompts:
                    whole_markdown+=" "+text   
        except:
            if args.debug:
                
                traceback.print_exc()
                raise
            else:
                logging.warning(f""" ============ fail to processing page {page_idx} ======================= """)
                continue
            
    with open(os.path.join(png_dir, 'content.md'),'w') as f:
        f.write(whole_markdown)     
import traceback
def deal_with_one_pdf_file_wrapper(args):
    html_path, args = args
    if not os.path.exists(html_path):
        return 'no_source', html_path
    if os.path.getsize(html_path)< 10_000:
        return 'small_source', html_path
    assert html_path.endswith('.html')
    success_file = html_path.replace('.html','.success')
    if os.path.exists(success_file) and not args.redo:
        return 'skip', html_path
    try:

        pdf_path  = html_path[:-5] + '.pdf'
        deal_with_one_pdf_file(html_path, pdf_path, args)
        
        with open(success_file, "a") as f: 
            pass


        return 'pass', html_path
    except Exception as e:
        print(f"error for {html_path} with {e}")
        if args.debug:
            traceback.print_exc()
            raise
        return 'fail', html_path