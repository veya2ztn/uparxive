from uparxive.tex_to_xml.standalize_tex import *
from uparxive.lougat.color_tex import *
from uparxive.xml_to_json.utils import better_latex_sentense_string
import regex
import numpy as np
from pdf2image import convert_from_path
from PIL import Image, ImageChops
import subprocess
import regex
from ..batch_run_utils import BatchModeConfig, dataclass
import latex2mathml.commands as commands

@dataclass
class PrepareColorFulConfig(BatchModeConfig):
    verbose : bool = False
    redo : bool = False
    mode : str = 'generate_table_image'
    do_colorful : bool = True
    task_name = 'prepare_colorful'
    force_redo: bool = False
    try_color_table: bool = False
    add_bbl:bool = False
    color_mode:str ='colorful_table_figure'

    def __post_init__(self):
        if not self.do_colorful:
            print("please in current version, please force colorful the tex and adjust in color_mode")

def remove_footnotes(text):
    result = []
    i = 0
    while i < len(text):
        if text[i:i+9] == '\\footnote':
            # Skip past \footnote
            i += 9
            if i < len(text) and text[i] == '{':
                brace_count = 1
                i += 1
                # Skip content within the braces
                while i < len(text) and brace_count > 0:
                    if text[i] == '{':
                        brace_count += 1
                    elif text[i] == '}':
                        brace_count -= 1
                    i += 1
        else:
            result.append(text[i])
            i += 1
    return ''.join(result)

def format_latex_content(content):
    # Split content by multiple newline characters to identify paragraphs
    paragraphs = re.split(r'\n\s*\n', content)
    
    # Format each paragraph into a single line by replacing single newlines with spaces
    formatted_paragraphs = [re.sub(r'\n', ' ', paragraph).strip() for paragraph in paragraphs]
    
    return formatted_paragraphs

def read_content_with_input(latex_file_path):
    rootpath      = os.path.dirname(latex_file_path)
    with open(latex_file_path, 'r', encoding='utf-8') as file:
        content_lines = [t.strip() for t in file]
    #input_pattern = re.compile(r'\\input{(.+?)}')
    input_pattern = re.compile(r'\\input\s*{?([^{}\s]+)}?')
    def include_file(match):
        file_name = match.group(1)
        if not file_name.endswith('.tex'):
            file_name = file_name+'.tex'
        file_path = os.path.join(rootpath,file_name)
        try:
            return read_content_with_input(file_path)
        except FileNotFoundError:
            #logging.warning(f"Warning: '{file_name}' not found.")
            return ''
    
    new_content_lines = [input_pattern.sub(include_file, line) for line in content_lines]
    return "\n".join(new_content_lines)

def clean_latex_content(content):
    # Patterns to remove non-visible LaTeX commands
    patterns_to_remove = [
        r'\\textcolor(\{(?:[^{}]++|(?1))*\})',
        r'\\color(\{(?:[^{}]++|(?1))*\})',
        r'\\label(\{(?:[^{}]++|(?1))*\})',
        r'\\vspace.*?(\{(?:[^{}]++|(?1))*\})',
        r'\\pageref(\{(?:[^{}]++|(?1))*\})',
        #r'%.*?\n',  # Remove comments
        r'\\hspace(\{(?:[^{}]++|(?1))*\})',
        r'\\href(\{(?:[^{}]++|(?1))*\})',
        r'\\email(\{(?:[^{}]++|(?1))*\})',
        r'\\subjclass(\[.*?\])?\{(?:[^{}]++|(?1))*\}',
        #r'\\affiliation(\{(?:[^{}]++|(?1))*\})',
        r'\\newline',
        r'\\newpage',
        r'\\pagebreak',
        #r'\\footnote(\{(?:[^{}]++|(?1))*\})',
    ]

    # Remove standard patterns
    for pattern in patterns_to_remove:
        content = regex.sub(pattern, '\n', content, flags=regex.DOTALL)
    
    content = content.replace('\\newblock',"").replace("\\em","").replace('\\~',' ')
    return content

def replace_ref(content, reference_map):
    patterns_to_remove = [
        r'\\cite(\{(?:[^{}]++|(?1))*\})',
        r'\\citet(\{(?:[^{}]++|(?1))*\})',
        r'\\citep(\{(?:[^{}]++|(?1))*\})',
        r'\\newcite(\{(?:[^{}]++|(?1))*\})',
        r'\\ref(\{(?:[^{}]++|(?1))*\})',
        r'\\pageref(\{(?:[^{}]++|(?1))*\})',

        r'\\eqref(\{(?:[^{}]++|(?1))*\})',
        
    ]
    def replace_cite(match):
        #print(match)

        keywords= match.group(1).split(',')
        
        output = []
        for keyword in keywords:
            keyword = keyword.strip().strip('\{\}')
            if keyword in reference_map:
                output.append(reference_map[keyword])
            else:
                pass
                    #print(keyword)
        

            
        if len(output)==0:return "[?]"
        if len(output)>4:
            output = output[0].rstrip(')]') + '-' + output[-1].lstrip('([')
        return "".join(output)
        
        
    for pattern in patterns_to_remove:
        content = regex.sub(pattern, replace_cite, content, flags=regex.DOTALL)

    return content

def filter_out_preamble_block(content, redefine_commands=None, layout_commands=None, end="\n"):
    assert redefine_commands is not None
    assert layout_commands is not None
    for cmd in redefine_commands:
        content = content.replace(cmd,"\n"+cmd)
    included_commands = redefine_commands + layout_commands
    brace_counts = {'curly': 0, 'square': 0, 'round': 0}
    
    commented_content = []
    
    # Helper function to check if all braces are balanced
    def braces_balanced(brace_counts):
        return all(count == 0 for count in brace_counts.values())

    # Define commands to exclude from commenting
    
    
    lines = [re.sub(r"%.*", "", line) for line in content.splitlines(True) if  line.strip()]
    lines = [line for line in lines if  line.strip()]
    elements =[]
    preamble_block=[]
    layerout_block=[]
    element  =""
    in_command = False
    for i in range(len(lines)):
        line = lines[i]  # Keep linebreaks

        if line.strip().startswith('%'):
            continue
        
        if not in_command:
            if included_commands is None:
                in_command = "should_comment" if line.lstrip().startswith("\\") else "donot_comment"
            else:
                if any(line.lstrip().startswith(cmd) for cmd in included_commands):
                    in_command = "should_comment"
                else:
                    in_command = "donot_comment"

        # If we are inside an excluded command, count braces
        if in_command:
            brace_counts['curly']  += line.count('{') - line.count('}')
            brace_counts['square'] += line.count('[') - line.count(']')
            brace_counts['round']  += line.count('(') - line.count(')')

            # If all braces are balanced, the command has ended
            is_commandQ = braces_balanced(brace_counts) and (i==len(lines)-1 or lines[i+1].strip()[0]=='\\')
            if is_commandQ:
                in_command = f"end_of_comment.{in_command}"
        #print(brace_counts)
        # Add line to commented_content
        element += line.rstrip('\n') + end

        if in_command.startswith("end_of_comment"):
            COMMENTQ=not in_command.endswith('donot_comment')
            
            if COMMENTQ:
                if any(element.lstrip().startswith(cmd) for cmd in layout_commands):
                    elements.append("\n%%-->layerout<--%%"+element+'\n')
                    layerout_block.append(element)
                else:
                    preamble_block.append(element)
            else:
                elements.append(element)
            element=""
            in_command = False

    return '\n'.join(elements), "\n".join(preamble_block), layerout_block


def native_parser_latex_string(text):
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
                
                new_seg += word
                seg_idx += tag_res.span()[1]
                logging.debug("tag_res:",word)
                continue
            # (x,y)：坐标，保持不变
            
            new_seg += seg[seg_idx]
            seg_idx += 1 
        texts[j] = new_seg
    return "\n".join(texts)
         




def blockwise_content(content, blocks= [
        (r'\\documentclass.*?\\begin{document}', 'preamble'),
        (r'\\begin{abstract}.*?\\end{abstract}', 'abstract'),
        (r'\\begin{fig.*?\\end{fig.*?}', 'figure'),
        (r'\\begin{table.*?\\end{table.*?}', 'table'),
        (r'\\begin{tabular.*?\\end{tabular.*?}', 'table'),
        
        (r'\\begin{algorithm}.*?\\end{algorithm}', 'algorithm'),
        (r'\\begin{algorithm\*}.*?\\end{algorithm\*}', 'algorithm'),
        (r'\\begin{Verbatim.*?\\end{Verbatim.*?}', 'Verbatim'),
        (r'\\begin{widetext.*?\\end{widetext.*?}', 'equation'),
        (r'\\begin{flalign.*?\\end{flalign.*?}', 'equation'),
        
        #(r'\\begin{center.*?\\end{center.*?}', 'center'),
        (r'\\begin{thebibliography.*?\\end{thebibliography.*?}', 'thebibliography'),
        (r'\\begin{equation.*?\\end{equation.*?}', 'equation'),
        (r'\\begin{eqnarray.*?\\end{eqnarray.*?}', 'equation'),
        (r'\\\[.*?\\\]', 'equation'),
        (r'\n\$\$.*?\$\$', 'equation'),
        (r'\\begin{align.*?\\end{align.*?}', 'equation'),
        (r'\\begin{multline.*?\\end{multline.*?}', 'equation'),

        # (r'\\chapt.*?\n', 'chapter'),
        # (r'\\sec.*?\n', 'section'),
        # (r'\\subsec.*?\n', 'subsection'),
        # (r'\\subsub.*?\n', 'subsubsection'),
        
    ]):
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

def better_document_class(content):
    def replace_document_class(match):
            return f"% {match.group(0)}" + "\n"+"\\documentclass[amsmath,amssymb,color,hyperref,cite]{revtex4-1}"

    if "\\documentclass" in content:
        content = re.sub(r'\\documentclass(\[[^\]]*\])?\{.*\}', replace_document_class, content)
    elif "\\documentstyle" in content:
        content = re.sub(r'\\documentstyle(\[[^\]]*\])?\{.*\}', replace_document_class, content)
    return content

def env_partition(content):
    """
    Partition the content based on LaTeX environments and sections.
    Assumes that environments are properly closed and that each \begin and \end
    are on separate lines from content.
    """
    def braces_balanced(brace_counts):
        return all(count == 0 for count in brace_counts.values())

    included_commands = [
        '\\begin', '\\end', '\\section', '\\subsection', 
        '\\subsubsection', '\\chapter', '\\paragraph', '\\subparagraph',
        '\\def','\\Declare', '\\define',
        '\\newcommand', '\\let',
        '\\def', '\\usepackage', "\\affiliation",
        '\\eqnobysec','\\newenvironment', '\\pdfoutput',
        '\\newtheorem',
        '\\providecommand',
        '\\renewcommand', 
        '\\documentclass',"\\global",'\\setlength','\\newcolumntype',
        '\\twocolumn',"\\if","\\fi","\\thispagestyle","\\pagerange","\\setcounter","\\makebox","\\global"
    ]

    lines = content.splitlines(True)
    elements = []
    element = ""
    in_command = False
    brace_counts = {'curly': 0, 'square': 0, 'round': 0}

    for i, line in enumerate(lines):
        line_strip = line.strip()
        if line_strip.startswith('%'):
            continue  # Skip commented lines

        # Update brace counts
        brace_counts['curly'] += line.count('{') - line.count('}')
        brace_counts['square'] += line.count('[') - line.count(']')
        brace_counts['round'] += line.count('(') - line.count(')')

        # Check if the line starts any included commands
        if any(line_strip.startswith(cmd) for cmd in included_commands):
            if not in_command:
                # Flush any existing text elements
                if element.strip():
                    elements.append(['text', element])
                    element = ""
                in_command = True

        if in_command:
            element += line
            # Check if braces are balanced to determine if the command has ended
            if braces_balanced(brace_counts):
                elements.append(['env', element])
                element = ""
                in_command = False
                brace_counts = {'curly': 0, 'square': 0, 'round': 0}  # Reset brace counts
        else:
            element += line.rstrip('\n')+'\n'

    if element.strip():
        # Append any remaining text as a text block
        elements.append(['text', element])

    return elements


def parse_def(latex_content, command=r'\\def', commands={}):
    # Pattern to extract \def command
    pattern = re.compile(command + r'\\(\w+)([^\{]*)\{')
    
    # Find the match for the initial part (name and parameters)
    match = pattern.search(latex_content)
    if not match:
        return commands  # No valid \def found
    
    # Extract command name
    command_name = match.group(1)
    
    # Parse parameters from the parameter part
    parameter_part = match.group(2)
    num_params = 0
    params_pattern = re.compile(r'#(\d+)')
    params = params_pattern.findall(parameter_part)
    if params:
        num_params = max(map(int, params))  # Get the highest parameter number used
    
    # Calculate the start of the definition by finding the next opening brace after the pattern match
    start_of_definition = latex_content.find('{', match.end()-1) + 1
    end_of_definition = start_of_definition
    brace_count = 1
    
    # Count braces to find the corresponding closing brace
    while end_of_definition < len(latex_content) and brace_count > 0:
        if latex_content[end_of_definition] == '{':
            brace_count += 1
        elif latex_content[end_of_definition] == '}':
            brace_count -= 1
        end_of_definition += 1
    
    # Extract the definition enclosed in the outermost braces
    definition = latex_content[start_of_definition:end_of_definition-1]
    #print(f"def=> {command_name} ==> {definition}")
    
    def replace_param_dollars(match):
        # Extract the full match which includes the dollar signs and parameters
        full_match = match.group(0)
        # Replace starting and ending dollar signs
        replaced = re.sub(r'^\$', '<dollarsign>', full_match)
        replaced = re.sub(r'\$$', '<dollarsign>', replaced)
        return replaced
    
    # Apply the replacement to the definition
    param_regex = r'\$(#\d+)+\$'
    definition = re.sub(param_regex, replace_param_dollars, definition)
    
    # Store the command in the dictionary
    commands[f"\\\\{command_name}"] = {
        "params": num_params,
        "definition": definition
    }
    return commands


def parse_newcommand_old(latex_content, command=r'\\newcommand', commands={}):
    # Pattern to extract command name, optional parameters
    pattern = re.compile(command+r'(?:{\\(\w+)}|\\(\w+))(\[\d+\])?')
    
    # Find the match for the initial part (name and optional parameters)
    match = pattern.search(latex_content)
    if not match:
        return commands  # No valid \newcommand found

    # Extract command name and number of parameters
    command_name = match.group(1) if match.group(1) else match.group(2)
    num_params   = int(match.group(3).strip('[]')) if match.group(3) else None
    
    # Remove the matched content to leave behind the definition
    # Calculate the start of the definition by adding the length of the matched part to its start index
    start_of_definition = match.end()
    definition = latex_content[start_of_definition:].strip()
    
    # Assuming the definition is correctly enclosed in braces, extract the content within the first level of braces
    brace_counts = {'curly': 0, 'square': 0, 'round': 0}
    definition = definition #[1:-1]  # definition must start with '{' and end with '}'
    assert definition[0] == '{', f"you get a defination = {definition} from {latex_content}"
    for i in range(len(definition)):
        if definition[i] =='{':
            brace_counts['curly'] += 1
        elif definition[i] == '}':
            brace_counts['curly'] -= 1
        if brace_counts['curly'] == 0:
            
            break
    definition = definition[:i+1]
    
    definition = apply_macros(definition, commands)
    def replace_param_dollars(match):
        # Extract the full match which includes the dollar signs and parameters
        full_match = match.group(0)
        # Replace starting and ending dollar signs
        replaced = re.sub(r'^\$', '<dollarsign>', full_match)
        replaced = re.sub(r'\$$', '<dollarsign>', replaced)
        return replaced

    # Apply the replacement to the definition
    param_regex = r'\$(#\d+)+\$'
    definition = re.sub(param_regex, replace_param_dollars, definition)
    return commands|{r"\\"+command_name: {
        "params": num_params,
        "definition": definition
    }}


def parse_newcommand(latex_content, command=r'\\newcommand', commands={}):
    # Improved pattern to extract command name, optional parameters, and their default values
    pattern = re.compile(command + r'{\\(\w+)}(\[\d+\](?:\[[^\]]+\])?)?{')
    
    # Find the match for the initial part (name and optional parameters)
    match = pattern.search(latex_content)
    if not match:
        return commands  # No valid \newcommand found

    # Extract command name
    command_name = match.group(1)
    
    # Initialize parameter count and default value
    num_params = 0
    default_value = None
    
    # Check if there are optional parameters
    if match.group(2):
        params = match.group(2)
        if params.count('[') == 2:
            num_params = int(params[1:params.find(']')])
            default_value = params[params.find('[')+1+len(str(num_params))+1:-1]
        else:
            num_params = int(params[1:-1])

    # Calculate the start of the definition by finding the next opening brace after the pattern match
    start_of_definition = latex_content.find('{', match.end()-1) + 1
    end_of_definition = start_of_definition
    brace_count = 1

    # Count braces to find the corresponding closing brace
    while end_of_definition < len(latex_content) and brace_count > 0:
        if latex_content[end_of_definition] == '{':
            brace_count += 1
        elif latex_content[end_of_definition] == '}':
            brace_count -= 1
        end_of_definition += 1

    # Extract the definition enclosed in the outermost braces
    definition = latex_content[start_of_definition:end_of_definition-1]
    #print(f"recommand=> {command_name} ==> {definition}")
    # Store the command in the dictionary
    commands[f"\\\\{command_name}"] = {
        "params": num_params,
        "default": default_value,
        "definition": definition
    }
    return commands

def parse_redefine(commands_str,commands = {}):
    
    lines = commands_str.strip().splitlines()
    for line in lines:
        #print(line)
        if line.startswith('\\newcommand'):
            commands = parse_newcommand(line,r'\\newcommand',commands = commands)

        elif line.startswith('\\def'):
            commands = parse_def(line,commands = commands)
    
    return commands


def apply_macros(latex_text, commands):
    # Replace each command in the text
    
    for command, details in commands.items():

        if details['definition'] is None:continue
        if not details['params']:
            # Direct replacement if there are no parameters
            pattern = regex.escape(command[1:]) + r'(?=\s|\Z|\\|\_|\^|\}|\]|\)|\$)'
            #print(pattern,details['definition'])
            latex_text = re.sub(pattern, details['definition'].replace("\\", "\\\\"), latex_text)
        else:
            
            # Replacement with parameter handling
            def replacer(match):
                # Replace each parameter occurrence
                content = details['definition']
                for i in range(details['params']):
                    param_match = match.group(i + 1)  # Get the i-th parameter group
                    # Clean and unbrace the parameter content
                    cleaned_param = param_match[1:-1] if len(param_match) > 2 else param_match
                    
                    content = content.replace(f"#{i + 1}", cleaned_param)
                return content
            
            # Create a regex pattern that matches this command followed by its parameters in nested braces
            brace_pattern = r'(\{(?:[^{}]++|(?1))*\})'
            full_pattern  = regex.escape(command[1:]) + brace_pattern * details['params']
            latex_text    = regex.sub(full_pattern, replacer, latex_text)
    
    return latex_text

def expand_macro(contents):
    latex_blocks = blockwise_content(contents, blocks=[(r'\\documentclass.*?\\begin{document}', 'preamble')])
    redefine_commands = ['\\def','\\Declare', '\\define',
                         '\\newcommand', '\\let',
                         '\\def', '\\usepackage',
                         '\\eqnobysec','\\newenvironment',
                         '\\newtheorem',
                         '\\providecommand',
                         '\\renewcommand', 
                         '\\documentclass',"\\global"
                        ]
    new_latex_blocks = []
    commands = {}
    for _type, content in latex_blocks:
        if _type == 'preamble':
            for cmd in redefine_commands:
                content = content.replace(cmd,"\n"+cmd)
            _, command_str, _ =  filter_out_preamble_block(content,redefine_commands = redefine_commands,layout_commands = [] )
            #print(command_str)
            commands = parse_redefine(command_str,commands)
            
            # for key,val in commands.items():
            #     print(f"{key} => {val}")
            # raise
        elif commands: ### <--- may cause unexcep error when replace math
            
            content = apply_macros(content,commands)
        new_latex_blocks.append(content)
    new_latex_blocks = "\n".join(new_latex_blocks)
    return new_latex_blocks





def process_latex_content(content, collect_preamble=True, color_mode='colorful_table_figure'):
    redefine_commands = ['\\def','\\Declare', '\\define',
                         '\\newcommand', '\\let',
                         '\\def', '\\usepackage',
                         '\\eqnobysec','\\newenvironment',
                         '\\newtheorem',
                         '\\providecommand',
                         '\\renewcommand', 
                         '\\documentclass',"\\global"
                        ]
    relative_layout_commands = ['\\setlength','\\newcolumntype','\\SetArgSty']
    layout_commands = ['\\input','\\twocolumn',"\\if","\\fi"] + relative_layout_commands
 

    latex_blocks = blockwise_content(content)

     
    preamble_content = [""]
    layerout_blocks  = []
    new_blocks = []
    commands={}
    for block_type, block_content in latex_blocks:
        
        # for a,b  in commands.items():
        #     print(a)
        #     print(b)
        # raise
        new_block_content = block_content
        if block_type == 'preamble':
            block_content = block_content.split('\n')
            block_content.insert(-1,r"\usepackage[most]{tcolorbox}")
            ## below for color board for colorfbox
            #block_content.insert(-1,"""\\newcommand{\\colorfbox}[3]{ \\fboxsep=0pt \\fboxrule=1pt \\extractRGB{#2} \\fbox{\\colorbox{#1}{\\strut #3}}}""")
            ## below for color backgroud for colorfbox
            block_content.insert(-1,"""\\newcommand{\\extractRGB}[1]{\\def\\tempa##1,##2,##3\\end{\\definecolor{tempbordercolor}{RGB}{##1,##2,##3} \\color{tempbordercolor}  }\\expandafter\\tempa#1\\end}""")
            
            if color_mode == 'colorful_table_figure':
                block_content.insert(-1,"""\\newcommand{\\colorfbox}[3]{\\definecolor{bgcolor}{RGB}{#2} \\fboxsep=0pt \\fboxrule=0pt \\color{bgcolor} \\fbox{\\colorbox{bgcolor}{\\strut #3}}}""")
                block_content.insert(-1,"""\\newcommand{\colorfboxx}[3]{\n\\definecolor{bgcolor}{RGB}{#2} \n\\begin{tcolorbox}[colback=bgcolor, colframe=bgcolor, coltext=bgcolor] \n\\strut #3  \n\\end{tcolorbox} \n}""")
            elif color_mode == 'virtual_box_table_figure':
                block_content.insert(-1,"""\\newcommand{\\colorfbox}[3]{\\definecolor{bgcolor}{RGB}{255,255,255} \\fboxsep=0pt \\fboxrule=0pt  \\fbox{\\colorbox{bgcolor}{\\strut #3}}}""")
                block_content.insert(-1,"""\\newcommand{\colorfboxx}[3]{ \n\\definecolor{bgcolor}{RGB}{255,255,255} \n\\begin{tcolorbox}[colback=bgcolor, colframe=bgcolor, coltext=black] \n\\strut #3  \n\\end{tcolorbox} \n}""")
            new_block_content = "\n".join(block_content)
            new_blocks.append([block_type, new_block_content])
        
        else:
            _, command_line,_ = filter_out_preamble_block(block_content,redefine_commands=redefine_commands, layout_commands=layout_commands,end=" ")

            commands          = parse_redefine(command_line,commands)
            block_content = apply_macros(block_content, commands)
            if block_type == 'text':
                ##Find the defination commend and add prefix on them
                # new_block_content, command_line,layerout_block = filter_out_preamble_block(block_content,
                #                                                                 redefine_commands=[], 
                #                                                                 layout_commands=layout_commands+redefine_commands+[
                #                                                                     r"\\begin",
                #                                                                     r"\\end"
                #                                                                 ])

                envs_blocks = env_partition(block_content)
                new_blocks.extend(envs_blocks)
                
            else:
                new_blocks.append([block_type, block_content])

        
    return new_blocks,layerout_blocks

def convert_pdf_to_img(pdf_file, dpi=300):
    # Convert PDF to list of images with specified DPI for high resolution
    images = convert_from_path(pdf_file, dpi=dpi)
    return images

def auto_crop_image(image):
    # Convert image to numpy array
    image_np = np.array(image)
    
    # Find all non-white pixels
    non_white_pixels = np.where(np.all(image_np != [255, 255, 255], axis=-1))
    
    # Get the bounds of the non-white pixels
    y_min, y_max = non_white_pixels[0].min(), non_white_pixels[0].max()
    x_min, x_max = non_white_pixels[1].min(), non_white_pixels[1].max()
    
    # Crop the image using PIL
    cropped_image = image.crop((x_min, y_min, x_max, y_max))
    return cropped_image

def trim(image, margin=10):
    """
    Trims the white space around an image and adds a margin.

    :param image: PIL Image object to be trimmed.
    :param margin: Margin size to be added around the trimmed image.
    :return: Cropped PIL Image object with added margin.
    """
    bg = Image.new(image.mode, image.size, (255, 255, 255))
    diff = ImageChops.difference(image, bg)
    bbox = diff.getbbox()
    if bbox:
        # Expand the bounding box by the margin
        bbox = (
            max(0, bbox[0] - margin),  # Left
            max(0, bbox[1] - margin),  # Top
            min(image.size[0], bbox[2] + margin),  # Right
            min(image.size[1], bbox[3] + margin)   # Bottom
        )
        return image.crop(bbox)
    return image

def is_comprehensive_table(val):
    if r"\multirow" in val:return True
    if r"\multicolumn" in val:return True
    if r"\tabincell" in val:return True
    return False

def split_on_first_closure(input_string):
    # Determine which bracket type appears first (either '{' or '[')
    first_brace = regex.search(r"[{}\[\]]", input_string)
    if not first_brace:
        return ("", input_string)  # No brackets found, return empty closure and original string

    # Select pattern based on the first bracket type found
    if first_brace.group() in '{':
        pattern = r"\{(?:[^{}]*|(?R))*\}"
    elif first_brace.group() in '[':
        pattern = r"\[(?:[^\[\]]*|(?R))*\]"

    # Search for the first full balanced bracket expression
    match = regex.search(pattern, input_string)
    if match:
        # 'a' is the matched closure, 'b' is the remainder of the string after the closure
        a = match.group(0)
        b = input_string[match.end():]
        return (a, b)
    else:
        # If no complete match is found, return empty 'a' and original string as 'b'
        return ("", input_string)

def identity(x,*args,**kargs):
    return x

def replace_tabular_content(latex_content):
    # Regular expression pattern to find tabular environments and their content.
    pattern = r"\\begin{tabular}(\[[^\]]*\])?{([^}]*)}\n(.*)\\end{tabular}"
    
    # Function to apply colorful_fun to the content of each tabular environment found.
    def replacer(match):
        tabular_options = match.group(1) or ""  # Optional positional arguments
        tabular_format  = match.group(2)         # Format argument of the tabular
        tabular_content = match.group(3)        # Content of the tabular
        new_content     = colored_text(tabular_content)
        return f"\\begin{{tabular}}{tabular_options}{{{tabular_format}}}{new_content}\\end{{tabular}}"
    
    # Use re.sub to replace the content of all tabular environments found in the input string.
    updated_latex_content = re.sub(pattern, replacer, latex_content, flags=re.DOTALL)
    return updated_latex_content


def replace_equation_content(text):
    raise
    # This regular expression uses named groups to separately capture the opening tag, content, and closing tag
    patterns = [r'(\\begin{equation\*?})(.*?)(\\end{equation\*?})',
                r'(\\begin{eqnarray\*?})(.*?)(\\end{eqnarray\*?})',
                r'(\\begin{align\*?})(.*?)(\\end{align\*?})',
                r'(\\begin{multline\*?})(.*?)(\\end{multline\*?})',
                r'(\\\[)(.*?)(\\\])',
                r'(\$\$)(.*?)(\$\$)',
                
                ]

    # Function to replace found pattern
    def replace_content(match):
        # Extracting the parts using the named groups
        opening_tag = match.group(1)
        content     = match.group(2)
        closing_tag = match.group(3)
        
        new_content = colored_word("\n"+content.strip()+'\n')
        
        # Constructing the new equation string
        return '{}\n{}\n{}'.format(opening_tag, new_content, closing_tag)
    
    # Using re.sub to replace all occurrences in the text
    for pattern in patterns:
        text = re.sub(pattern, replace_content, text, flags=re.DOTALL)
    #result = re.sub(pattern, replace_content, text, flags=re.DOTALL)
    return text

def caption_replacement(match):
    return '\\caption{' + colored_text(better_latex_sentense_string(clean_latex_content(match.group(1)[1:-1]))) + '}'

def remove_out_the_caption(content, replaced_element="\n"):
    pattern = r'\\caption(\{(?:[^{}]++|(?1))*\})'
    captions = regex.findall(pattern, content, flags=regex.DOTALL)
    content  = regex.sub(pattern, replaced_element, content, flags=regex.DOTALL)
    return content,captions


def remove_affiliation_lines(text):
    # Split the text into lines
    lines = text.splitlines()
    # Filter out lines that start with \affiliation
    filtered_lines = [line for line in lines if not line.lstrip(r"\\").startswith(r'affiliation')]
    # Join the remaining lines back into a single string
    result_text = '\n'.join(filtered_lines)
    return result_text


def get_pdf_path(path):
    aaa = path.lower()
    if aaa.endswith('.png') or aaa.endswith('.jpg') or aaa.endswith('.jpeg') or aaa.endswith('.gif'):return path
    dir, name= os.path.split(path)
    name = name.split('.')
    if len(name)==1:
        name = name
    else:
        name = name[:-1]
    name = ".".join(name)
    name = name+'.pdf'
    return os.path.join(dir,name)

def replace_function(match):
    options = match.group(1) if match.group(1) is not None else ""
    old_path = match.group(2)
    #new_path = get_pdf_path(old_path)
    new_path = old_path ### lets do not modify
    #return r"\begin{tcolorbox}[colframe=blue, colback=white, boxsep=0pt, left=0pt, right=0pt, top=0pt, bottom=0pt]" +"\n" + f'\\includegraphics{options}{{{new_path}}}' + "\n" + r"\end{tcolorbox}"
    return add_color_box(f'\\includegraphics{options}{{{new_path}}}')
     
def add_color_box_tabular(latex_content):
    # Regular expression pattern to find tabular environments and their content.
    pattern = r"\\begin{tabular}(\[[^\]]*\])?{([^}]*)}\n(.*)\\end{tabular}"
    
    # Function to apply colorful_fun to the content of each tabular environment found.
    def replacer(match):
        tabular_options = match.group(1) or ""  # Optional positional arguments
        tabular_format  = match.group(2)         # Format argument of the tabular
        tabular_content = match.group(3)        # Content of the tabular
        new_content =  f"\\begin{{tabular}}{tabular_options}{{{tabular_format}}}{tabular_content}\\end{{tabular}}"
        #new_content =  r"\begin{tcolorbox}[colframe=blue, colback=white, boxsep=0pt, left=0pt, right=0pt, top=0pt, bottom=0pt]" +"\n" + new_content + "\n" + r"\end{tcolorbox}"
        return add_color_box(new_content)

    # Use re.sub to replace the content of all tabular environments found in the input string.
    updated_latex_content = re.sub(pattern, replacer, latex_content, flags=re.DOTALL)
    return updated_latex_content

def add_color_box(content):
    # Regular expression pattern to find tabular environments and their content.
    color = get_one_color()
    return r"\colorfbox{white}{"+color+"}{" +"\n" + content + "\n" + r"}"

def add_color_box2(content):
    # Regular expression pattern to find tabular environments and their content.
    color = get_one_color()
    return r"\colorfboxx{white}{"+color+"}{" +"\n" + content + "\n" + r"}"


def wrap_tables_with_tcolorbox(content, names,captions_string, boxfunction=add_color_box):
    """
    Wraps specified LaTeX environments in a tcolorbox environment to enhance their visual presentation.

    Args:
    content (str): The LaTeX document content containing environments to wrap.
    names (list): A list of environment names to wrap.

    Returns:
    str: Modified LaTeX content with specified environments wrapped in tcolorbox environments.
    """
    # Create a regex pattern dynamically based on the provided environment names
    name = '|'.join(re.escape(b) for b in names) if isinstance(names, list) else names
    pattern = re.compile(
        r'\\begin{(?P<env>' + name + r'\*?)}(\[.*?\])?(?P<content>.*?)\\end{\1}',
        re.DOTALL
    )

    def wrap_with_tcolorbox(match):
        start_tag_with_params = match.group(0).split(match.group('content'), 1)[0]  # Includes \begin{...} with params
        table_content = match.group('content')  # The actual content inside the environment
        end_tag = match.group(0).split(match.group('content'), 1)[1]  # \end{...}

        # Constructing the new content wrapped in tcolorbox
        wrapped_table = f"{start_tag_with_params}\n"+ boxfunction(table_content) + f"\n{captions_string}\n{end_tag}\n"
        #wrapped_content = f"{start_tag_with_params}\n\\begin{{tcolorbox}}[colframe=blue, colback=white, sharp corners]\n{table_content}\n\\end{{tcolorbox}}\n{end_tag}"
        return wrapped_table


    # Apply the wrapping function to all found blocks
    modified_content = pattern.sub(wrap_with_tcolorbox, content)
    return modified_content


def colorful_inside_brace(content, commend,colorful_fun ):
    return regex.sub(r'\\'+commend+r'(\{(?:[^{}]++|(?1))*\})',  
                                 lambda match: '\\'+ commend + '{' + colorful_fun(better_latex_sentense_string(clean_latex_content(match.group(1)[1:-1]))) + '}', 
                                 content, flags=regex.DOTALL)

def remove_inside_brace(content, commend,colorful_fun ):
    return regex.sub(r'\\'+commend+r'(\{(?:[^{}]++|(?1))*\})',   "",  content, flags=regex.DOTALL)

def lets_deal_with_text_in_math(val):
    # Define the regex pattern to match \text{...} or \mbox{...}
    pattern = r'\\(text|mbox|hbox|textit)\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}'
    
    # Replacement function that processes the match
    def replacement(m):
        # m[1] will be either "text" or "mbox"
        # m[2] contains the content inside the brackets
        inner_content = m[2].replace("$", "<dollarsign>")
        return f"\\{m[1]}{{{inner_content}}}"

    # Perform the substitution
    val = re.sub(pattern, replacement, val, flags=re.DOTALL)
    return val

def deal_with_one_block_with_math(val, colorful_fun):
    new_val = []
    val = lets_deal_with_text_in_math(val) # in case for those $\text{$d$ }$
    string_and_math_blocks = blockwise_content(val, blocks=[(r'(?<!\\)\$.*?(?<!\\)\$', 'math')])
    for block_type, block_content in string_and_math_blocks:
        if block_type == 'math':
            if colorful_fun != identity:
                block_content = "\n"+colored_text_math(better_latex_sentense_string(block_content)).strip()+'\n' 
        else:
            lines = format_latex_content(block_content)
            lines = [clean_latex_content(better_latex_sentense_string(line)) for line in lines]
            new_lines = []
            for line in lines:
                if line.lstrip().startswith('%%-->layerout<--%%'):
                    new_lines.append(line.replace('%%-->layerout<--%%',''))
                elif line.lstrip().startswith('%'):
                    new_lines.append(line)
                else:
                    new_lines.append(colorful_fun(line))
            block_content = "\n\n".join(new_lines)
        block_content = block_content.replace("<dollarsign>","$")
        new_val.append(block_content)
    return " ".join(new_val)

from uparxive.deal_with_empty_reference.deal_with_ref_complete_with_bbl import parse_bbl_string_to_plain, bbl_file, chardet


def remove_the_bib(tex_content):
    bib_pattern = r'\\bibliography{[^}]+}'
    # Replace the \bibliography command with the contents of bbl_content
    isusebiblio = re.search(bib_pattern, tex_content)

    if isusebiblio:
        # Replace the \bibliography command with the contents of bbl_content
        tex_content = re.sub(bib_pattern, "\n", tex_content)
    return tex_content

def add_bbl_content(tex_content,tex_file):
    if "\\bibliography" not in tex_content:
        return tex_content
    tex_fold, tex_name = os.path.split(tex_file)
    tex_name = tex_name[:-4]
    bbl_path = os.path.join(tex_fold,bbl_file(tex_name))
    if not os.path.exists(bbl_path):
        return tex_content
    with open(bbl_path, "rb") as file:
        bbl_content = file.read()
        encoding = chardet.detect(bbl_content)["encoding"]
    bbl_content=[]
    with open(bbl_path,'r', errors='ignore',encoding=encoding ) as ffff:
        for line in ffff:
            bbl_content.append(line.strip().rstrip('%'))
    
    
    
    bbl_content = '\n'.join(bbl_content)
    bbl_content = bbl_content
    if "providecommand" in bbl_content:
        return remove_the_bib(tex_content)
    #bbl_content = parse_bbl_string_to_plain(bbl_content)
    
    if "begin{thebibliography}" not in bbl_content:
        bbl_content = "\\begin{thebibliography}[99]\n" + bbl_content + "\n\\end{thebibliography}"
    bib_pattern = r'\\bibliography{[^}]+}'
    # Replace the \bibliography command with the contents of bbl_content
    isusebiblio = re.search(bib_pattern, tex_content)

    if isusebiblio:
        # Replace the \bibliography command with the contents of bbl_content
        tex_content = re.sub(bib_pattern, lambda match: bbl_content, tex_content)
    return tex_content

def remove_author_optional(latex_content):
    pattern = r'\\author(\[.*?\])?'
    replacement = r'\\author'
    modified_content = re.sub(pattern, replacement, latex_content)
    return modified_content

def preprocess_latex_content(content):
    content = remove_author_optional(content)

    # content =  content.replace('\\em ',' ')
    content =  re.sub(r'\\begin\s+\{', r'\\begin{', content)
    content =  re.sub(r'\\end\s+\{', r'\\end{', content)
    return content

def formularize_latex(file_path, colorful_fun,args:PrepareColorFulConfig):
    force_redo = args.force_redo
    reference_map_path = os.path.join(os.path.dirname(file_path),'uparxive',"reference_map.json")
    if os.path.exists(reference_map_path):
        with open(reference_map_path,'r') as f:
            origin_reference_map = json.load(f)
            reference_map = {}
            for k,reflabels in origin_reference_map.items():
                k = k.replace('LABEL:','')
                ref_order = {'reference':0, 'equation':1, 'figure':2, 'table':3, 'section':4}
                reflabels = sorted(reflabels,key=lambda x: ref_order.get(x[0].lower(),6))
                ref_type, reftags = reflabels[0]
                reftags = reftags.strip('[]()')
                # if ref_type.lower().startswith('missing'):
                #     continue
                ### even the tag is missing, we still add it, in this case, the reference is not aligned
                if ref_type.lower() == 'reference':
                    reftags = f"[{reftags}]"
                else:
                    reftags = f"({reftags})"
                reference_map[k] = reftags
            #for k,v in reference_map.items(): print(f"{k}==>{v}")
    else:
        reference_map = {}
    content = read_content_with_input(file_path)
    
    lines_without_comments = read_the_tex_file_into_memory_without_comment(content, use_content=True)
    lines_without_comments = [line.strip()+'\n' for line in lines_without_comments]
    content = "".join(lines_without_comments)
    if args.mode == 'judge_element':
        if """\\begin{algorithm}""" in content or """\\begin{algorithm*}""" in content or """\\begin{algorithmic}""" in content:
            return [],True
        else:
            return [],False
    content = replace_ref(content, reference_map=reference_map)
    if args.add_bbl:
        content = add_bbl_content(content,file_path)
    else:
        content = remove_the_bib(content)
    #content = expand_newcommand_in_latex(content)
    content = content.replace("\\tableofcontents", "") ### we can not handle content
    #content = expand_macro(content)
    
    content = expand_macro(content) # <-- this is needed since the \begin environment can also be defined in the newcommand
    content = preprocess_latex_content(content)

    latex_blocks,layerout_blocks = process_latex_content(content,False,args.color_mode)
    output = []
    errortable_path = []
    table_order = 0

    for key,val in latex_blocks:
        output.append(f"%vvvvvvvvvvvvvvvvvvvvvvv {key} vvvvvvvvvvvvvvvvvvvvvvvvv")
        
        if key in ['preamble','env']:
            for commend in ['title', 'author', 'address', 'section','subsection', 'subsubsection', 'chapter', 'paragraph', 'subparagraph']:
                val = colorful_inside_brace( val,commend,colorful_fun)
            if key == 'preamble':
                val = "\n".join(re.split(r'\n\s*\n', val))
        if key in ["text","abstract"]:
            #### 
            
            val = val.replace("\\item","\n\\item")
            val = deal_with_one_block_with_math(val, colorful_fun)
            val = remove_affiliation_lines(val)
        if key in ['algorithm','Verbatim']:
            val           = wrap_tables_with_tcolorbox(val,key,"",boxfunction=add_color_box2)
            #val = add_color_box(val) 
        if key in ['table']:
            if not args.try_color_table or is_comprehensive_table(val):
                val, captions = remove_out_the_caption(val)
                captions_string = "\n".join([f"\\caption{caption}" for caption in captions ])
                val           = wrap_tables_with_tcolorbox(val,key,captions_string)
             
                
                #val            = re.sub(r'\\end{table\*?}', lambda m: captions_string + '\n' + m.group(0), val)
                #print(val)
            else:
                blockwised_table_string = blockwise_content(val, [(r'\\begin{tabular}.*?\\end{tabular}', 'tabular')])
                tablelines =[]
                for tk,tv in blockwised_table_string:
                    if tk == 'tabular':
                        tv = tv.split('\n')
                        firstline = tv[0].strip()
                        parameter, remain_content = split_on_first_closure(firstline.strip().replace(r"\begin{tabular}",""))
                        remain_content = remain_content+'\n'+'\n'.join(tv[1:])
                        remain_content = deal_with_one_block_with_math(remain_content, colorful_fun)
                        remain_content = remain_content.replace(r"\end{tabular}","\n"+r"\end{tabular}")
                        tv = r"\begin{tabular}" + parameter + "\n" + remain_content
                    tablelines.append(tv)
                val = "\n".join(tablelines)
       
        if key in ['figure','table']: ### for caption
            val = re.sub(r'\\includegraphics.*?(\[.*?\])?\{(.+?)\}', replace_function, val)
            val,captions = remove_out_the_caption(val, lambda match: '\\caption{' + colorful_fun(better_latex_sentense_string(clean_latex_content(match.group(1)[1:-1]))) + '}')

        if key in ['section','chapter','subsection','subsubsection']:
            val = colorful_fun(val)
        if key in ['equation']:
            #val = colorful_fun(val)
            ### should remove whole the empty line in equation
            val = val.splitlines()
            val = [t.strip() for t in val if len(t.strip())>0]
            val = "\n".join(val)
            val = colored_word(val) if colorful_fun!=identity else val #replace_equation_content(val) if colorful_fun!=identity else val
            #val = add_color_box(val) if colorful_fun!=identity else val 
        if key in ['thebibliography']:
            ### use re split by \bibitem
            lines = []
            for line in  re.split(r'(?=\\bibitem)', val):
                if '\\bibitem' in line:
                    #line = better_latex_sentense_string(clean_latex_content(line))
                    #line = colorful_fun(line)
                    line = deal_with_one_block_with_math(line, colorful_fun)

                
                lines.append(line)
           
            val = "\n".join(lines)
        
        
        output.append(val)
        output.append(f"%^^^^^^^^^^^^^^^^^^^^^^^ {key} ^^^^^^^^^^^^^^^^^^^^^^^^^")
    
    output = "\n".join(output)
    output = output.replace('\\`','')

    return errortable_path, output

def convert_color_tex_into_nocolor_tex(file_path):
    assert '.colorful' in file_path
    filedir, filename = os.path.split(file_path)
    pdfpath = os.path.join(filedir, 'temp', filename[:-4]+'.colorful_all_colored.pdf')
    assert os.path.exists(pdfpath), pdfpath

    no_masked_file_path = file_path[:-4]+'.origin.tex'
    if os.path.exists(no_masked_file_path):
        os.rename(no_masked_file_path, file_path)
    with open(file_path,'r') as f:
        content_ready_for_modification = f.readlines()
    new_content = []
    for line in content_ready_for_modification:
        if line.strip() == "\\newcommand{\\colorfbox}[3]{\\definecolor{bgcolor}{RGB}{#2} \\fboxsep=0pt \\fboxrule=0pt \\color{bgcolor} \\fbox{\\colorbox{bgcolor}{\\strut #3}}}":
            line = "\\newcommand{\\colorfbox}[3]{\\definecolor{bgcolor}{RGB}{255,255,255} \\fboxsep=0pt \\fboxrule=0pt  \\fbox{\\colorbox{bgcolor}{\\strut #3}}}"
        new_content.append(line)
    os.rename(file_path, no_masked_file_path)
    with open(file_path,'w') as f:
        f.write(''.join(new_content))
    return file_path, 'Converted'
#

def get_the_resource_path(file_path, args):
    content = read_content_with_input(file_path)
    lines_without_comments = read_the_tex_file_into_memory_without_comment(content, use_content=True)
    lines_without_comments = [line.strip()+'\n' for line in lines_without_comments ]
    content = "".join(lines_without_comments)
    pattern = r'\\includegraphics(\[.*?\])?\{(.+?)\}'
    # Find all matches of the pattern
    matches = re.findall(pattern, content)
    # Extract the paths (second group in the pattern)
    paths = [match[1] for match in matches]
    foldir= os.path.dirname(file_path)
    abspaths = [os.path.join(foldir, path) for path in paths]
    existedP = [path for path in abspaths if os.path.exists(path)]
    redownload_P = [path for path in abspaths if not os.path.exists(path)]
    redownload_P = [os.path.relpath(path, foldir) for path in redownload_P]

    return redownload_P, 'ResrouceList'

def process_one_file(file_path, args:PrepareColorFulConfig):
    if args.mode == 'remove_color_mask':

        return convert_color_tex_into_nocolor_tex(file_path)
    colorful_fun=colored_text if args.do_colorful else identity
    tag = 'colorful' if args.do_colorful else  'prepare_for_colorful'
    if args.color_mode != 'colorful_table_figure':
        tag += f"_{args.color_mode}"
    filename = os.path.basename(file_path)
    savename = f"{filename[:-4]}.{tag}.tex"
    if args.savepath is None:
        save_path = os.path.join(os.path.dirname(file_path),savename)
    else:
        raise 
        save_path = os.path.join(args.savepath,savename)
    if not os.path.exists(file_path):
        return file_path,'NoSource'
    if os.path.exists(save_path) and not args.redo:
        
        return save_path,'AlreadyDone'
    #tqdm.write(file_path)
    
    errortable_path, output = formularize_latex(file_path,colorful_fun,args)
    if args.mode == 'judge_element':
        status = 'HasAlgorithm' if output else 'NoAlgorithm'
        return file_path,status
    else:
        with open(save_path,'w') as f:
            f.write(output)
        if len(errortable_path)>0:
            return file_path,'Error'
        else:
            
            return  save_path,'Success'
import traceback
def process_one_file_wrapper(args:PrepareColorFulConfig):
    file_path, args = args
    if file_path.endswith('.prepare_for_colorful.tex'):
        file_path = file_path[:-len('.prepare_for_colorful.tex')]+'.tex'
    elif file_path.endswith('.colorful.tex'):
        file_path = file_path[:-len('.colorful.tex')]+'.tex'
    #file_path = file_path.replace('archive_tex','archive_tex.colorful.addbbl')
    try:
        return process_one_file(file_path, args)
    except KeyboardInterrupt:
        raise

    except:
        if args.verbose: 
            
            tqdm.write(f"fail at {file_path}")
            traceback.print_exc()
        if args.debug:
            raise
        return file_path,"Fatal"

