CHUNKSIZE=100
for ((CPU=0; CPU<CHUNKSIZE; CPU++));
do
    nohup python unarxive_to_uparxive.py $CPU $CHUNKSIZE > log/convert/thread.$CPU.log&
done 