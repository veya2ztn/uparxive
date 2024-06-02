import re
import json
import random
import datetime
import os
from pathlib import Path
import logging
ROOTFILE = Path(__file__).resolve().parent
with open(os.path.join(ROOTFILE,'Greek.json'),'r') as fi:
    GREEK = json.loads(fi.read())
with open(os.path.join(ROOTFILE,'MathSymbol.json'),'r') as fi:
    MATH = json.loads(fi.read())
with open(os.path.join(ROOTFILE,'symbol_dictionary.json'),'r') as fi:
    SYMBOLS = json.loads(fi.read())

dct_greek2math = {}
for k,v in GREEK.items():
    dct_greek2math[v] = k   
COLORS = [(r,g,b) for r in range(5,255,5) for g in range(0,255,5) for b in range(0,255,5)]
color_idx = 0
MATH=set(MATH+SYMBOLS)

def greater_rgb(color1,color2):
    '''
    color1:(r,g,b)
    color2:(r,g,b)
    '''
    if color1[0]==color2[0]:
        if color1[1] == color2[1]:
            return color1[2]>color2[2]
        else:
            return color1[1]>color2[1]
    else:
        return color1[0]>color2[0] 
    
def add_rgb(color,increment=0.1):
    # 对(R,G,B)计算加法，递增序列
    if color[2]+increment <= 255:
        return (color[0],color[1],color[2]+increment)
    elif color[1]+increment <= 255:
        return (color[0],color[1]+increment,0)
    else:
        return (color[0]+increment,color[1],color[2])

def inserted_color(color):
    # 判断color是否为后加入的，即不可见符号
    for i in range(3):
        if color[i]%5:
            return True
    return False

def box_distance(box1,box2,alpha=16):
    # |x1-x2|<=50,|y1-y2|<=20
    center1 = ((box1[0][0]+box1[1][0])/2,(box1[0][1]+box1[1][1])/2)
    center2 = ((box2[0][0]+box2[1][0])/2,(box2[0][1]+box2[1][1])/2)
    distance = (center1[0]-center2[0])**2+alpha*(center1[1]-center2[1])**2
    return distance**.5

def random_date():
    year = random.randint(1800,2025)
    month = random.randint(1,12)
    day = random.randint(1,28)
    random_date = datetime.date(year,month,day).strftime('%B %d, %Y')
    return random_date

def get_one_color():
    global color_idx
    color = f"{'{:03}'.format(COLORS[color_idx][0])},{'{:03}'.format(COLORS[color_idx][1])},{'{:03}'.format(COLORS[color_idx][2])}"
    color_idx  = (color_idx+1)%len(COLORS)
    return color

def colored_word(word):
    if word == "\\sqrt":
        return word
    color = get_one_color()
    if word in [r'\'', r'\"']:
        return ""

    if word == "&":
        return "&"
    if word.startswith(f'\\') and len(word)<3:
        return word
    if word == '\\left(': word= '('
    if word == '\\right)': word= ')'
    if word == '\\left\{': word= '\{'
    if word == '\\right\}': word= '\}'
    if word == '\\left[': word= ']'
    if word == '\\right]': word= ']'   
    if word == '\\~': word = " "
    color_word = f'\\textcolor[RGB]{{{color}}}{{{word}}}'
    return color_word

def encapsulate_command_arguments(text):
    # List of LaTeX commands that should be followed by a single letter or digit argument
    commands = [
        r'\\bar', r'\\dot', r'\\ddot', r'\\vec'
    ]
    command_pattern = r'(' + '|'.join(commands) + r')\s+([a-zA-Z0-9])'

    # Use regex to find and replace occurrences where a command is followed by a single letter or digit
    def replace_func(match):
        command = match.group(1)  # The command part
        argument = match.group(2)  # The single character argument
        return f'{command}{{{argument}}}'  # Encapsulate the argument in braces

    # Perform the transformation
    transformed_text = re.sub(command_pattern, replace_func, text)
    return transformed_text

mathfunction = [
        r'\\bar', r'\\overline', r'\\mathfrak', r'\\mathbb',
        r'\\script', r'\\mathscr', r'\\code',  r'\\cancel',
        r'\\dot', r'\\vector', r'\\ddot', r'\\vec', r'\\mathrm',r'\\text'
    ]

def colored_text_math(text):
    # LaTeX commands to look for
    text = encapsulate_command_arguments(text)
    commands = mathfunction
    command_pattern = r'(' + '|'.join(commands) + r')\s*({[^}]*}|[^\s]*)'

    # Split the text by space to handle each segment independently
    segments = text.split()
    processed_segments = []

    for segment in segments:
        # Find all occurrences of LaTeX commands followed by their arguments
        match = re.search(command_pattern, segment)
        if match:
            start_index = match.start()
            if start_index > 0:
                # Add preceding text if there's any
                processed_segments.append(segment[:start_index])
            
            # Check the character immediately after the command
            command_end_index = match.end()
            if command_end_index < len(segment):
                next_char = segment[command_end_index]
                if next_char == '{':
                    # Command followed by a braced argument
                    brace_end = segment.find('}', command_end_index) + 1
                    processed_segments.append(segment[start_index:brace_end])
                    if brace_end < len(segment):
                        processed_segments.append(segment[brace_end:])
                else:
                    # Command followed by a space and a single character
                    processed_segments.append(segment[start_index:command_end_index+2])
                    if command_end_index+2 < len(segment):
                        processed_segments.append(segment[command_end_index+2:])
            else:
                # Command at the end of the segment
                processed_segments.append(segment[start_index:])
        else:
            # No command found, append the whole segment
            processed_segments.append(segment)

    processed_segments = [treat_seg(t) for t in processed_segments]
    # Rejoin the processed segments with space
    # print(text)
    # print(processed_segments)
    return ' '.join(processed_segments)

def treat_seg(seg):
    seg_idx = 0
    new_seg = ''
    while seg_idx < len(seg):  
        # \tag
        tag_res = re.match(r'\\[A-Za-z]+',seg[seg_idx:])
        if tag_res:
            word = tag_res.group(0)
            # 加颜色显示的tag: \alpha \sum
            if word in GREEK.keys() or word in MATH:
                """
                \frac is a function and cause problem when it is colored
                \bar  is a function and cause problem when it followed a colored should corlor for whole like \color{\bar\nu}
                """
                new_seg += colored_word(word)
                seg_idx += tag_res.span()[1]
                logging.debug(f"at seg_idx={seg_idx}. word is greek={word}")
                continue
            
            # 需要和后面[]*{}内容一起保留原样的tag
            elif word in ['\\label','\\begin','\\end','\\includegraphics','\\resizebox','\\cline','\\multicolumn','\\multirow','\\pagestyle','\\email',
                            '\\input','\\bibliographystyle','\\bibliography','\\newcommand','\\usepackage','\\preprint','\\ref','\\url','\\bibitem','\\bibinfo','\\bibnamefont'] \
                            or any(banword in word for banword in ['\\cite','\\ref','hspace','vspace']):  # \\citep,\\citen,\\hspace*
                ignore_res = re.match(r'\\[A-Za-z]+(?:\[.*?\])*(?:\{.*?\}){1,2}',seg[seg_idx:])
                new_seg += ignore_res.group(0) if ignore_res else word
                seg_idx += ignore_res.span()[1] if ignore_res else tag_res.span()[1]
                logging.debug(f"at seg_idx={seg_idx}. word is tag={word}")
                continue
            # 需要和后面[]*{}内容一起保留原样的tag
            elif word in mathfunction and seg_idx+ tag_res.span()[1] < len(seg)  and seg[seg_idx+ tag_res.span()[1]] not in [r'[',r'{',r'<',r'(']: ### otherwise fail into the third part
                ## in some case it use \bar a which will be split into \bar and a, so we need to merge them
                seg_idx += tag_res.span()[1]
                greek_res = re.match(r'\\[A-Za-z]+',seg[seg_idx:])
                try:
                    if greek_res:   # 希腊字母
                        new_seg += colored_word(word + greek_res.group(0)) 
                        seg_idx += 0 + greek_res.span()[1]
                    else:   # 英文字母
                        
                        new_seg += colored_word(word +  seg[seg_idx+1]) 
                        seg_idx += 1 ## this is for the "{" which we dont have one, such skip
                except:
                    print(word, seg)
                    raise
                logging.debug(f"math function:{new_seg}")
                continue
            # 需要和后面合并在一起: \\left(  \\left\\{  \\left\vert \\big( \\Bigg\{
            elif re.match(r'(\\[A-Za-z]+)(\(|\)|\[|\]|\\{|\\}|<|>|\||\\[A-Za-z]+)',seg[seg_idx:]):
                ltag_res = re.match(r'(\\[A-Za-z]+)(\(|\)|\[|\]|\\{|\\}|<|>|\||\\[A-Za-z]+)',seg[seg_idx:])
                lword = ltag_res.group(0)
                if lword in MATH:
                    new_seg += colored_word(ltag_res.group(0)) 
                    seg_idx += ltag_res.span()[1] 
                else:   # 按照其他tag处理，后面的括号是勿匹配
                    new_seg +=  word
                    seg_idx +=  tag_res.span()[1]
                
            # 保留原样，不加颜色不忽略后文的tag：\it \frac等   
            else:
                new_seg += word
                seg_idx += tag_res.span()[1]
                logging.debug("tag_res:",word)
            continue
        # (x,y)：坐标，保持不变
        coord_res = re.match(r'\(-?\d+,-?\d+\)',seg[seg_idx:])
        if coord_res:
            new_seg += coord_res.group(0)
            seg_idx += coord_res.span()[1]
            logging.debug("coord_res:",coord_res.group(0),f"start from {seg_idx}")
            continue
        # 制表符：删不净：保持不变
        vh_res = re.match(r'-?\d+(pt|mm|bp|cm|em|ex|in)',seg[seg_idx:])
        if vh_res:
            new_seg += vh_res.group(0)
            seg_idx += vh_res.span()[1]
            logging.debug("vh_res:",vh_res.group(0),f"go to {seg_idx}")
            continue
        # invisible符号：_, ^, { 等：不加颜色，保留原样
        invisible_res = re.match(r'(\{\[\})|_|\^|\||\{|\}|\$|\\\\|\\$|\[.*\]|&|%|\s+|\*|~|#|\[|\]|(natexlab)|(urlprefix)|\\(!|,|;)',seg[seg_idx:])
        if invisible_res:
            # 上下标没加括号：后面必为一个字母或希腊字母，这时最好加上括号
            if seg[seg_idx] in ['_','^'] and seg_idx < len(seg)-1 and seg[seg_idx+1] != '{':
                greek_res = re.match(r'\\[A-Za-z]+',seg[seg_idx+1:])
                if greek_res:   # 希腊字母
                    new_seg += seg[seg_idx]+'{' + colored_word(greek_res.group(0)) + '}'
                    seg_idx += 1 + greek_res.span()[1]
                else:   # 英文字母
                    new_seg += seg[seg_idx]+'{'+colored_word(seg[seg_idx+1]) + '}'
                    seg_idx += 2
            else:
                new_seg += invisible_res.group(0)  
                seg_idx += invisible_res.span()[1] 
            logging.debug("invisible:",invisible_res.group(0),f"go to {seg_idx}", f"new_seg: {new_seg}" )
            continue
        # visible符号：字母、数字、运算符、转义字符等: 加颜色
        visible_res = re.match(r'(\.*\s*[A-Za-z]+)|(\d+(,|\.)*)+|\+|-|/|>|<|=|\(|\)|,|\.|@|;|!|\?|\:|\'|\"|`|(\\[^\\])',seg[seg_idx:])
        if visible_res:
            new_seg += colored_word(visible_res.group(0))
            seg_idx += visible_res.span()[1]
            logging.debug("visible_res:",visible_res.group(0),f"go to {seg_idx}", f"new_seg: {new_seg}" )
            continue
        
        else: # 理论上不应该到这里，先保留原样
            logging.debug(f'unhandled char:"{seg[seg_idx:]}"', f"new_seg: {new_seg}" )
            new_seg += seg[seg_idx]
            seg_idx += 1
            
            continue
    return new_seg

from tqdm.auto import tqdm
def colored_text(text, end='\n'):    
    if len(text.strip())==0:return text
    texts = [seg for seg in re.split(r'(\\[A-Za-z]+(?:\[.*?\])*(?:\{.*?\})+)|\s', text) if seg]  # 使用\tag[]{}或\tag{}或空白符将句子分为单词，括号内不会被切分
    new_text = []

    for j,seg in enumerate(texts):
        if not seg: continue
        new_seg = treat_seg(seg)
            
        new_text.append(new_seg )
        
    color_text = end.join(new_text)
    return color_text

def colored_file(tex_file, output_file=None):
            
    with open(tex_file,'r',encoding='utf-8') as fi:
        lines = fi.read()
    # 删除注释和不必要的定义头
    lines = re.sub(r'%.*?\n|\\vskip.*?\n|\\vspace.*?\n','\n',lines)
    # 参考文献后面不处理
    if '\\begin{thebibliography}' in lines:
        lines,reference = re.split(r'(?=\\begin\{thebibliography\})', lines)
    else:
        reference = ''
    # 开头的预定义部分不处理
    if '\\begin{document}' in lines:
        predef,lines = re.split(r'(?=\\begin\{document\})',lines)
    else:
        predef = ''
        
    
    # 按照真正的换行位置切分：双斜杠；author和affiliation所在的行单独筛选出来
    lines = re.split(r'\n\n|(?=\\author)|(?=\\affiliation)',lines)
    
    for i,line in enumerate(lines):
        line = line.strip().replace('\n',' ')
        if '\\def' in line:
            continue
        # 去除affiliation和author内部的花括号，否则可能编译出错
        if '\\affiliation' in line: # F\'{\i}sica -> F\'isica
            content = re.match(r'\\affiliation(?:\[.*?\])*\{(.*)\}',line[line.index('\\affiliation'):]).group(1)
            new_content =re.sub(r'(?=[^\^])\{([a-z])\}(?=[^\$])',r'\1',content)
            line = line.replace(content,new_content)
            lines[i] = line
            continue    # affiliation颜色不变
          
        if '\\author' in line:  #\author{C. Bal\'{a}zs$^{1}$} -> C. Bal\'azs$^{1}$
            res = re.match(r'\\author(?:\[.*?\])*\{(.*)\}',line[line.index('\\author'):])
            if res:
                content = res.group(1)
                new_content = re.sub(r'(?=[^\^])\{([a-z])\}(?=[^\$])',r'\1',content)
                line = line.replace(content,new_content)
        
        # 将'\\date{\\today}'函数换为固定日期，防止mmd和PDF生成的日期不同
        if re.search(r'\\date\{.*?\}',line):
            line = line.replace('\\today',random_date())  
        
        
        lines[i] = colored_text(line)
        
        
    lines = '\n\n'.join(lines)
        
    lines = predef + '\\usepackage{xcolor}\n\n'+ lines + reference
    # 去除多余空行
    lines = re.sub('\n\n+','\n\n',lines)
    if output_file is None:
        output_file = tex_file.replace('.tex','.colored.tex')
    with open(output_file,'w',encoding='utf-8') as fo:
        fo.writelines(lines)
         
class colorful_engine:
    def __init__(self, enable):
        self.enable = enable
        self.color_idx = 0
    def get_one_color(self):
        if self.enable:
            color = f"{'{:03}'.format(COLORS[self.color_idx][0])},{'{:03}'.format(COLORS[self.color_idx][1])},{'{:03}'.format(COLORS[self.color_idx][2])}"
            self.color_idx = (self.color_idx+1)%len(COLORS)
            return color
        else:
            return f"0,0,0"
        
    def treat_seg(self,seg):
        seg_idx = 0
        new_seg = ''
        while seg_idx < len(seg):  
            # \tag
            tag_res = re.match(r'\\[A-Za-z]+',seg[seg_idx:])
            if tag_res:
                word = tag_res.group(0)
                # 加颜色显示的tag: \alpha \sum
                if word in GREEK.keys() or word in MATH:
                    """
                    \frac is a function and cause problem when it is colored
                    \bar  is a function and cause problem when it followed a colored should corlor for whole like \color{\bar\nu}
                    """
                    new_seg += colored_word(word)
                    seg_idx += tag_res.span()[1]
                    logging.debug(f"at seg_idx={seg_idx}. word is greek={word}")
                    continue
                
                # 需要和后面[]*{}内容一起保留原样的tag
                elif word in ['\\label','\\begin','\\end','\\includegraphics','\\resizebox','\\cline','\\multicolumn','\\multirow','\\pagestyle','\\email',
                                '\\input','\\bibliographystyle','\\bibliography','\\newcommand','\\usepackage','\\preprint','\\ref','\\url','\\bibitem','\\bibinfo','\\bibnamefont'] \
                                or any(banword in word for banword in ['\\cite','\\ref','hspace','vspace']):  # \\citep,\\citen,\\hspace*
                    ignore_res = re.match(r'\\[A-Za-z]+(?:\[.*?\])*(?:\{.*?\}){1,2}',seg[seg_idx:])
                    new_seg += ignore_res.group(0) if ignore_res else word
                    seg_idx += ignore_res.span()[1] if ignore_res else tag_res.span()[1]
                    logging.debug(f"at seg_idx={seg_idx}. word is tag={word}")
                    continue
                # 需要和后面[]*{}内容一起保留原样的tag
                elif word in mathfunction and seg_idx+ tag_res.span()[1] < len(seg)  and seg[seg_idx+ tag_res.span()[1]] not in [r'[',r'{',r'<',r'(']: ### otherwise fail into the third part
                    ## in some case it use \bar a which will be split into \bar and a, so we need to merge them
                    seg_idx += tag_res.span()[1]
                    greek_res = re.match(r'\\[A-Za-z]+',seg[seg_idx:])
                    try:
                        if greek_res:   # 希腊字母
                            new_seg += colored_word(word + greek_res.group(0)) 
                            seg_idx += 0 + greek_res.span()[1]
                        else:   # 英文字母
                            
                            new_seg += colored_word(word +  seg[seg_idx+1]) 
                            seg_idx += 1 ## this is for the "{" which we dont have one, such skip
                    except:
                        print(word, seg)
                        raise
                    logging.debug(f"math function:{new_seg}")
                    continue
                # 需要和后面合并在一起: \\left(  \\left\\{  \\left\vert \\big( \\Bigg\{
                elif re.match(r'(\\[A-Za-z]+)(\(|\)|\[|\]|\\{|\\}|<|>|\||\\[A-Za-z]+)',seg[seg_idx:]):
                    ltag_res = re.match(r'(\\[A-Za-z]+)(\(|\)|\[|\]|\\{|\\}|<|>|\||\\[A-Za-z]+)',seg[seg_idx:])
                    lword = ltag_res.group(0)
                    if lword in MATH:
                        new_seg += colored_word(ltag_res.group(0)) 
                        seg_idx += ltag_res.span()[1] 
                    else:   # 按照其他tag处理，后面的括号是勿匹配
                        new_seg +=  word
                        seg_idx +=  tag_res.span()[1]
                    
                # 保留原样，不加颜色不忽略后文的tag：\it \frac等   
                else:
                    new_seg += word
                    seg_idx += tag_res.span()[1]
                    logging.debug("tag_res:",word)
                continue
            # (x,y)：坐标，保持不变
            coord_res = re.match(r'\(-?\d+,-?\d+\)',seg[seg_idx:])
            if coord_res:
                new_seg += coord_res.group(0)
                seg_idx += coord_res.span()[1]
                logging.debug("coord_res:",coord_res.group(0),f"start from {seg_idx}")
                continue
            # 制表符：删不净：保持不变
            vh_res = re.match(r'-?\d+(pt|mm|bp|cm|em|ex|in)',seg[seg_idx:])
            if vh_res:
                new_seg += vh_res.group(0)
                seg_idx += vh_res.span()[1]
                logging.debug("vh_res:",vh_res.group(0),f"go to {seg_idx}")
                continue
            # invisible符号：_, ^, { 等：不加颜色，保留原样
            invisible_res = re.match(r'(\{\[\})|_|\^|\||\{|\}|\$|\\\\|\\$|\[.*\]|&|%|\s+|\*|~|#|\[|\]|(natexlab)|(urlprefix)|\\(!|,|;)',seg[seg_idx:])
            if invisible_res:
                # 上下标没加括号：后面必为一个字母或希腊字母，这时最好加上括号
                if seg[seg_idx] in ['_','^'] and seg_idx < len(seg)-1 and seg[seg_idx+1] != '{':
                    greek_res = re.match(r'\\[A-Za-z]+',seg[seg_idx+1:])
                    if greek_res:   # 希腊字母
                        new_seg += seg[seg_idx]+'{' + colored_word(greek_res.group(0)) + '}'
                        seg_idx += 1 + greek_res.span()[1]
                    else:   # 英文字母
                        new_seg += seg[seg_idx]+'{'+colored_word(seg[seg_idx+1]) + '}'
                        seg_idx += 2
                else:
                    new_seg += invisible_res.group(0)  
                    seg_idx += invisible_res.span()[1] 
                logging.debug("invisible:",invisible_res.group(0),f"go to {seg_idx}", f"new_seg: {new_seg}" )
                continue
            # visible符号：字母、数字、运算符、转义字符等: 加颜色
            visible_res = re.match(r'(\.*\s*[A-Za-z]+)|(\d+(,|\.)*)+|\+|-|/|>|<|=|\(|\)|,|\.|@|;|!|\?|\:|\'|\"|`|(\\[^\\])',seg[seg_idx:])
            if visible_res:
                new_seg += colored_word(visible_res.group(0))
                seg_idx += visible_res.span()[1]
                logging.debug("visible_res:",visible_res.group(0),f"go to {seg_idx}", f"new_seg: {new_seg}" )
                continue
            
            else: # 理论上不应该到这里，先保留原样
                logging.debug(f'unhandled char:"{seg[seg_idx:]}"', f"new_seg: {new_seg}" )
                new_seg += seg[seg_idx]
                seg_idx += 1
                
                continue
        return new_seg

    def colored_text_math(self,text):
        # LaTeX commands to look for
        text = encapsulate_command_arguments(text)
        commands = mathfunction
        command_pattern = r'(' + '|'.join(commands) + r')\s*({[^}]*}|[^\s]*)'

        # Split the text by space to handle each segment independently
        segments = text.split()
        processed_segments = []

        for segment in segments:
            # Find all occurrences of LaTeX commands followed by their arguments
            match = re.search(command_pattern, segment)
            if match:
                start_index = match.start()
                if start_index > 0:
                    # Add preceding text if there's any
                    processed_segments.append(segment[:start_index])
                
                # Check the character immediately after the command
                command_end_index = match.end()
                if command_end_index < len(segment):
                    next_char = segment[command_end_index]
                    if next_char == '{':
                        # Command followed by a braced argument
                        brace_end = segment.find('}', command_end_index) + 1
                        processed_segments.append(segment[start_index:brace_end])
                        if brace_end < len(segment):
                            processed_segments.append(segment[brace_end:])
                    else:
                        # Command followed by a space and a single character
                        processed_segments.append(segment[start_index:command_end_index+2])
                        if command_end_index+2 < len(segment):
                            processed_segments.append(segment[command_end_index+2:])
                else:
                    # Command at the end of the segment
                    processed_segments.append(segment[start_index:])
            else:
                # No command found, append the whole segment
                processed_segments.append(segment)

        processed_segments = [self.treat_seg(t) for t in processed_segments]
        # Rejoin the processed segments with space
        # print(text)
        # print(processed_segments)
        return ' '.join(processed_segments)


    def colored_word(self, word):
        if word == "\\sqrt":
            return word
        color = self.get_one_color()
        if word in [r'\'', r'\"']:
            return ""

        if word == "&":
            return "&"
        if word.startswith(f'\\') and len(word)<3:
            return word
        if word == '\\left(': word= '('
        if word == '\\right)': word= ')'
        if word == '\\left\{': word= '\{'
        if word == '\\right\}': word= '\}'
        if word == '\\left[': word= ']'
        if word == '\\right]': word= ']'   
        if word == '\\~': word = " "
        color_word = f'\\textcolor[RGB]{{{color}}}{{{word}}}'
        return color_word

if __name__ == '__main__':
    import sys
    source_path = sys.argv[1]
    colored_file(source_path)


