
#STARTINDEX=$1
ROOTFILE=$1 #/nvme/zhangtianning.di/sharefold/whole_arxiv_all_files/analysis/should_reterive_reference.filelist
STARTINDEX=0
CHUNKSIZE=100
for ((CPU=0; CPU<$CHUNKSIZE; CPU++));
do
    #PrefixFlag="nohup taskset -c $CPU  python ~/projects/unique_data_build"
    PostFlag="--root $ROOTFILE --index_part $(($STARTINDEX+$CPU)) --num_parts $CHUNKSIZE "
    
    # nohup python ~/projects/unique_data_build/uparxive/reference_reterive/analysis_citation_reterive.py --root /nvme/zhangtianning.di/sharefold/whole_arxiv_all_files/should_reterive_reference.filelist --index_part $CPU --num_parts $CHUNKSIZE > log/convert/thread.$CPU.log&
    

    # nohup taskset -c $CPU  python ~/projects/unique_data_build/uparxive/reference_reterive/mevrge_anystyle_and_grobid_result.py $PostFlag > ~/tmp/log/convert/thread.$CPU.log&

    # nohup taskset -c $CPU python ~/projects/unique_data_build/python_script/parse_citation.py --mode grobid --root /nvme/zhangtianning.di/sharefold/whole_arxiv_all_files/should_reterive_reference.grobid.filelist --index_part $CPU --num_parts $CHUNKSIZE > log/convert/thread.$CPU.log&
    
    nohup python python_script/generate_file_level_metadata.py $CPU $CHUNKSIZE > ~/tmp/log/convert/thread.$CPU.log&
    #nohup taskset -c $CPU  python ~/projects/unique_data_build/uparxive/reference_reterive/parser_reference_grobid_result.py $PostFlag > ~/tmp/log/convert/thread.$CPU.log&

    # nohup taskset -c $CPU python ~/projects/unique_data_build/uparxive/reference_reterive/split_concencated_reference.py \
    # --root /nvme/zhangtianning.di/sharefold/whole_arxiv_all_files/productive_valid_file_list.unarxive.arxivids \
    # --datapath /nvme/zhangtianning.di/sharefold/whole_arxiv_all_files/ \
    # --index_part $CPU --num_parts $CHUNKSIZE > ~/tmp/log/convert/thread.$CPU.log&
    
    #nohup taskset -c $CPU python  ~/projects/unique_data_build/uparxive/xml_to_json/xml_to_dense_text.py --root /nvme/zhangtianning.di/sharefold/whole_arxiv_all_files/archive_xml.filelist --index_part $CPU --num_parts $CHUNKSIZE -n --redo > log/convert/thread.$CPU.log&
    
    #nohup python ~/projects/unique_data_build/uparxive/tex_to_xml/find_the_root_file_of_a_tex_project.py --root /nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/unprocessed_tex --index_part $CPU --num_parts $CHUNKSIZE > log/convert/thread.$CPU.log&
    
    #nohup taskset -c $CPU  python unarxive_to_uparxive.py $CPU $CHUNKSIZE > log/convert/thread.$CPU.log& 
    
    #nohup python uparxive/tex_to_xml/standalize_tex.py --root /nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/analysis/tex_to_xml.clean.filelist --index_part $CPU --num_parts $CHUNKSIZE > log/convert/thread.$CPU.log&
    #nohup python uparxive/tex_to_xml/find_the_root_file_of_a_tex_project.py --root /nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/analysis/base.arxivids --index_part $CPU --num_parts $CHUNKSIZE > log/convert/thread.$CPU.log&
done 

