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
processed=0
# Read the filelist line by line
while IFS= read -r texfilepath #dir
do
    # If the counter is greater than or equal to the index and less than the end_index
    if [ "$counter" -ge "$end_index" ]; then
        break
    fi
    if [ "$counter" -ge "$index" ] && [ "$counter" -lt "$end_index" ]; then

        #ROOTDIR=data/whole_arxiv_quant_ph/unprocessed_xml/$dir
        # for texfilepath in $(find $ROOTDIR -type f -name "*.xml"); do
        
        # absolute_texfilepath=$(readlink -f $texfilepath)
        # paper_fold=$(dirname $absolute_texfilepath)
        # tex_fold=$(dirname $paper_fold)
        # ROOTDIR=$(dirname $tex_fold)
        # #echo $paper_fold $tex_fold
        # texfilename=`basename $texfilepath .xml`
        # OUTPUTFIE=$ROOTDIR/unprocessed_json/$dir/$dir.json
        # echo "===>$texfilepath ==> $OUTPUTFIE"
        # if [ -e "$OUTPUTFIE" ]; then
        #     echo "File $OUTPUTFIE already exists, skipping"
        #     ((counter++))
        #     continue
        # fi
        # OUTPUTDIR=$(dirname $OUTPUTFIE)
        # python xml_to_dense_text.py $texfilepath $OUTPUTDIR
        #done
        #echo $texfilepath

        ((processed++))
        percent=$((100 * processed / chunk_size))
        bar=$(printf '%*s' $((percent / 2)) '' | tr ' ' '=')
        printf "\rProgress: [%-50s] %d%% (%d/%d)" "$bar" $percent $processed $chunk_size


        paper_fold=$(dirname $texfilepath)
        tex_id=$(basename $paper_fold)
        ROOTDIR=$(dirname $paper_fold)
        ROOTDIR=$(dirname $ROOTDIR)
        #echo $paper_fold $tex_fold
        texfilename=`basename $texfilepath .xml`
        OUTPUTFIE=$ROOTDIR/unprocessed_json/$tex_id/$tex_id.json
        echo "===>$texfilepath ==> $OUTPUTFIE"
        OUTPUTDIR=$(dirname $OUTPUTFIE)
        if [ -e "$OUTPUTFIE" ]; then
            echo "File $OUTPUTFIE already exists, skipping"
            ((counter++))
            continue
        fi
        
        python xml_to_dense_text.py $texfilepath $OUTPUTDIR
        
    fi

    # Increment the counter
    ((counter++))

done < "$filelist"
echo "done"