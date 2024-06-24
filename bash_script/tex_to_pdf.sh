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
        #for texfilepath in $(find $ROOTDIR -type f -name "*.tex"); do
        OUTPUTFIE=$paper_fold/temp/$texfilename.pdf
        #if [ ! -e "$OUTPUTFIE" ]; then
            #latexml --noparse --nocomments --includestyles --log="$LOGFILE" --path="$paper_fold" --dest="$OUTPUTFIE" "$texfilename.tex"
            timeout 120 latexmk -quiet -silent -synctex=0 -pdflatex="pdflatex -interaction=nonstopmode" -file-line-error -pdf -f -outdir=temp -cd $texfilepath > /dev/null
            #timeout 120 latexmk -quiet -silent -synctex=0 -xelatex="xelatex -interaction=nonstopmode" -file-line-error -f -outdir=temp -cd $texfilepath > /dev/null
        #fi

    fi

    ((counter++))
    if [ "$counter" -ge "$end_index" ]; then
        break
    fi
done < "$filelist"

echo "\n"