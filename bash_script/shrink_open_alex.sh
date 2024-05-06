#!/bin/bash

# Check if the correct number of arguments are provided
if [ "$#" -ne 3 ]; then
    echo "You need to supply a filelist and an index"
    exit 1
fi

# Assign the first argument to a variable
filelist=$1

# Assign the second argument to a variable and multiply by 100
chunk_size=$3
index=$(($2*$chunk_size))

# Calculate the end index
end_index=$(($index+$chunk_size))

# Initialize a counter
counter=0

# Read the filelist line by line
while IFS= read -r filepath
do
    # If the counter is greater than or equal to the index and less than the end_index
    if [ "$counter" -ge "$index" ] && [ "$counter" -lt "$end_index" ]; then
        echo "===>$filepath"
        absolute_filepath=$(readlink -f $filepath)
        datefold=$(dirname $absolute_filepath)
        date=$(basename $datefold)
        worksfold=$(dirname $datefold)
        ROOTDIR=$(dirname $worksfold)
        filename=`basename $filepath .gz`
        OUTPUTDIR=$ROOTDIR/whole_paper_information/$date/$filename
        OUTPUTPATH="$OUTPUTDIR"/paper_identity.jsonl
        if [ -e $OUTPUTPATH ]; then
            echo "File $OUTPUTPATH already exists, skipping"
            ((counter++))
            continue
        fi
        echo "====> Save to $OUTPUTPATH"    
        python data/openalex/extract_information.py $absolute_filepath $OUTPUTDIR
        
        
    fi

    # Increment the counter
    ((counter++))

done < "$filelist"