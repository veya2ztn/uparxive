CHUNKSIZE=5
for CPU in {0..101};
do
    nohup bash bash_script/shrink_open_alex.sh openalex.list.shuffle $CPU $CHUNKSIZE > log/convert/thread.$CPU.log&
done 