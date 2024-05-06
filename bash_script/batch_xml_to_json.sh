
# #taskset -c $CPU

CHUNKSIZE=200
for ((CPU=0; CPU<CHUNKSIZE; CPU++));
do
    nohup taskset -c $CPU python /home/zhangtianning.di/projects/unique_data_build/python_script/xml_to_json.py --root $1 --index_part $CPU --num_parts $CHUNKSIZE --passNote --redo > ~/tmp/log/convert/thread.$CPU.log&
done 