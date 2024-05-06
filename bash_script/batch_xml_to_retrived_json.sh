
# Check if the file path argument is provided
if [ -z "$1" ]; then
    echo "Error: No file path provided. Please provide a file path as the first argument."
    exit 1
fi

FILEPATH=$1 # Path to the file
CPU_NUM=200 # Automatically get the number of CPUs
LINE_COUNT=$(wc -l < "$FILEPATH") # Get the number of lines in the file
CHUNKSIZE=$(echo "(($LINE_COUNT + $CPU_NUM - 1) / $CPU_NUM)" | bc)
for ((CPU=0; CPU<CPU_NUM; CPU++));
do
    nohup taskset -c $CPU bash bash_script/xml_to_retrived_json_chunk.sh $FILEPATH $CPU $CHUNKSIZE > log/convert/thread.$CPU.log&
done 