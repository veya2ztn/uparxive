#!/bin/bash

# Check if the correct number of arguments are provided
if [ "$#" -ne 4 ]; then
    echo "You need to supply a filelist and an index and the engine type"
    exit 1
fi

# Assign the first argument to a variable
filelist=$1

# Assign the second argument to a variable and multiply by 100
chunk_size=$3
index=$(($2*$chunk_size))
engine=$4
# Calculate the end index
end_index=$(($index+$chunk_size))

# Initialize a counter
counter=0
ROOT=$(dirname $filelist)
# Read the filelist line by line
while IFS= read -r dir
do
    # If the counter is greater than or equal to the index and less than the end_index
    if [ "$counter" -ge "$index" ] && [ "$counter" -lt "$end_index" ]; then
        texfilepath=$ROOT/unprocessed_json/$dir/reference.structured.jsonl
        echo "===>$texfilepath"
        paper_fold=$(dirname $texfilepath)
        tex_fold=$(dirname $paper_fold)
        ROOTDIR=$(dirname $tex_fold)
        OUTPUTFIE=$paper_fold/reference.es_$engine.json

        if [ -e "$OUTPUTFIE" ]; then
            echo "File $OUTPUTFIE already exists, skipping"
            ((counter++))
            continue
        fi
        
        python python_script/reference_reterive/citation_string_to_reference.py $texfilepath $OUTPUTFIE $engine
            
        
    fi

    # Increment the counter
    ((counter++))

done < "$filelist"