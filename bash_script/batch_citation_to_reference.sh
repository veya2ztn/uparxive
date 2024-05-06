
# ESINDEX=integrate
# #PARSER=anystyle
# PARSER=grobid
CHUNKSIZE=30
for ((CPU=0; CPU<CHUNKSIZE; CPU++));
do
    nohup  python ~/projects/unique_data_build/python_script/reference_reterive/citation_string_to_reference_async.py \
    --root /nvme/zhangtianning.di/sharefold/whole_arxiv_all_files/analysis.analysis/retreive_reference_result/not_processed.filelist \
    --index_part $CPU --num_parts $CHUNKSIZE \
    > log/convert/thread.$CPU.log&
done 


# for CPU in {0..30};
# do
#     nohup  python python_script/reference_reterive/citation_string_to_reference_async.py \
#     /nvme/zhangtianning.di/sharefold/whole_arxiv_all_cs/analysis.eval_reterive_quality/reterive.remain \
#     /nvme/zhangtianning.di/sharefold/whole_arxiv_all_cs/unprocessed_json sentense 9200 0.7 > log/convert/thread.$CPU.log&
# done 