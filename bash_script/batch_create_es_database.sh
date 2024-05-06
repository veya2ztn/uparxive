CPU_NUM=10 # Automatically get the number of CPUs
for ((CPU=0; CPU<CPU_NUM; CPU++));
do
    #nohup python python_script/build_es_database/build_es_async.py  > log/convert/thread.$CPU.log&
    #nohup python python_script/build_es_database/update_es_from_cr_async.py  > log/convert/thread.$CPU.log&
    #nohup python python_script/build_es_database/update_es_citation_via_cr_async.py  > log/convert/thread.$CPU.log&
    nohup python python_script/build_es_database/update_es_from_arxivemetadata.py $CPU $CPU_NUM > log/convert/thread.$CPU.log&
    #nohup python python_script/build_es_database/update_es_citation_via_ss_async.py > log/convert/thread.$CPU.log&
done 