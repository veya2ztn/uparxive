import os
ROOTDIR='data/whole_arxiv_quant_ph/unprocessed_json'
alread_processing_file_list = os.listdir(ROOTDIR)
citation_found_file = []
citation_missing_file=[]
for filename in alread_processing_file_list:
    filepath = os.path.join(ROOTDIR,filename)
    filelist = os.listdir(filepath)
    if 'reference.grobid.tei.xml' in filelist:
        citation_found_file.append(filename)
    else:
        citation_missing_file.append(filename)

print(f"""
      You should process {len(citation_found_file) + len(citation_missing_file)} files, 
      and you had process {len(citation_found_file)} files, 
      remain {len(citation_missing_file)} files""")


with open('filelists/citation_found_file','w') as f:
    for file in citation_found_file:
        f.write(file+'\n')

with open('filelists/citation_missing_file','w') as f:
    for file in citation_missing_file:
        f.write(file+'\n')


for a in citation_found_file:
    os.system(f"mv data/whole_arxiv_quant_ph/unprocessed_json/{a} data/whole_arxiv_quant_ph/citation_found_json/{a}")