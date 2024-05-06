# Check if the file path argument is provided
if [ -z "$1" ]; then
    echo "Error: No file path provided. Please provide a file path as the first argument."
    exit 1
fi
FILEPATH=$1 # #/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_cs/xml_to_json.pass.filelist
CPU_NUM=100 # Automatically get the number of CPUs
LINE_COUNT=$(wc -l < "$FILEPATH") # Get the number of lines in the file
CHUNKSIZE=$(echo "(($LINE_COUNT + $CPU_NUM - 1) / $CPU_NUM)" | bc)
for ((CPU=0; CPU<CPU_NUM; CPU++));
do
    nohup bash bash_script/parser_reference.sh $FILEPATH $CPU $CHUNKSIZE > log/convert/thread.$CPU.log&
done 
#