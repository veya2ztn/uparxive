import fitz, math
def is_meaningful_markdonw_color(color):
    return all([isinstance(c,int) for c in color])
def is_meaninful_pdf_color(color):
    return color and color !=0 and color !=(0,0,0)

def add_rgb(color,increment=0.1):
    # 对(R,G,B)计算加法，递增序列
    if color[2]+increment <= 255:
        return (color[0],color[1],color[2]+increment)
    elif color[1]+increment <= 255:
        return (color[0],color[1]+increment,0)
    else:
        return (color[0]+increment,color[1],color[2])
def greater_rgb(color1,color2):
    '''
    color1:(r,g,b)
    color2:(r,g,b)
    '''
    if color1[0]==color2[0]:
        if color1[1] == color2[1]:
            return color1[2]>color2[2]
        else:
            return color1[1]>color2[1]
    else:
        return color1[0]>color2[0] 
def norm_box(box,page_h,page_w):
    x1,y1,x2,y2 = box[0]/page_w,box[1]/page_h,box[2]/page_w,box[3]/page_h
    return [[x1,y1],[x2,y2]]    
def add_rgb(color,increment=0.1):
    # 对(R,G,B)计算加法，递增序列
    if color[2]+increment <= 255:
        return (color[0],color[1],color[2]+increment)
    elif color[1]+increment <= 255:
        return (color[0],color[1]+increment,0)
    else:
        return (color[0]+increment,color[1],color[2])
def inserted_color(color):
    # 判断color是否为后加入的，即不可见符号
    for i in range(3):
        if color[i]%5:
            return True
    return False
def hex_to_rgb(hex_color):
    # Check if the provided hex_color is valid
    if len(hex_color) != 6:
        raise ValueError(f"Invalid color code: must be a 6-digit hexadecimal number, now is {hex_color}")
    
    # Extract the red, green, and blue parts from the hex_color
    r = int(hex_color[0:2], 16)  # Convert the first two characters to an integer from base-16
    g = int(hex_color[2:4], 16)  # Convert the second two characters to an integer from base-16
    b = int(hex_color[4:6], 16)  # Convert the last two characters to an integer from base-16

    return (int(r),int(g),int(b))

def get_color(sRGB):
    color = fitz.sRGB_to_rgb(sRGB )
    #color = sRGB_to_rgb(s['color'])
    color = tuple([math.ceil(c/5)*5 for c in color])
    return color

def are_adjacent_or_overlapping(bbox1, bbox2, tolerance=1):
    """
    Check if two bounding boxes are adjacent or overlapping.

    Parameters:
    - bbox1: Tuple (min_x1, min_y1, max_x1, max_y1)
    - bbox2: Tuple (min_x2, min_y2, max_x2, max_y2)

    Returns:
    - Boolean indicating if the two boxes are adjacent or overlapping.
    """
    # Check for overlap or adjacency in horizontal (x) and vertical (y) axis
    horizontal = (bbox1[0] <= bbox2[2] + tolerance) and (bbox2[0] <= bbox1[2] + tolerance)
    vertical = (bbox1[1] <= bbox2[3] + tolerance) and (bbox2[1] <= bbox1[3] + tolerance)
    return horizontal and vertical

def merge_bboxes(bboxes, tolerance=10):
    """
    Merge bounding boxes that are overlapping or adjacent.

    Parameters:
    - bboxes: List of tuples, where each tuple represents a bounding box as
              (min_x, min_y, max_x, max_y).

    Returns:
    - A tuple representing the merged bounding box (min_x, min_y, max_x, max_y), or None if they are not adjacent or overlapping.
    """
    if not bboxes:
        return None

    # Start with the first bbox
    merged_bbox = bboxes[0]

    for bbox in bboxes[1:]:
        if are_adjacent_or_overlapping(merged_bbox, bbox,tolerance):
            # Update merged_bbox to include the current bbox
            merged_bbox = (
                min(merged_bbox[0], bbox[0]),
                min(merged_bbox[1], bbox[1]),
                max(merged_bbox[2], bbox[2]),
                max(merged_bbox[3], bbox[3])
            )
        else:
            return None  # If any bbox is not adjacent or overlapping, return None

    return merged_bbox