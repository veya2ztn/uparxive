CHUNKSIZE=60
for CPU in {0..200};
do
    nohup taskset -c $CPU python write_data_into_redis.py $CPU 200 > log/convert/thread.$CPU.log&
done 