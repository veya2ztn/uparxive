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
while IFS= read -r texfilepath #dir ## each input a complete path like /nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_old_quant_ph/unprocessed_xml/2302.00976/Nogotheorem_Arxiv.xml
do
    # If the counter is greater than or equal to the index and less than the end_index
    if [ "$counter" -ge "$index" ] && [ "$counter" -lt "$end_index" ]; then
        paper_fold=$(dirname $texfilepath)
        tex_id=$(basename $paper_fold)
        ROOTDIR=$(dirname $paper_fold)
        ROOTDIR=$(dirname $ROOTDIR)
        #echo $paper_fold $tex_fold
        texfilename=`basename $texfilepath .xml`
        OUTPUTFIE=$ROOTDIR/unprocessed_json/$tex_id/$tex_id.retrieved.json
        
        echo "===>$texfilepath ==> $OUTPUTFIE"
        OUTPUTDIR=$(dirname $OUTPUTFIE)
        if [ -e "$OUTPUTFIE" ]; then
            echo "File $OUTPUTFIE already exists, skipping"
            ((counter++))
            continue
        fi
        
        NEEDFILE=$ROOTDIR/unprocessed_json/$tex_id/reference.es_semantic_scholar.json.done
        if [ ! -e "$NEEDFILE" ]; then
            echo "File $NEEDFILE not exists, skipping"
            ((counter++))
            continue
        fi
        
        MUSTEMPTYFILE=$ROOTDIR/unprocessed_json/$tex_id/reference.txt
        if [ -s "$INPUTPATH" ]; then
            echo "File $INPUTPATH is not empty, skipping"
            ((counter++))
            continue
        fi
        
        python xml_to_dense_text.py $texfilepath $OUTPUTDIR 1
        
    fi

    # Increment the counter
    ((counter++))

done < "$filelist"