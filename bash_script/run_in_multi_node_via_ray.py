import ray
import time
import os
from ray.experimental.tqdm_ray import tqdm
from simple_parsing import ArgumentParser
from uparxive.reference_reterive.citation_string_to_reference import process_one_path_wrapper, RetrieveESConfig
from uparxive.xml_to_json.xml_to_dense_text import XMLtoJsonConfig, xml_to_json_one_path_wrapper
from uparxive.tex_to_xml.run_tex_to_html import tex_to_html_wrapper, Tex2HTMLConfig
from uparxive.batch_run_utils import obtain_processed_filelist, process_files, save_analysis, BatchModeConfig, Pool
from python_script.pdf_aligned_pipline import deal_with_one_pdf_file_wrapper, MarkdownPDFalignedConfig
import os
import logging
def set_log_level(log_level):
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError('Invalid log level: %s' % log_level)
    logging.basicConfig(level=numeric_level)

# Set the log level to 'DEBUG'
set_log_level('error')
# Initialize Ray
ray.init(address='auto')  # Connect to the cluster
func=deal_with_one_pdf_file_wrapper
# General task function parameterized by resources
@ray.remote
def general_task(args):
    # hostname = os.popen('hostname').read().strip()
    # results = (f"Processed  data at {hostname}")
    # return results
    already_processing_file_list = obtain_processed_filelist(args)
    num_processes = args.batch_num
    with Pool(processes=num_processes) as pool:
        args_list = [(file, args) for file in already_processing_file_list]
        results = list(tqdm(pool.imap(func, args_list), total=len(already_processing_file_list)))
    return results

# Prepare arguments
results = []
node_resources = [#{"124": 1}, 
                  {"120": 1}, 
                  {"119": 1}, 
                  {"118": 1},
                  {"123": 1},
                  {"121": 1}, 
                  {"122": 1},
                  { "86": 1}, 
                  { "87": 1}, 
                  { "88": 1}, 
                  { "89": 1},
                  { "90": 1}
                  ]  # Define resources for each node type
for index, resources in enumerate(node_resources):
    # args = RetrieveESConfig(
    #     root_path="/nvme/zhangtianning.di/sharefold/whole_arxiv_all_files/should_reterive_reference.filelist",
    #     batch_num=40,
    #     index_part=index,
    #     num_parts=len(node_resources)
    # )
    # args = XMLtoJsonConfig(
    #     root_path="/nvme/zhangtianning.di/sharefold/whole_arxiv_all_files/archive_xml.filelist",
    #     batch_num=200,
    #     index_part=index,
    #     do_not_generate_reference=True,
    #     num_parts=len(node_resources),
    #     logpath=f"/nvme/zhangtianning.di/sharefold/whole_arxiv_all_files/analysis/host_{index}"
    #     #shuffle=True
    # )
    args = Tex2HTMLConfig(
        root_path="/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/no_target_html.colorful.filelist",
        batch_num=100,
        index_part=index,
        num_parts=len(node_resources)
    )
    # args = MarkdownPDFalignedConfig(
    #     root_path="/nvme/zhangtianning.di/sharefold/whole_arxiv_all_files/no_content_md.colorful.filelist",
    #     batch_num=50,
    #     index_part=index,
    #     num_parts=len(node_resources)
    # )
    # Using the general task function with specific resources

    result = general_task.options(resources=resources).remote(args)
    results.append(result)

# Gather results (if needed immediately, otherwise can be handled later)

# Retrieve and print results
for result in results:
    a=ray.get(result)
    if isinstance(a,str):
        print(a)

ray.shutdown()