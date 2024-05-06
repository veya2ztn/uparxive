import os
from find_remake_filelist import find_the_correct_tex


alread_processing_file_list = os.listdir('data/whole_arxiv_quant_ph/unprocessed_json')

should_processing_file_list = []
with open('filelists/ready_file','r') as f:
    for line in f:
        should_processing_file_list.append(line.strip())

alread_processing_file_list = set(alread_processing_file_list)
should_processing_file_list = set(should_processing_file_list)

remain_processing_file_list = should_processing_file_list - alread_processing_file_list
print(f"""
      You should process {len(should_processing_file_list)} files, 
      and you had process {len(alread_processing_file_list)} files, 
      remain {len(remain_processing_file_list)} files""")
with open('filelists/file_wont_processed_from_xml_to_json','w') as f:
    for file in remain_processing_file_list:
        f.write(file+'\n')


REMAKE_FILES, multifiles_case, main_file_miss_case= find_the_correct_tex(remain_processing_file_list)

with open('filelists/remain_file','w') as f:
    for file in REMAKE_FILES:
        f.write(file+'\n')

# for a in alread_processing_file_list:
#     os.system(f"mv data/whole_arxiv_quant_ph/unprocessed_xml/{a} data/whole_arxiv_quant_ph/successed_xml/{a}")