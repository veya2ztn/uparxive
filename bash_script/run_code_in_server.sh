
#ray start --head --resources='{"124": 1}' --port=5005
#conda activate arxive; ray stop; ps -axuf | grep general_task | awk '{print $2}' | xargs -n 1 kill -9
for address in 123 122 121 118 86 87 88 89 90 120 119 ;
do 
    #ssh -t zhangtianning.di@10.140.52.$address "conda activate unarxive; pip install -r /nas/zhangtianning.di/projects/unique_data_build/requirements.txt" &
    #ssh -t zhangtianning.di@10.140.52.$address "conda activate unarxive;pip install beautifulsoup4"&
    #ssh -t zhangtianning.di@10.140.52.$address "docker stop grobid;docker run --rm --init -d --ulimit core=0 --name grobid -p 0.0.0.0:8070:8070 -v /home/zhangtianning.di/grobid.yaml:/opt/grobid/grobid-home/config/grobid.yaml lfoppiano/grobid:0.8.0" &
    #ssh -t zhangtianning.di@10.140.52.$address "sudo rm /tmp/*" &
    ssh -t zhangtianning.di@10.140.52.$address "bash /nas/zhangtianning/killall.sh" &
    #ssh -t zhangtianning.di@10.140.52.$address "bash /nas/zhangtianning/status.sh" &
    ssh -t zhangtianning.di@10.140.52.$address "conda activate unarxive; ray stop; ps -axuf | grep general_task | awk '{print \$2}' | xargs -n 1 kill -9 ;" & 
    #ssh -t zhangtianning.di@10.140.52.$address "conda activate unarxive; ray start --address='10.140.52.124:5005' --resources='{\"$address\": 1}' ; sleep 2; " & 
done

# ssh -t zhangtianning.di@10.140.52.123 'ps -axuf | grep general_task | awk '{print \$2}' | xargs -n 1 kill; conda activate unarxive; ray stop; ray start --address='10.140.52.124:5005' --resources='{"123": 1}''
# ssh -t zhangtianning.di@10.140.52.122 'ps -axuf | grep general_task | awk '{print \$2}' | xargs -n 1 kill; conda activate unarxive; ray stop; ray start --address='10.140.52.124:5005' --resources='{"122": 1}''
# ssh -t zhangtianning.di@10.140.52.121 'ps -axuf | grep general_task | awk '{print \$2}' | xargs -n 1 kill; conda activate unarxive; ray stop; ray start --address='10.140.52.124:5005' --resources='{"121": 1}''
# ssh -t zhangtianning.di@10.140.52.120 'ps -axuf | grep general_task | awk '{print \$2}' | xargs -n 1 kill; conda activate unarxive; ray stop; ray start --address='10.140.52.124:5005' --resources='{"120": 1}''
# ssh -t zhangtianning.di@10.140.52.119 'ps -axuf | grep general_task | awk '{print \$2}' | xargs -n 1 kill; conda activate unarxive; ray stop; ray start --address='10.140.52.124:5005' --resources='{"119": 1}''
# ssh -t zhangtianning.di@10.140.52.118 'ps -axuf | grep general_task | awk '{print \$2}' | xargs -n 1 kill; conda activate unarxive; ray stop; ray start --address='10.140.52.124:5005' --resources='{"118": 1}''
# ssh -t zhangtianning.di@10.140.52.107 'ps -axuf | grep general_task | awk '{print \$2}' | xargs -n 1 kill; conda activate unarxive; ray stop; ray start --address='10.140.52.124:5005' --resources='{"107": 1}''
# ssh -t zhangtianning.di@10.140.52.86  'ps -axuf | grep general_task | awk '{print \$2}' | xargs -n 1 kill; conda activate unarxive; ray stop; ray start --address='10.140.52.124:5005' --resources='{"86": 1}''
# ssh -t zhangtianning.di@10.140.52.87  'ps -axuf | grep general_task | awk '{print \$2}' | xargs -n 1 kill; conda activate unarxive; ray stop; ray start --address='10.140.52.124:5005' --resources='{"87": 1}''
# ssh -t zhangtianning.di@10.140.52.88  'ps -axuf | grep general_task | awk '{print \$2}' | xargs -n 1 kill; conda activate unarxive; ray stop; ray start --address='10.140.52.124:5005' --resources='{"88": 1}''
# ssh -t zhangtianning.di@10.140.52.89  'ps -axuf | grep general_task | awk '{print \$2}' | xargs -n 1 kill; conda activate unarxive; ray stop; ray start --address='10.140.52.124:5005' --resources='{"89": 1}''
# ssh -t zhangtianning.di@10.140.52.90  'ps -axuf | grep general_task | awk '{print \$2}' | xargs -n 1 kill; conda activate unarxive; ray stop; ray start --address='10.140.52.124:5005' --resources='{"90": 1}''


# curl -X DELETE 10.140.52.122:9200/integrate20240311
# curl -X DELETE 10.140.52.122:9200/_snapshot/digital_resource
# curl -X DELETE 10.140.52.122:9200/_snapshot/digital_resource/paper:crf+ss+arxiv

# curl -X DELETE 10.140.52.107:9200/integrate20240311
# curl -X DELETE 10.140.52.107:9200/_snapshot/digital_resource
# curl -X DELETE 10.140.52.107:9200/_snapshot/digital_resource/paper:crf+ss+arxiv

