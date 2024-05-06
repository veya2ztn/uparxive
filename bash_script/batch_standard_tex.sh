CHUNKSIZE=100
for ((CPU=0; CPU<CHUNKSIZE; CPU++));
do
    nohup python python_script/tex_to_xml/standalize_tex.py --root $1 --index_part $CPU --num_parts $CHUNKSIZE --ForceQ > log/convert/thread.$CPU.log&
done 