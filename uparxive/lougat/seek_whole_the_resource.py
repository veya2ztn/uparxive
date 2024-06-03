from .prepare_tex import *


@dataclass
class SeekResourceConfig(BatchModeConfig):
    verbose : bool = False
    redo : bool = False
    task_name = 'seek_resource'



def seek_resource(file_path,args):
    if not os.path.exists(file_path):return []
    root = os.path.dirname(file_path)
    roott= os.path.dirname(root)
    content = read_content_with_input(file_path)
    lines_without_comments = read_the_tex_file_into_memory_without_comment(content, use_content=True)
    lines_without_comments = [line.strip()+'\n' for line in lines_without_comments ]
    content = "".join(lines_without_comments)
    content = re.sub( r'\\includegraphics\[[^\]]+\]', f'\\\\includegraphics', content, flags=regex.DOTALL)
    pattern = r'\\includegraphics\s*(?:\[.*?\])?\s*\{(.+?)\}'
    matches = re.findall(pattern, content)
    matches = re.findall(pattern, content)
    
    whole_resource = []
    for file_path in matches:
        abspath = os.path.join(root, file_path)
        #print(abspath)
        if os.path.exists(file_path):continue
        
        whole_resource.append(os.path.relpath(abspath,roott))
    #
    return whole_resource

    

def process_one_file_wrapper(args:PrepareColorFulConfig):
    file_path, args = args
    try:
        return seek_resource(file_path, args)
    except:
        #tqdm.write(f"fail ===> {file_path}")
        return []
 