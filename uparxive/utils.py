import os
def get_tex_file_name(texname:str, modes = ['clean','revtex','package']):
    ### get the tex file name. The tex name may ends with .tex, .TeX, .TEX, .clean.tex , .revtex.tex , .package.tex
    ### we will use python re package do this 
    lowertexname = texname.lower()
    for mode in modes:
        flag = f".{mode}.tex" 
        if lowertexname.endswith(flag):
            return texname[:-len(flag)]+texname[-4:]
    assert lowertexname.endswith('.tex')
    return texname


def isHardTex(texname):
    extensions = ['.tex']
    for ext in extensions:
        if texname.lower().endswith(ext):
            return True
    return False


def isSoftTex(texname):
    extensions = ['.tex.cry','.txt','.fls','.latex']
    for ext in extensions:
        if texname.lower().endswith(ext):
            return True
    if len(texname.split('/')[-1].split('.'))==1: ### no postfix
        return True
    return False

def isComponentOfTex(texname):
    extensions = ['.bbl', '.sty','.ltx', '.cls', '.bst', '.bib', '.bbx','.tikz','.clo','.cbx','.dtx']
    for ext in extensions:
        if texname.lower().endswith(ext):
            return True
    return False

def isHardTexFile(texfile):
    if not os.path.exists(texfile):return False
    return isHardTexFile(os.path.basename(texfile))

def isHardTexFile(texfile):
    if not os.path.exists(texfile):return False
    return isHardTex(texfile)

def isSoftTexFile(texfile):
    if not os.path.exists(texfile):return False
    return isSoftTex(texfile)
