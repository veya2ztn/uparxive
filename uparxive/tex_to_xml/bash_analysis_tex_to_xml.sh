XMLPATH=$1
mode=$2
CHUNKSIZE=100
for ((CPU=0; CPU<CHUNKSIZE; CPU++));
do
    nohup python python_script/tex_to_xml/analysis_tex_to_xml.py --root $XMLPATH --index_part $CPU --num_parts $CHUNKSIZE --mode $mode > log/convert/thread.$CPU.log&
   
done 

# 