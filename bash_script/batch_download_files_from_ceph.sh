
if [ -z "$1" ]; then
    echo "Error: No file path provided. Please provide a file path as the first argument."
    exit 1
fi

FILEPATH=$1 # Path to the file
CPU_NUM=10 # Automatically get the number of CPUs
LINE_COUNT=$(wc -l < "$FILEPATH") # Get the number of lines in the file
CHUNKSIZE=$(echo "(($LINE_COUNT + $CPU_NUM - 1) / $CPU_NUM)" | bc)

for ((CPU=0; CPU<CPU_NUM; CPU++));
do
    nohup bash ~/projects/unarXive/src/bash_script/download_files_from_ceph.sh $FILEPATH $CPU $CHUNKSIZE > log/convert/thread.$CPU.log&
done 