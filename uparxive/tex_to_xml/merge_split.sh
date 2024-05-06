ROOT=/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/analysis.tex_to_xml

for name in emptydir error multilog success warning emptylog timeout nolog noxml fail_reason nodir NoXML;
do
    splitdir=$ROOT/tex_to_xml.$name.filelist.split
    # do only when the splitdir exists
    if [ -d $splitdir ]; then
        cat $splitdir/* > $ROOT/tex_to_xml.$name.filelist
        rm -r $splitdir
        wc -l $ROOT/tex_to_xml.$name.filelist
    fi
    
done 
