import json
import sys

JsonFilePath = sys.argv[1] #/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_old_quant_ph/unprocessed_json/0711.3850/0711.3850.retrieved.json

markdownstring = ""
def print_content_string(sections_pool, level=1):
    if content['abstract']:
        print("#","Abstract")
        print(content['abstract'])

    def print_sentense(sections_pool, level = 1):
        if 'title' in sections_pool and sections_pool['title']:print("#"*level, sections_pool['title'])
        if 'content' in sections_pool:
            for paragraph in sections_pool['content']:
                if isinstance(paragraph, str):
                    print(paragraph+'\n')
                else:
                    print_sentense(paragraph, level+1)
    if content['sections']:
        print_sentense(content['sections'])

def build_content_string(sections_pool, level=1):
    result = ""
    if 'title' in sections_pool and sections_pool['title']:
        result += "#" * level + " " + sections_pool['title'] + "\n"
    if 'content' in sections_pool:
        for paragraph in sections_pool['content']:
            if isinstance(paragraph, str):
                result += paragraph + "\n\n"
            else:
                result += build_content_string(paragraph, level + 1)
    return result

# Load JSON data from file
with open(JsonFilePath, 'r') as f:
    content = json.load(f)

# Start assembling the output
output = ""
# Append abstract if it exists
if content.get('abstract'):
    output += "# Abstract\n" + content['abstract'] + "\n\n"

# Append the rest of the document
output += build_content_string(content['sections'])

# Finally, print the entire constructed content at once


figure_source =  content['metadata']['figures_source']
tables_source =  content['metadata']['tables_source']

def replace_from_source(match):
    
    _type = match.group(1)
    key   = match.group(2)  # Construct the key as 'TYPE:key'
    #print(_type, key)
    if _type == 'Figure':
        return figure_source[key].replace('.pdf','').replace(')','') + '.jpeg)'
    if _type == 'Table':
        return tables_source[key]
    raise NotImplementedError(f"Unknown type: {_type}")
# Regular expression to find patterns in the format ![TYPE:key]
pattern = r"!\[(Figure|Table):(.*?)\]"

import re
updated_content = re.sub(pattern, replace_from_source, output)

with open('snap.md','w') as f:
    f.write(updated_content)

