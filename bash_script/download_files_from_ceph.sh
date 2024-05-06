#!/bin/bash

# Check if the correct number of arguments are provided
if [ "$#" -ne 3 ]; then
    echo "You need to supply a filelist and an index"
    exit 1
fi

# Assign the first argument to a variable
filelist=$1
chunk_size=$3
index=$(($2*$chunk_size))

# Calculate the end index
end_index=$(($index+$chunk_size))
# end_index=$(($end_index-80))
# Initialize a counter
counter=0
ROOTDIR=$(dirname $filelist)
# Read the filelist line by line
while IFS= read -r filepath
do
    # If the counter is greater than or equal to the index and less than the end_index
    if [ "$counter" -ge "$index" ] && [ "$counter" -lt "$end_index" ]; then
        
        absfilepath=$ROOTDIR/arxiv_id_in_ceph_list/$filepath
        echo "===>$absfilepath"
        rclone --progress --files-from-raw $absfilepath --no-traverse copy cephhs:public-dataset/arxiv-uncompressed unprocessed_tex/
        
        
    fi

    # Increment the counter
    ((counter++))

done < "$filelist"