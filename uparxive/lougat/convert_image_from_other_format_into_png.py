from PIL import Image, ImageChops

from uparxive.tex_to_xml.standalize_tex import *
from uparxive.lougat.color_tex import *
from ..batch_run_utils import BatchModeConfig, dataclass
import subprocess

@dataclass
class ImgaeConverterConfig(BatchModeConfig):
    verbose : bool = False
    redo : bool = False
    mode : str = 'eps_to_png'
    task_name = 'convert_image'
    deleteSrc: bool = False
    move_to_figure: bool = False
class FailError(NotImplementedError):pass
class NoMethodError(NotImplementedError):pass
def get_true_img_path(img_path,args:ImgaeConverterConfig):
    if not os.path.exists(img_path):
        arxivid = img_path.split('/')[0]
        if len(arxivid) > 4:
            match = re.search(r"\d{4}", arxivid)
            if match:
                # Print the matched pattern
                date = match.group()
            img_path = os.path.join(args.datapath, date, img_path)
        else:
            img_path = os.path.join(args.datapath, img_path)
    return img_path


def convert_eps_into_png(eps_path, args:ImgaeConverterConfig):
    eps_path = get_true_img_path(eps_path,args)
    assert eps_path.endswith('.eps'), f"the input file should be eps file, but got {eps_path}"
    png_path = get_png_name(eps_path)
    
    #tqdm.write(png_path)
    if os.path.exists(png_path) and not args.redo:return
    

    TARGET_BOUNDS = (2048, 2048)
    # Load the EPS at 10 times whatever size Pillow thinks it should be
    # (Experimentaton suggests that scale=1 means 72 DPI but that would
    #  make 600 DPI scale=8⅓ and Pillow requires an integer)
    pic = Image.open(eps_path)
    pic.load(scale=10)

    # Ensure scaling can anti-alias by converting 1-bit or paletted images
    if pic.mode in ('P', '1'):
        pic = pic.convert("RGB")

    # Calculate the new size, preserving the aspect ratio
    ratio = min(TARGET_BOUNDS[0] / pic.size[0], TARGET_BOUNDS[1] / pic.size[1])
    new_size = (int(pic.size[0] * ratio), int(pic.size[1] * ratio))
    # Resize to fit the target size
    pic = pic.resize(new_size, Image.Resampling.LANCZOS)
    pic.save(png_path)
    ## use unit k
    if args.verbose:old_size = int(os.path.getsize(eps_path)/1024)
    if args.verbose:new_size = int(os.path.getsize(png_path)/1024)
    if args.verbose:tqdm.write(f"shrink from {old_size}k to {new_size}k for {eps_path}")
    if args.deleteSrc:
        os.remove(eps_path)

def convert_eps_into_pdf(eps_path, args:ImgaeConverterConfig):
    eps_path = get_true_img_path(eps_path,args)
    #assert eps_path.endswith('.eps') or eps_path.endswith('.epsi') or eps_path.endswith('.ps'), f"the input file should be eps file, but got {eps_path}"
    pdf_path = get_png_name(eps_path)
    #tqdm.write(png_path)
    if os.path.exists(pdf_path) and not args.redo:return
    process = subprocess.Popen(["ps2pdf", "-dEPSCrop",eps_path , pdf_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
            )
    while True:
        line = process.stdout.readline()
        if 'error' in line.lower():
            process.kill()  # Kill the process if an error is detected
            raise FailError
        if not line:  # If readline returns an empty bytes object, the process has finished
            break
        decoded_line = line#.decode('utf-8')
        #print(decoded_line, end='')  # Print the output in real-time
    if args.verbose:old_size = int(os.path.getsize(eps_path)/1024)
    if args.verbose:new_size = int(os.path.getsize(pdf_path)/1024)
    if args.verbose:tqdm.write(f"shrink from {old_size}k to {new_size}k for {eps_path}")
    if args.deleteSrc:
        os.remove(eps_path)
    
def get_png_name(path):
    path = os.path.basename(path)
    path = path.split('.')[:-1]
    path = ".".join(path)
    path = path+'.png'
    return path

def trim(image, margin=10):
    """
    Trims the white space around an image and adds a margin.

    :param image: PIL Image object to be trimmed.
    :param margin: Margin size to be added around the trimmed image.
    :return: Cropped PIL Image object with added margin.
    """
    bg = Image.new(image.mode, image.size, (255, 255, 255))
    diff = ImageChops.difference(image, bg)
    bbox = diff.getbbox()
    if bbox:
        # Expand the bounding box by the margin
        bbox = (
            max(0, bbox[0] - margin),  # Left
            max(0, bbox[1] - margin),  # Top
            min(image.size[0], bbox[2] + margin),  # Right
            min(image.size[1], bbox[3] + margin)   # Bottom
        )
        return image.crop(bbox)
    return image

from pdf2image import convert_from_path
def convert_pdf_into_png(pdf_path, args:ImgaeConverterConfig):
    pdf_path = get_true_img_path(pdf_path,args)
    assert pdf_path.endswith('.pdf'), f"the input file should be eps file, but got {pdf_path}"
    png_path = get_png_name(pdf_path)
    if args.move_to_figure:
        png_path = os.path.join(os.path.dirname(os.path.dirname(pdf_path)),'figures',os.path.basename(png_path))
    #tqdm.write(png_path)
    if os.path.exists(png_path) and not args.redo:return
    images = convert_from_path(pdf_path, dpi=300)
    assert len(images)>0
    cropped_image = trim(images[0])
    cropped_image.save(png_path)
    if args.verbose:old_size = int(os.path.getsize(pdf_path)/1024)
    if args.verbose:new_size = int(os.path.getsize(png_path)/1024)
    if args.verbose:tqdm.write(f"shrink from {old_size}k to {new_size}k for {png_path}")
    if args.deleteSrc:
        os.remove(pdf_path)



def process_one_file_wrapper(args:ImgaeConverterConfig):
    file_path, args = args
    file_path = get_true_img_path(file_path,args)
    if not os.path.exists(file_path):
        return file_path, 'NoSource'
    try:
        if args.mode == 'eps_to_png':
            convert_eps_into_png(file_path, args)
        elif args.mode == 'pdf_to_png':
            convert_pdf_into_png(file_path, args)
        elif args.mode == 'eps_to_pdf':
            convert_eps_into_pdf(file_path, args)
        else:
            raise NoMethodError(f"not support mode {args.mode}")
        return file_path, 'Pass'
    except FailError:
        return file_path, 'Fail'
    except NoMethodError:
        raise
    except Exception as e:
        return file_path, 'Fatal'