import os,re
from tqdm.auto import tqdm
from ..batch_run_utils import BatchModeConfig, dataclass
from ..utils import get_tex_file_name
@dataclass
class TexStandardConfig(BatchModeConfig):
    modelist = ['clean', 'revtex','nopackage','clean_beta','revtex_beta']
    extra_mode_list = ['prepare_for_color']
    mode : str = 'clean'
    task_name = 'tex_standard'

    @property
    def excluded_commands(self):
        return ['\\input', '\\def','\\Declare', '\\define',
                         '\\abstract','\\newcommand', '\\let',
                         '\\def', '\\usepackage',
                         '\\documentstyle','\\eqnobysec','\\newenvironment',
                         '\\newtheorem',
                         '\\providecommand','\\subtitle',
                         '\\renewcommand', '\\addbibresource',
                         '\\bibliography','\\input','\\documentclass','\\title',"\\global"]
    @property
    def blacklisted_packages(self):
        return set(['morefloats','CJKutf8','floatrow','datetime2','biblatex'])

    def __post_init__(self ):
        assert self.mode in self.modelist + self.extra_mode_list
        import sys
        from pathlib import Path
        module_dir = str(Path(__file__).resolve().parent)
        with open(os.path.join(module_dir,'blacklist_package.alpha'),'r') as f:
            blacklisted_packages2 = set([t.strip() for t in f.readlines()])
        self.blacklisted_packages2 = blacklisted_packages2|self.blacklisted_packages
        with open(os.path.join(module_dir,'blacklist_package.beta'),'r') as f:
            blacklisted_packages3 = set([t.strip() for t in f.readlines()])
        self.blacklisted_packages3 = blacklisted_packages3|self.blacklisted_packages
def read_the_tex_file_into_memory_without_comment(tex_path):
    with open(tex_path, 'r', encoding='utf-8', errors='ignore') as file:
        lines = file.readlines()

    def remove_comments(line):
        # Split the line by % that are not preceded by a backslash
        parts = re.split(r'(?<!\\)%', line)
        # Return the first part, which is before the comment
        parts =  parts[0]  if parts else ''
        if len(parts.strip()) < len(line.strip()) and len(parts.strip())>0:
            parts = parts + '\n'
        return parts

    # Apply the comment removal to each line and preserve lines that are not comments
    lines = [remove_comments(line) for line in lines]
    return lines

def match_nested_braces(s):
    """Match content within nested braces."""
    stack = []
    for i, c in enumerate(s):
        if c == '{':
            stack.append(i)
        elif c == '}' and stack:
            start = stack.pop()
            if not stack:
                yield s[start:i+1]

################################################
############### remove affiliation #############
################################################
def filter_out_affiliation(content,excluded_commands):
    def comment_out_affiliation(match):
        begin_document_line = match.group(1)
        text_to_comment     = match.group(2)
        #print(text_to_comment)
        commented_text = comment_out_preamble_block(text_to_comment, excluded_commands=excluded_commands)
        return begin_document_line + '\n' + commented_text + '\n' + match.group(3)
    pattern = r'(\\begin{document})([\s\S]*?)(\\section\{|\\begin{abstract})'
    cleaned_content = re.sub(pattern, comment_out_affiliation, content)
    return cleaned_content

def filter_out_affiliation2(content,excluded_commands):
    def comment_out_affiliation2(match):
        begin_document_line = match.group(1)
        text_to_comment     = match.group(2)
        commented_text = comment_out_preamble_block(text_to_comment, excluded_commands=excluded_commands)
        return begin_document_line + '\n' + commented_text + '\n' 
    pattern = r'(\\end{abstract})([\s\S]*?)(?=\\section\{|(?<!\\)\n(?!\s*\\))'
    cleaned_content = re.sub(pattern, comment_out_affiliation2, content)
    return cleaned_content


################################################
### remove figures/table (remain caption) ######
################################################
def comment_out_figures(match):
    # Split the matched text into lines
    begin_document_line = match.group(1)
    text_to_comment     = match.group(2)
    
    commented_text      = comment_out_figure_block(text_to_comment, excluded_commands=['psfig', 'includegraphics'])
    return begin_document_line + '\n' + commented_text + '\n'+match.group(3)

def filter_out_figures(content):
    # Define the pattern to match figures blocks
    figure_pattern = r'(\\begin{figure(?:\*)?})([\s\S]*?)(\\end{figure(?:\*)?})'
    # Use the sub function to replace figure blocks with their commented version
    commented_content = re.sub(figure_pattern, comment_out_figures, content)
    return commented_content

def filter_out_tables(content):
    # Define the pattern to match figures blocks
    figure_pattern = r'(\\begin{table(?:\*)?})([\s\S]*?)(\\end{table(?:\*)?})'
    # Use the sub function to replace figure blocks with their commented version
    commented_content = re.sub(figure_pattern, comment_out_figures, content)
    return commented_content

def comment_out_figure_block(content, excluded_commands):
    # Define regex patterns for caption and label
    caption_pattern = r'\\caption\{.*?\}'
    label_pattern = r'\\label\{.*?\}'

    # Match all caption elements taking nested braces into account
    captions = []
    for match in re.finditer(r'\\caption', content, flags=re.DOTALL):
        start_index = match.end()
        brace_content = content[start_index:]
        nested_brace_match = list(match_nested_braces(brace_content))
        if nested_brace_match:
            captions.append(match.group() + nested_brace_match[0])
    
    # Remove all caption elements from the content
    content_without_captions = re.sub(caption_pattern, '', content, flags=re.DOTALL)

    # Find all label elements after removing captions
    labels = re.findall(label_pattern, content_without_captions, flags=re.DOTALL)

    # Remove all label elements from the content
    content_without_captions_and_labels = re.sub(label_pattern, '', content_without_captions, flags=re.DOTALL)

    # Combine the captions and labels back into the content (optional)
    # Here I am assuming you want them at the beginning of the content, but you can place them wherever you need
    remain = content_without_captions_and_labels
    ahead = ["%" + line for line in content_without_captions_and_labels.splitlines()]
    ahead = "\n".join(ahead)
    processed_content = ahead + '\n'+ '\n'.join(captions + labels)  # No content appended, as per your given code

    return processed_content


##########################################################
### remove packages and other unecessary defination ######
##########################################################
def remove_blacklisted_packages(content, blacklisted_packages):
    # This regular expression pattern matches \usepackage{} commands, including those with multiple packages
    usepackage_pattern = r'\\usepackage(\[[^\]]*\])?\{([^}]*)\}'
    removed_blacklisted_packages = []
    # Function to check if any blacklisted package is in the package list and remove it
    def remove_blacklisted(match):
        # Find all packages within the curly braces
        package_list = match.group(2).split(',')
        # Remove any leading/trailing whitespace around package names
        package_list = [pkg.strip() for pkg in package_list]
        # Filter out blacklisted packages
        filtered_packages = [pkg for pkg in package_list if pkg not in blacklisted_packages]
        blacked_packages  = [pkg for pkg in package_list if pkg     in blacklisted_packages]
        removed_blacklisted_packages.extend(blacked_packages)
        # If no packages left after filtering, remove the entire usepackage command
        options = match.group(1) if match.group(1) else ''
        if not filtered_packages:
            remain =  ''
        # Otherwise, create a new usepackage command with the remaining packages
        else:
            
            remain = '\\usepackage{}{{{}}}'.format(options, ', '.join(filtered_packages))
        if len(blacked_packages) > 0:
            filted_package = '%\\usepackage{}{{{}}}'.format(options, ', '.join(blacked_packages))
            return remain +'\n' + filted_package
        return remain

    # Use the sub() method to apply the removal logic to each usepackage command
    modified_content = re.sub(usepackage_pattern, remove_blacklisted, content, flags=re.MULTILINE)

    return modified_content,removed_blacklisted_packages

def comment_out_preamble(content,excluded_commands):
    def comment_out_dependency(match):
        preamble_text = match.group(1)
        #preamble_text,removed_blacklisted_packages = remove_blacklisted_packages(preamble_text,blacklisted_packages = blacklisted_packages)
        commented_preamble = comment_out_preamble_block(preamble_text, excluded_commands=excluded_commands)
        return commented_preamble + '\n'+match.group(2)
    # Define the pattern to match everything from start to the \begin{document} (exclusive)
    preamble_pattern = r'^(.*?)(\\begin{document})'
    commented_content = re.sub(preamble_pattern, comment_out_dependency, content, flags=re.DOTALL)
    return commented_content

def comment_out_preamble_block(content, excluded_commands=None, reverse_mode=False):
    # Initialize variables
    brace_counts = {'curly': 0, 'square': 0, 'round': 0}
    
    commented_content = []
    
    # Helper function to check if all braces are balanced
    def braces_balanced(brace_counts):
        return all(count == 0 for count in brace_counts.values())

    # Define commands to exclude from commenting
    
    
    lines = [line.strip() for line in content.splitlines(True) if  line.strip()]

    elements =[]
    element  =""
    in_command = False
    for i in range(len(lines)):
        line = lines[i]  # Keep linebreaks
        if line.strip().startswith('%'):
            element += line+"\n"
            continue
        
        if not in_command:
            if reverse_mode:
                if not any(line.lstrip().startswith(cmd) for cmd in excluded_commands):
                    in_command = "donot_comment"
                else:
                    in_command = "should_comment"
            else:
                if any(line.lstrip().startswith(cmd) for cmd in excluded_commands):
                    in_command = "donot_comment"
                else:
                    in_command = "should_comment"

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
        element += line

        if in_command.startswith("end_of_comment"):
            COMMENTQ=not in_command.endswith('donot_comment')
            
            if COMMENTQ:
                elements.append("%"+element)
            else:
                elements.append(element)
            element=""
            in_command = False

    return '\n'.join(elements)

def remove_line_via_comment(match):
    return f"% {match.group(0)}" 

def deal_with_the_documentclass(content,mode,blacklisted_packages=None,ForceQ= False):
    assert blacklisted_packages is not None
    removed_blacklisted_packages=[]
    if mode in 'nopackage':
        content = re.sub(r'\\usepackage(\[[^\]]*\])?\{([^}]*)\}', remove_line_via_comment, content)
    else:
        content,removed_blacklisted_packages = remove_blacklisted_packages(content,blacklisted_packages = blacklisted_packages)
    #ForceQ = mode in ['revtex', 'nopackage']
    if ForceQ or 'biblatex' in removed_blacklisted_packages :
        def replace_document_class(match):
            return f"% {match.group(0)}" + "\n"+"\\documentclass[amsmath,amssymb,color,hyperref,cite]{revtex4-1}"

        if "\\documentclass" in content:
            content = re.sub(r'\\documentclass(\[[^\]]*\])?\{.*\}', replace_document_class, content)
        elif "\\documentstyle" in content:
            content = re.sub(r'\\documentstyle(\[[^\]]*\])?\{.*\}', replace_document_class, content)
        bib_filename = None
        def remove_addbibresource(match):
            nonlocal bib_filename
            
            bib_filename = match.group(1).replace('.bib', '')  # Capture the filename for later use
            
            return ''  # Remove the command

        content = re.sub(r'\\addbibresource\{(.+?)\.bib\}', remove_addbibresource, content)
        if bib_filename:
            bib_filename=bib_filename.replace('\\','\\\\')
            bibliography_command = '\\\\bibliography{'+ bib_filename +'}\n'
            content = re.sub(r'(?=\\end{document})', bibliography_command, content)
            
        content = re.sub(r'\\printbibliography.*', '', content)
        content = re.sub(r'\\appendixpage.*', '', content)
    if 'CJK' in removed_blacklisted_packages:
        content = re.sub(r'\\begin{CJK(?:\*)?}', remove_line_via_comment, content)
        content = re.sub(r'\\end{CJK(?:\*)?}', remove_line_via_comment, content)
    content = re.sub(r'\\begin{opening}', remove_line_via_comment, content)
    content = re.sub(r'\\end{opening}', remove_line_via_comment, content)
    return content

#############################################
#################### main ###################
#############################################
def standardize_one_file(file_path, args:TexStandardConfig):
    if args.mode == 'revtex':
        blacklist = args.blacklisted_packages2
        ForceQ = True
    elif args.mode == 'revtex_beta':
        blacklist = args.blacklisted_packages3
        ForceQ = True
    elif args.mode == 'clean':
        blacklist = args.blacklisted_packages
        ForceQ = False
    elif args.mode == 'clean_beta':
        blacklist = args.blacklisted_packages3
        ForceQ = False
    elif args.mode == 'nopackage':
        blacklist = args.blacklisted_packages2
        ForceQ = True
    
    else:
        raise NotImplementedError
    
    file_path = get_tex_file_name(file_path, modes = args.modelist)
    lines_without_comments = read_the_tex_file_into_memory_without_comment(file_path)
    lines_without_comments = [line for line in lines_without_comments if line]

    new_file_path = file_path[:-4]+f'.{args.mode}.tex'


    content = "".join(lines_without_comments)
    content = comment_out_preamble(content,excluded_commands=args.excluded_commands)
    content = deal_with_the_documentclass(content,args.mode,blacklisted_packages=blacklist, ForceQ=ForceQ)
    content = filter_out_affiliation(content, excluded_commands = args.excluded_commands)
    content = filter_out_figures(content)
    content = filter_out_tables(content)
    with open(new_file_path, 'w', encoding='utf-8') as file:
        file.write(content)
    return new_file_path, 'finish'
    
def standardize_one_file_wrapper(args):
    arxiv_path, args = args
    if args.mode == 'prepare_for_color':
        lines_without_comments = read_the_tex_file_into_memory_without_comment(arxiv_path)
        lines_without_comments = [line for line in lines_without_comments if line]
        new_file_path = arxiv_path[:-4]+f'.{args.mode}.tex'
        with open(new_file_path, 'w', encoding='utf-8') as file:
            file.write("".join(lines_without_comments))
        return new_file_path, 'finish'
    else:
        return standardize_one_file(arxiv_path, args)

