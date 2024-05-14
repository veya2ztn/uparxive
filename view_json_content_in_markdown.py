import json
import sys

JsonFilePath = sys.argv[1] #/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_old_quant_ph/unprocessed_json/0711.3850/0711.3850.retrieved.json

with open(JsonFilePath, 'r') as f:
    content = json.load(f)
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

