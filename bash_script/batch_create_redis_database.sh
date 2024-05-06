CPU_NUM=10 # Automatically get the number of CPUs
for ((CPU=0; CPU<CPU_NUM; CPU++));
do
    nohup python python_script/build_redis_database/write_data_into_redis.py $CPU $CPU_NUM > log/convert/thread.$CPU.log&
done 