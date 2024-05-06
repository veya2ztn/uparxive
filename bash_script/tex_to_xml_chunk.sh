#!/bin/bash

monitor_program() {
  local pid=$1
  local logfile=$2
  tail -f "$logfile" | while read -r line; do
    echo "$line"
    if echo "$line" | grep -q "Error"; then
      echo "======================================"
      echo "Error detected. Killing the program..."
      echo "======================================"
      kill "$pid"
      pkill -P "$pid" # Kill subprocesses if any
      break
    fi
  done
}
# Check if the correct number of arguments are provided
if [ "$#" -ne 3 ]; then
    echo "You need to supply a filelist and an index an and chunk_size"
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
        dir=`basename $paper_fold`
        ROOTDIR=$(dirname $paper_fold)
        ROOTDIR=$(dirname $ROOTDIR)
        LOCKFILE=$ROOTDIR/unprocessed_lock/$dir.lock

        # if [ -e "$LOCKFILE" ]; then
        #     #echo "File $LOCKFILE already exists, skipping"
        #     ((counter++))
        #     continue
        # fi
        # touch $LOCKFILE


        texfilename=`basename $texfilepath .tex`
        
        #for texfilepath in $(find $ROOTDIR -type f -name "*.tex"); do
        OUTPUTFIE=$ROOTDIR/unprocessed_xml/$dir/$texfilename.xml
        LOGFILE=$ROOTDIR/unprocessed_xml/$dir/$texfilename.log
        #echo "=>$paper_fold ==> $texfilename.tex ===> $OUTPUTFIE"
        if [ ! -e "$OUTPUTFIE" ]; then
            #latexml --noparse --nocomments --includestyles --log="$LOGFILE" --path="$paper_fold" --dest="$OUTPUTFIE" "$texfilename.tex"
            #latexmlc --noparse --nocomments --includestyles --nopictureimages --nographicimages --nosvg --timeout 360 --log="$LOGFILE" --path="$paper_fold" --dest="$OUTPUTFIE" "$texfilename.tex" 
            latexmlc --noparse --nocomments --includestyles --nopictureimages --nographicimages --nosvg \
                     --timeout 360 --log="$LOGFILE" --path="$paper_fold" \
                     --dest="$OUTPUTFIE" "$texfilepath" &
            sleep 1
            pid=$!
            
            monitor_program "$pid" "$LOGFILE" &
            wait "$pid"
            result=$?
            
            pkill -P $$ tail  # kill the tail process if latexmlc finishes without errors
            if [ $result -ne 0 ]; then
                echo "Conversion complete: Quick End error" >> "$LOGFILE"
            fi
        fi

    fi

    ((counter++))
    if [ "$counter" -ge "$end_index" ]; then
        break
    fi
done < "$filelist"

echo "\n"