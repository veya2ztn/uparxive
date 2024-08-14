from pathlib import Path
import sys
module_dir = str(Path(__file__).resolve().parent.parent)
if module_dir not in sys.path:sys.path.append(module_dir)

from uparxive.batch_run_utils import obtain_processed_filelist, process_files,save_analysis, BatchModeConfig
from simple_parsing import ArgumentParser
import os,re
import pandas as pd
from tqdm.auto import tqdm
import numpy as np
from transformers import AutoTokenizer
import traceback

def is_good_a_math_sequence(block_math_indices):
    block_math_indices = np.array(block_math_indices)
    if len(block_math_indices) % 2 == 0:
        if all((block_math_indices[1::2] - block_math_indices[::2]) == 2):
            return 'good'
        else:
            return None
    else:
        if is_good_a_math_sequence(block_math_indices[1:]):
            return 'left'
        elif is_good_a_math_sequence(block_math_indices[:-1]):
            return 'right'
        else:
            return None
def good_box(box):
    if box is None:return None
    if box is np.nan:return None
    if isinstance(box,str):box= eval(box)
    assert isinstance(box, list)
    assert isinstance(box[0], list)
    return box    

def filter_df(df):
    df = df[~((df['text_type']=='<text>') & (df['markdown']!=df['pdf']))]
    df = df[~df['markdown'].isna()].reset_index(drop=True)
    first_no_nan = df['bbox'].first_valid_index()
    
    if len(df) > 1.5*df['bbox'].count() or len(df) > 2000 or df['bbox'].count()<100:
        #bad_pdf_bbox_data_path_pair.append([arxivpath, pdf_name, page_id, 'bad_alignment'])
        return False, 'bad_alignment'
    df = df.loc[first_no_nan-1:].reset_index(drop=True)
    first_no_nan = df['bbox'].first_valid_index()
    boxes = []
    for t in df['bbox'].values:
        box = good_box(t) 
        if box is None:
            if len(boxes)>0:
                side = boxes[-1][-1]
            else:
                side = good_box(df['bbox'].values[first_no_nan])[0]
            box = [side,side]
        boxes.append(box)
    block_math_indices = df.index[df['text_type'] == '<block_math>'].tolist()
    block_status = is_good_a_math_sequence(block_math_indices)
    if block_status == 'good':
        pass
    elif block_status == 'left':
        if block_math_indices[0] == 1:
            ### lets add a new block_math_indices at the begin
            new_row = pd.DataFrame({'text_type': ['<block_math>'], 'markdown': ['\n\[\n'], 'pdf': [''] ,'status': 'invisable','bbox': None})
            df = pd.concat([new_row, df]).reset_index(drop=True)
            block_math_indices = df.index[df['text_type'] == '<block_math>'].tolist()
        else:
            df.iloc[block_math_indices[0], df.columns.get_loc("markdown")] = ""
            block_math_indices = block_math_indices[1:]
    elif block_status == 'right':
        if block_math_indices[-1] == len(df)-2:
            ### lets add a new block_math_indices at the end
            new_row = pd.DataFrame({'text_type': ['<block_math>'], 'markdown': ['\n\]\n'], 'pdf': [''] ,'status': 'invisable','bbox': None})
            df = pd.concat([df,new_row]).reset_index(drop=True)
            block_math_indices = df.index[df['text_type'] == '<block_math>'].tolist()
        else:
            df.iloc[block_math_indices[-1], df.columns.get_loc("markdown")] = ""
            block_math_indices = block_math_indices[:-1]
    else:
        #bad_pdf_bbox_data_path_pair.append([arxivpath, pdf_name, page_id, 'bad_block_math'])
        return False, 'bad_block_math'
    

    for i in range(0, len(block_math_indices) - 1, 2):
        start = block_math_indices[i]
        end = block_math_indices[i + 1]
        
        # Check if the closing <block_math> has only one text in it
        if end - start > 2:
            #bad_pdf_bbox_data_path_pair.append([arxivpath, pdf_name, page_id, 'bad_block_math'])
            return False, 'bad_block_math'
        if end - start  == 2:
            df.loc[start + 1:end-1, df.columns.get_loc("markdown")] = '<block_equation>'
    return True, df 


def deal_with_one_pdf_file_wrapper(args):
    arxivpath, _ =args
    whole_pdf_bbox_data_path_pair = []
    bad_pdf_bbox_data_path_pair = []
    boxedfile = os.path.join(arxivpath, 'boxed_pdf_image')
    pdf_name  = Path(boxedfile).glob('*.colorful.text_only.pdf')
    pdf_name  = list(pdf_name)[0]
    pdf_name  = os.path.relpath(pdf_name, boxedfile)
    pdf_name  = pdf_name.replace('.colorful.text_only.pdf','')
    pagelist  = os.listdir(os.path.join(boxedfile, 'text_bbox'))
    for page_name in pagelist:
        page_id = int(re.match(r"page_(.*?).csv",os.path.basename(page_name)).group(1))
        try:
            df = pd.read_csv(os.path.join(boxedfile, 'text_bbox', page_name))
            status, df = filter_df(df)
            # tokened = tokenizer(
            #         df['markdown'].values.tolist(),  # len(label)>=1，将pretext和label连起来tokenize并行训练->lst，label_id再自己tokenize一遍（用长度匹配）
            #         return_token_type_ids=False,
            #     )
            if status:
                if max([len(t) for t in df['markdown']]) > 2000:
                    bad_pdf_bbox_data_path_pair.append([arxivpath, pdf_name, page_id, 'too_long'])
                    continue
                whole_pdf_bbox_data_path_pair.append([arxivpath, pdf_name, page_id, ])
            else:
                bad_pdf_bbox_data_path_pair.append([arxivpath, pdf_name, page_id, df])
        except:
            tqdm.write(f"Error in reading {os.path.join(boxedfile, 'text_bbox', page_name)}")
            bad_pdf_bbox_data_path_pair.append([arxivpath, pdf_name, page_id, 'fail_to_read'])
            continue
    return bad_pdf_bbox_data_path_pair,whole_pdf_bbox_data_path_pair
if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_arguments(BatchModeConfig, dest="config")
    args = parser.parse_args()
    args = args.config

    alread_processing_file_list = obtain_processed_filelist(args)
    results = process_files(deal_with_one_pdf_file_wrapper, alread_processing_file_list, args)
    bad_pdf_bbox_data_path_pair_all = []
    whole_pdf_bbox_data_path_pair_all=[]
    for bad_pdf_bbox_data_path_pair,whole_pdf_bbox_data_path_pair in results:
        #print(f"bad_pdf_bbox_data_path_pair={len(bad_pdf_bbox_data_path_pair)} whole_pdf_bbox_data_path_pair={len(whole_pdf_bbox_data_path_pair)}")
        bad_pdf_bbox_data_path_pair_all.extend(bad_pdf_bbox_data_path_pair)
        whole_pdf_bbox_data_path_pair_all.extend(whole_pdf_bbox_data_path_pair)
    
    analysis={
        'good': whole_pdf_bbox_data_path_pair_all,
        'bad':bad_pdf_bbox_data_path_pair_all,

    }
    for k,v in analysis.items():
        tqdm.write(f"{k}={len(v)}")
    name = os.path.basename(args.root_path).replace('.filelist','')
    df = pd.DataFrame(whole_pdf_bbox_data_path_pair_all, columns=['arxivpath', 'pdf_name', 'page_id'])
    np.random.seed(1994)
    labels = ['train', 'dev', 'test']
    probabilities = [0.8, 0.1, 0.1]
    group_labels = np.random.choice(labels, size=len(df), p=probabilities)
    df['split']  = group_labels
    df.to_csv(f'{name}.pdf_box_pair.csv', index=False)
    df = pd.DataFrame(bad_pdf_bbox_data_path_pair_all, columns=['arxivpath', 'pdf_name', 'page_id', 'fail_reason'])
    df.to_csv(f'{name}.bad_pdf_box_pair.csv', index=False)
    # totally_paper_num = len(alread_processing_file_list)
    # save_analysis(analysis, totally_paper_num==1, args)