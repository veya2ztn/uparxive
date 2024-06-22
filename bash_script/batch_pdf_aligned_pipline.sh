
if [ -z "$1" ]; then
    echo "Error: No file path provided. Please provide a file path as the first argument."
    exit 1
fi

FILEPATH=$1 # Path to the file
START=0
CPU_NUM=200 # Automatically get the number of CPUs
CHUNKSIZE=200
LINE_COUNT=$(wc -l < "$FILEPATH") # Get the number of lines in the file
CHUNKSIZE=$(echo "(($LINE_COUNT + $CPU_NUM - 1) / $CPU_NUM)" | bc)

for ((CPU=0; CPU<CHUNKSIZE; CPU++));
do
    nohup bash /home/zhangtianning.di/projects/unique_data_build/bash_script/pdf_alignment_pipline.sh $FILEPATH $(($CPU+$START)) $CHUNKSIZE > log/convert/thread.$CPU.log&
done 