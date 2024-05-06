conda init bash; conda activate unarxive
cd /nvme/zhangtianning.di/elasticsearch/
docker stop elasticsearch
docker rm elasticsearch
sudo rm -r repo
aws s3 --endpoint-url=http://10.140.2.254:80 cp s3://TEST/PaperAndShort_citation.ES.tar ./
sudo tar -xf PaperAndShort_citation.ES.tar 
