CPU_NUM=100 # Automatically get the number of CPUs
for ((CPU=1; CPU<CPU_NUM; CPU++));
do
    nohup python python_script/build_redis_database/update_identity_from_semantic_scholar.py $CPU $CPU_NUM > log/convert/thread.$CPU.log&
done 