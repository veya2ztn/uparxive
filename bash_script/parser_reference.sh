#!/bin/bash

# Check if the correct number of arguments are provided
if [ "$#" -ne 3 ]; then
    echo "You need to supply a filelist and an index"
    exit 1
fi

# Assign the first argument to a variable
filelist=$1 #/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_cs/analysis.grobid_reference/unprocessed_json/1703.07570

# Assign the second argument to a variable and multiply by 100
chunk_size=$3
index=$(($2*$chunk_size))

# Calculate the end index
end_index=$(($index+$chunk_size))

# Initialize a counter
counter=0
ROOT=$(dirname $filelist) # 
ROOT=$(dirname $ROOT)
# Read the filelist line by line
while IFS= read -r dir
do
    # If the counter is greater than or equal to the index and less than the end_index
    if [ "$counter" -ge "$index" ] && [ "$counter" -lt "$end_index" ]; then
        texfilepath=$ROOT/unprocessed_json/$dir/reference.txt
        echo "===>$texfilepath"
        paper_fold=$(dirname $texfilepath)
        tex_fold=$(dirname $paper_fold)
        ROOTDIR=$(dirname $tex_fold)
        INPUTPATH=$paper_fold/reference.txt
        if [ ! -s "$INPUTPATH" ]; then
            echo "File $INPUTPATH is empty, skipping"
            ((counter++))
            continue
        fi
        
        OUTPUTFIE=$paper_fold/reference.grobid.tei.xml
        if [ ! -e "$OUTPUTFIE" ]; then
            grobid_client --input $paper_fold processCitationList
        else
            echo "File $OUTPUTFIE already exists, skipping"
            
        fi
        
        # python python_script/reference_reterive/parser_reference_grobid_result.py $dir $ROOT/unprocessed_json
        OUTPUTFIE=$paper_fold/reference.structured.anystyle.jsonl
        if [ ! -e "$OUTPUTFIE" ]; then
            anystyle -f json parse $texfilepath > $OUTPUTFIE
        else
            echo "File $OUTPUTFIE already exists, skipping"
     
        fi
        

        ((counter++))

    fi

    # Increment the counter
    ((counter++))

done < "$filelist"