# if [ -z "$1" ]; then
#     echo "Error: No file path provided. Please provide a file path as the first argument."
#     exit 1
# fi

# FILEPATH=$1 # Path to the file

# # CPU_NUM=100 # Automatically get the number of CPUs
# # LINE_COUNT=$(wc -l < "$FILEPATH") # Get the number of lines in the file
# # CHUNKSIZE=$(echo "(($LINE_COUNT + $CPU_NUM - 1) / $CPU_NUM)" | bc)
# # for ((CPU=0; CPU<CPU_NUM; CPU++));
# # do
# # nohup bash bash_script/tex_to_xml_chunk.sh $FILEPATH $CPU $CHUNKSIZE > log/convert/thread.$CPU.log&
# # done 
# CPU_NUM=$3
# START=$2
# LINE_COUNT=$(wc -l < "$FILEPATH") # Get the number of lines in the file
# CHUNKSIZE=$(echo "(($LINE_COUNT + $CPU_NUM - 1) / $CPU_NUM)" | bc)
# for ((CPU=0; CPU<200; CPU++));
# do
#     nohup bash /home/zhangtianning.di/projects/unique_data_build/bash_script/tex_to_xml_chunk.sh $FILEPATH $(($CPU+$START)) $CHUNKSIZE > log/convert/thread.$CPU.log&
# done 
START=$2
CHUNKNUM=$3
for ((CPU=0; CPU<200; CPU++));
do
    nohup python /home/zhangtianning.di/projects/unique_data_build/python_script/tex_to_xml.py --root $1 --index_part $(($CPU+$START)) --num_parts $CHUNKNUM --redo > ~/tmp/log/convert/thread.$CPU.log&
    #nohup python /home/zhangtianning.di/projects/unique_data_build/python_script/tex_to_xml/run_tex_to_xml.py --root $1 --index_part 0 --num_parts $CHUNKNUM --shuffle > ~/tmp/log/convert/thread.$CPU.log&
done 