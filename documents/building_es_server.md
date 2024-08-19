> This article instruct you to build the advanced search engineer via [Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/elasticsearch-intro.html)

## Introduction

When building the uparxive dataset, we need retreive the paper object (i.e. the identity sign like doi for the paper) through only the bibgraphy. For example, we need locate the paper by the bibitem string: 

```
C. Szegedy , 2015 IEEE Conference on Computer Vision and Pattern Recognition (CVPR). Jun. 2015.
```

This paper is identified at 

```
{
        "retrieved_level": 5,
        "candidate": {
            "unique_id.doi": "10.1109/cvpr.2015.7298594",
            "unique_id.arxiv": "1409.4842",
            "unique_id.dblp": "conf/cvpr/szegedyljsraevr15",
            "unique_id.mag": "2950179405",
            "title": "Going deeper with convolutions",
            "journal_volume": null,
            "journal_page": "1-9",
            "year": 2014,
            "publisher": "IEEE",
            "content": null,
            "author.0": "C. Szegedy",
            "author.1": "W. Liu",
            "author.2": "Y. Jia",
            "journal": "2015 ieee conference on computer vision and pattern recognition (cvpr)",
            "short_content": "C. Szegedy , 2015 IEEE Conference on Computer Vision and Pattern Recognition (CVPR). Jun. 2015.",
            "score": 1,
            "from_structure": "anystyle"
        }
    },
```

---

For convinece and low frequency, one may refer this requirement to [Crossref](https://www.crossref.org/), [Semantic Scholar](https://www.semanticscholar.org/) and [OpenAlex](https://openalex.org/). Or use [Google Scholar ](https://scholar.google.com/)( or use [SerpAPI ](https://serpapi.com/google-scholar-api))

At uparxive senerio, we need search around 10M query thus which may not suitable for this case.

[Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/elasticsearch-intro.html) is the most popular and power serach backend around the world, another choose is [Manticore Search](https://manticoresearch.com/). Recently, [Typesense](https://typesense.org/) become another ideal candidate.

Anyway, in this article, we focus Elasticsearch

## Step by Step

- Install [Elasticsearch](https://www.elastic.co/guide/en/elasticsearch/reference/current/elasticsearch-intro.html)

  - I recommand you use Docker `docker pull docker.elastic.co/elasticsearch/elasticsearch:8.12.1`
- Collect metadata: after setup the ES server, your just need write data for [Crossref](https://www.crossref.org/), [Semantic Scholar](https://www.semanticscholar.org/) and [OpenAlex](https://openalex.org/)

  - check `uparxive\build_es_database` for example
- Deploy Elasticsearch

  > Elasticsearch may easily allocate whole the CPU resource when high concurrent queries. You may need deploy it at other CPU node without recreate the whole database. May [Snapshot and restore | Elasticsearch Guide [8.15]](https://www.elastic.co/guide/en/elasticsearch/reference/current/snapshot-restore.html) help you.
  >

  I also provide a private snapshot at `aws s3 --endpoint-url=http://10.140.27.254:80 ls s3://Elasticsearch_Snapshot/PaperAndShort_citation.ES.tar` (158G)

  A fast setup script belowLOCAL_ELASTIC_DOCKER_TAR=xxxxxxxxxxxxxxxxx

```
LOCAL_ELASTIC_SNAPSHOT_PATH=xxxxxxxxxxxxxxxxxxxxxx
LOCAL_ELASTIC_INSTALL_DIR=xxxxxxxxxxxxxxxxxx
mkdir -p $LOCAL_ELASTIC_INSTALL_DIR/repo/
sudo chmod -R 777 $LOCAL_ELASTIC_INSTALL_DIR
sudo chmod 777 /var/run/docker.sock
docker load -i $LOCAL_ELASTIC_DOCKER_TAR ## or docker pull docker.elastic.co/elasticsearch/elasticsearch:8.12.1
docker network create elastic
docker run --name elasticsearch --net elastic -p 0.0.0.0:9200:9200 -p 0.0.0.0:9300:9300 \
-v /nas/zhangtianning.di/elasticsearch.yml:/usr/share/elasticsearch/config/elasticsearch.yml \
-v $LOCAL_ELASTIC_INSTALL_DIR:/var/lib/elasticsearch -e "discovery.type=single-node" \
-t -d docker.elastic.co/elasticsearch/elasticsearch:8.12.1
### setup once to create the snapshot file
### then shut doen
docker stop elasticsearch; docker rm elasticsearch; 
### then move the snapshot into 
tar -cf $LOCAL_ELASTIC_SNAPSHOT_PATH
mv elasticsearch/data/repo/* $LOCAL_ELASTIC_INSTALL_DIR/repo/
#rm -r nvme 
sudo chown -R sunhongbin:root $LOCAL_ELASTIC_INSTALL_DIR
curl -X PUT "localhost:9200/_snapshot/digital_resource" -H "Content-Type: application/json" -d'
{
  "type": "fs",
  "settings": {
    "location": "/var/lib/elasticsearch/repo","compress": true
  }
}'
## do next step until this pass
curl -X POST "localhost:9200/_snapshot/digital_resource/_verify?pretty"
curl -X GET "localhost:9200/_snapshot/digital_resource/_all?pretty" ### if `s2-papers-v2.1` exists, then it is successful
curl -X POST localhost:9200/_snapshot/digital_resource/20240320:crf+ss+arxiv/_restore

### after you exec above line, the ES will restore the database from snapshot, please wait, it usuallly take very long time
### eval the building via follow curl 
curl -X GET "http://localhost:9200/integrate20240311/_search" -H 'Content-Type: application/json' -d'
{
  "query": {
    "bool": {
      "should": [
        {
          "multi_match": {
            "query": "L. Nieto",
            "fields": ["author.0", "author.1", "author.2"],
            "type": "best_fields"
          }
        },
        {
          "multi_match": {
            "query": "N. Atakishiyev",
            "fields": ["author.0", "author.1", "author.2"],
            "type": "best_fields"
          }
        },
        {
          "multi_match": {
            "query": "S. Chumakov",
            "fields": ["author.0", "author.1", "author.2"],
            "type": "best_fields"
          }
        },
        {
          "multi_match": {
            "query": "31",
            "fields": ["journal_volume"],
            "type": "best_fields"
          }
        },
        {
          "multi_match": {
            "query": "3875",
            "fields": ["journal_page"],
            "type": "best_fields"
          }
        },
        {
          "multi_match": {
            "query": "J. Phys. A",
            "fields": ["journal"],
            "type": "best_fields"
          }
        },
        {
          "multi_match": {
            "query": 1998,
            "fields": ["year"],
            "type": "best_fields"
          }
        }
      ]
    }
  },
  "size": <size>
}'

### ---> this is command to delete snapshot  `curl -X DELETE localhost:9200/20240320:crf+ss+arxiv`
```
