#!/bin/bash

# Assign the first argument to a variable
filelist=$1

# Assign the second argument to a variable and multiply by 100
chunk_size=$3
index=$(($2*$chunk_size))

# Calculate the end index
end_index=$(($index+$chunk_size))

# Initialize a counter
counter=0
time_limit=60 
processed=0
# Read the filelist line by line
while IFS= read -r texfilepath
do

    # If the counter is greater than or equal to the index and less than the end_index
    if [ "$counter" -ge "$index" ] && [ "$counter" -lt "$end_index" ]; then
        #Search for .tex files in the directory
        ((processed++))
        percent=$((100 * processed / chunk_size))
        bar=$(printf '%*s' $((percent / 2)) '' | tr ' ' '=')
        printf "\rProgress: [%-50s] %d%% (%d/%d)" "$bar" $percent $processed $chunk_size
        
        paper_fold=`dirname $texfilepath`
        texfilename=`basename $texfilepath .tex`
        ORIGINALTEXPATH=$paper_fold/$texfilename.origin.tex
        #for texfilepath in $(find $ROOTDIR -type f -name "*.tex"); do
        ### lets replace the 
        # arxivid=`basename $paper_fold`
        # paper_fold=`dirname $paper_fold`
        # date=`basename $paper_fold`
        # paper_fold=`dirname $paper_fold`
        # foldname=`basename $paper_fold`
        # paper_fold=/nvme/zhangtianning.di/sharefold/whole_arxiv_all_files/$foldname/$date/$arxivid
        echo $paper_fold
        if [ ! -e "$paper_fold" ]; then
            mkdir -p $paper_fold
        fi
        OUTPUTFIE=$paper_fold/boxed_pdf_image/content.md
        TEXTONLYPDFPATH=$paper_fold/temp/$texfilename.text_only.pdf
        COLORFULPDFPATH=$paper_fold/temp/$texfilename.pdf
        COLORFULHTMLPATH=$paper_fold/temp/$texfilename.html
        
        if [ -e "$ORIGINALTEXPATH" ]; then
            cp $ORIGINALTEXPATH $texfilepath 
        fi
        if [ ! -e "$COLORFULHTMLPATH" ]; then
            latexmlc --timeout 3600 --verbose --nocomments --includestyles  -log=$paper_fold/temp/latexmlc.log  --path=$paper_fold --dest=$COLORFULHTMLPATH $texfilepath
        fi
        if [ ! -e "$TEXTONLYPDFPATH" ]; then
            python /nas/zhangtianning.di/projects/unique_data_build/python_script/discard_color_box.py --root $texfilepath
            latexmk -quiet -silent -synctex=0 -pdflatex="pdflatex -interaction=nonstopmode" -file-line-error -pdf -f -outdir=$paper_fold/temp -cd $texfilepath
            mv $COLORFULPDFPATH $TEXTONLYPDFPATH
            cp $ORIGINALTEXPATH $texfilepath 
        fi
        if [ -e "$ORIGINALTEXPATH" ]; then
            cp $ORIGINALTEXPATH $texfilepath 
        fi
        if [ ! -e "$COLORFULPDFPATH" ]; then
            latexmk -quiet -silent -synctex=0 -pdflatex="pdflatex -interaction=nonstopmode" -file-line-error -pdf -f -outdir=$paper_fold/temp -cd $texfilepath
        fi

        ## if ORIGINALTEXPATH, TEXTONLYPDFPATH and COLORFULPDFPATH existed
        if [ -e "$COLORFULHTMLPATH" ] && [ -e "$TEXTONLYPDFPATH" ] && [ -e "$COLORFULPDFPATH" ] && [ ! -e "$OUTPUTFIE" ]; then
            python /nas/zhangtianning.di/projects/unique_data_build/python_script/pdf_box_aligned.py --root $COLORFULHTMLPATH
        fi

    fi

    ((counter++))
    if [ "$counter" -ge "$end_index" ]; then
        break
    fi
done < "$filelist"

echo "\n"