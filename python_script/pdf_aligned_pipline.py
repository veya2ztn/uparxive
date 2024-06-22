
from pathlib import Path
import sys
module_dir = str(Path(__file__).resolve().parent.parent)
if module_dir not in sys.path:sys.path.append(module_dir)

from uparxive.batch_run_utils import obtain_processed_filelist, process_files,save_analysis
from uparxive.lougat.markdown_pdf_align import MarkdownPDFalignedConfig
from simple_parsing import ArgumentParser
from python_script.discard_color_box import process_one_file as remove_color_box
from uparxive.lougat.markdown_pdf_align import deal_with_one_pdf_file as pdf_alignment
from uparxive.tex_to_xml.run_tex_to_html import tex_to_html
from python_script.compile_tex import process_one_file as tex_to_pdf

import os
def deal_with_one_pdf_file_wrapper(args):
    tex_path, args = args
    filename  = os.path.basename(tex_path)[:-4]
    assert 'colorful' in filename
    file_root = os.path.dirname(tex_path)

    ORIGINALTEXPATH =os.path.join(file_root, f"{filename}.origin.tex")
    OUTPUTFIE       =os.path.join(file_root, 'boxed_pdf_image', "content.md")
    TEXTONLYPDFPATH =os.path.join(file_root, 'temp', f"{filename}.text_only.pdf")
    COLORFULPDFPATH =os.path.join(file_root, 'temp', f"{filename}.pdf")
    COLORFULHTMLPATH=os.path.join(file_root, 'temp', f"{filename}.html")
    
    if not os.path.exists(COLORFULHTMLPATH):
        tex_to_html(tex_path, args)
    
    if os.path.exists(ORIGINALTEXPATH):os.rename(ORIGINALTEXPATH, tex_path)
    if not os.path.exists(TEXTONLYPDFPATH):
        
        remove_color_box(tex_path, args)
  
        tex_to_pdf(tex_path, args)
        
        if os.path.exists(COLORFULPDFPATH):os.rename(COLORFULPDFPATH, TEXTONLYPDFPATH)
        if os.path.exists(ORIGINALTEXPATH):os.rename(ORIGINALTEXPATH, tex_path)
    if os.path.exists(ORIGINALTEXPATH):os.rename(ORIGINALTEXPATH, tex_path)
    
    if not os.path.exists(COLORFULPDFPATH):
        tex_to_pdf(tex_path, args)
    # if os.path.exists(TEXTONLYPDFPATH) and os.path.exists(COLORFULPDFPATH) and os.path.exists(COLORFULHTMLPATH) and not os.path.exists(OUTPUTFIE):
    #     pdf_alignment(COLORFULHTMLPATH, COLORFULPDFPATH, args)
    
    if os.path.exists(TEXTONLYPDFPATH) and os.path.exists(COLORFULPDFPATH) and os.path.exists(COLORFULHTMLPATH):
        return 'success', tex_path
    else:
        return 'fail', tex_path



if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_arguments(MarkdownPDFalignedConfig, dest="config")
    args = parser.parse_args()
    args = args.config

    alread_processing_file_list = obtain_processed_filelist(args)
    results = process_files(deal_with_one_pdf_file_wrapper, alread_processing_file_list, args)
    
    analysis= {}
    for  _type,arxivid in results:
        if _type not in analysis:
            analysis[_type] = []
        analysis[_type].append(arxivid)
    
    totally_paper_num = len(alread_processing_file_list)
    save_analysis(analysis, totally_paper_num==1, args)