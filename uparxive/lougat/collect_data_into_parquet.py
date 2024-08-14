from PIL import Image, ImageChops
from ..batch_run_utils import BatchModeConfig, dataclass
from io import BytesIO
import base64
import fitz,os
fitz.TOOLS.mupdf_display_errors(on=False)
import io, json
from PIL import Image, ImageOps
import pandas as pd
from tqdm.auto import tqdm
import numpy as np
from datasets import Sequence,Features,Value,Array2D,Array3D, Dataset
import datasets
datasets.logging.disable_progress_bar()
@dataclass
class ParquetConverterConfig(BatchModeConfig):
    verbose : bool = False
    redo : bool = False
    dpi  : int  = 200
    task_name = 'convert_image'
    
NONE_BBOX_CASE=[None, np.nan,[[0,0],[0,0]],[[-1,-1],[-1,-1]]]

def good_box(box):
    if box in NONE_BBOX_CASE:return None
    if isinstance(box,str):box= eval(box)
    assert isinstance(box, list)
    assert isinstance(box[0], list)
    return box    

def fill_empty_bbox_follow_last(bbox_ordered):
    boxes = []
    for t in bbox_ordered:
        box = good_box(t) 
        if box is None:
            if len(boxes)>0:
                ((x0, y0),(x1,y1))= boxes[-1]
                box = [[x1,y0],[x1+0.001,y1]]
            else:
                box  = [[0,0],[0.001,0.001]]
        boxes.append(box)
    return boxes


def get_page_image(pdf_file_path, page_id, dpi=200):
    
    dpi_to_resolution={
        100: 1024,
        200: 2048,
    }
    with fitz.open(pdf_file_path) as pdf:
        page = pdf.load_page(page_id)
        image = Image.open(io.BytesIO(page.get_pixmap(colorspace=fitz.csGRAY,dpi=dpi).pil_tobytes(format="PNG")))
        #print(image.width,image.height )
        gray_image = ImageOps.grayscale(image)
        img = gray_image.point(lambda p: 255 if p == 255 else 0) ### <-- this one let all no-white color become black
        
        new_height    = dpi_to_resolution[dpi]
        #tqdm.write(f"{np.array(img).shape}")
        aspect_ratio  = img.width / img.height
        new_width     = int(new_height * aspect_ratio)
        resized_image = img.resize((new_width, new_height))
        
        # raise
    return resized_image

def convert_pdf_into_png(parquert_path, pdf_file_and_json_file_pair, args:ParquetConverterConfig):
    if os.path.exists(parquert_path):return 
    rows = [] 
    progressbar   = pdf_file_and_json_file_pair if args.batch_num > 1 else tqdm(pdf_file_and_json_file_pair,position=2,leave=False)
    for pdf_path, formated_path in progressbar:

        page_id = int(os.path.basename(formated_path).split('.')[0].replace('page_',''))
        with open(formated_path,'r') as f:  
            data = json.load(f)
        token_id  = data['token_ids']
        bbox      = data['bboxes']
        text_type = data['text_type']
        resized_image = get_page_image(pdf_path, page_id,args.dpi)
        bbox = fill_empty_bbox_follow_last(bbox)
        rows.append({
            "image":  resized_image,
            
                "token_ids":token_id,
                "bboxes": bbox,
                "text_types":text_type
    
        })
    
    os.makedirs(os.path.dirname(parquert_path),exist_ok=True)
    
    # import Dataset, Features, Image, Value,Array2D,Array3D,Sequence
    # we need to define the features ourselves
    features = Features({
        'token_ids' : Sequence(feature=Sequence(Value(dtype='int32'))), 
        'text_types': Sequence(feature=Value(dtype='int8')), 
        'bboxes'    : Sequence(feature=Array2D(shape=(2,2),dtype='float32')), 
        'image'     : datasets.Image(decode=True),
    })
    dataset = Dataset.from_list(rows, features=features)
    dataset.to_parquet(parquert_path)
    
def process_one_file_wrapper(args):
    (parquert_path, pdf_file_and_json_file_pair), args = args
    convert_pdf_into_png(parquert_path, pdf_file_and_json_file_pair, args)
   
