import re
import json
import random
import datetime
import os
from pathlib import Path

ROOTFILE = Path(__file__).resolve().parent
with open(os.path.join(ROOTFILE,'Greek.json'),'r') as fi:
    GREEK = json.loads(fi.read())
with open(os.path.join(ROOTFILE,'MathSymbol.json'),'r') as fi:
    MATH = json.loads(fi.read())
dct_greek2math = {}
for k,v in GREEK.items():
    dct_greek2math[v] = k   
COLORS = [(r,g,b) for r in range(5,255,5) for g in range(0,255,5) for b in range(0,255,5)]
color_idx = 0

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

def colored_word(word):
    global color_idx
    color = f"{'{:03}'.format(COLORS[color_idx][0])},{'{:03}'.format(COLORS[color_idx][1])},{'{:03}'.format(COLORS[color_idx][2])}"
    color_idx  = (color_idx+1)%len(COLORS)
    color_word = f'\\textcolor[RGB]{{{color}}}{{{word}}}'
    return color_word

def colored_text(text):    
    
    texts = [seg for seg in re.split(r'(\\[A-Za-z]+(?:\[.*?\])*(?:\{.*?\})+)|\s', text) if seg]  # 使用\tag[]{}或\tag{}或空白符将句子分为单词，括号内不会被切分
    # seg: 单词、公式等切分片段
    for j,seg in enumerate(texts):
        if not seg:
            continue
        seg_idx = 0
        new_seg = ''
        while seg_idx < len(seg):            
            # \tag
            tag_res = re.match(r'\\[A-Za-z]+',seg[seg_idx:])
            if tag_res:
                word = tag_res.group(0)
                # 加颜色显示的tag: \alpha \sum
                if word in GREEK.keys() or word in MATH:
                    new_seg += colored_word(word)
                    seg_idx += tag_res.span()[1]
                    continue
                # 需要和后面[]*{}内容一起保留原样的tag
                elif word in ['\\label','\\begin','\\end','\\includegraphics','\\resizebox','\\cline','\\multicolumn','\\multirow','\\pagestyle','\\email',
                              '\\input','\\bibliographystyle','\\bibliography','\\newcommand','\\usepackage','\\preprint','\\ref','\\url','\\bibitem','\\bibinfo','\\bibnamefont'] \
                                or any(banword in word for banword in ['\\cite','\\ref','hspace','vspace']):  # \\citep,\\citen,\\hspace*
                    ignore_res = re.match(r'\\[A-Za-z]+(?:\[.*?\])*(?:\{.*?\}){1,2}',seg[seg_idx:])
                    new_seg += ignore_res.group(0) if ignore_res else word
                    seg_idx += ignore_res.span()[1] if ignore_res else tag_res.span()[1]
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
                continue
            # (x,y)：坐标，保持不变
            coord_res = re.match(r'\(-?\d+,-?\d+\)',seg[seg_idx:])
            if coord_res:
                new_seg += coord_res.group(0)
                seg_idx += coord_res.span()[1]
                continue
            # 制表符：删不净：保持不变
            vh_res = re.match(r'-?\d+(pt|mm|bp|cm|em|ex|in)',seg[seg_idx:])
            if vh_res:
                new_seg += vh_res.group(0)
                seg_idx += vh_res.span()[1]
                continue
            # invisible符号：_, ^, { 等：不加颜色，保留原样
            invisible_res = re.match(r'(\{\[\})|_|\^|\||\{|\}|\$|\\\\|\\$|\[.*\]|&|%|\s+|\*|~|#|\[|\]|(natexlab)|(urlprefix)|\\(!|,|;)',seg[seg_idx:])
            if invisible_res:
                # 上下标没加括号：后面必为一个字母或希腊字母，这时最好加上括号
                if seg[seg_idx] in ['_','^'] and seg_idx < len(seg)-1 and seg[seg_idx+1] != '{':
                    greek_res = re.match(r'\\[A-Za-z]+',seg[seg_idx+1:])
                    if greek_res:   # 希腊字母
                        new_seg += seg[seg_idx]+'{'+greek_res.group(0) + '}'
                        seg_idx += 1+greek_res.span()[1]
                    else:   # 英文字母
                        new_seg += seg[seg_idx]+'{'+seg[seg_idx+1] + '}'
                        seg_idx += 2
                else:
                    new_seg += invisible_res.group(0)  
                    seg_idx += invisible_res.span()[1] 
                continue
            # visible符号：字母、数字、运算符、转义字符等: 加颜色
            visible_res = re.match(r'(\.*\s*[A-Za-z]+)|(\d+(,|\.)*)+|\+|-|/|>|<|=|\(|\)|,|\.|@|;|!|\?|\:|\'|\"|`|(\\[^\\])',seg[seg_idx:])
            if visible_res:
                new_seg += colored_word(visible_res.group(0))
                seg_idx += visible_res.span()[1]
                continue
            
            else: # 理论上不应该到这里，先保留原样
                print(f'unhandled char:"{seg[seg_idx:]}"')
                new_seg += seg[seg_idx]
                seg_idx += 1
                continue
                
         
        texts[j] = new_seg   
        
    color_text = ' '.join(texts)
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
         

if __name__ == '__main__':
    import sys
    source_path = sys.argv[1]
    colored_file(source_path)


