> This article instruct you how to build the unique doi engine to its metadata or its alias via Redis

## Introduction

One paper on the Internet my have many alias, for example

- paper title
- arxiv id
- Digital Object Identifier(DOI)
- Publisher Code

Currently, many provider like [Crossref](https://www.crossref.org/), [Semantic Scholar](https://www.semanticscholar.org/) and [OpenAlex](https://openalex.org/) can help you find whole the alias of one unique paper.  This is the most convince way that user only need to query their api and collect response.

For zero latency and fast paper analysis, one may need collect their metadata bulk such as

- openalex snapshot: [official page](https://docs.openalex.org/download-all-data/download-to-your-machine) or the [aws s3 opendata](https://registry.opendata.aws/openalex/)
- crossref snapshot: [Metadata Retrieval](https://www.crossref.org/documentation/retrieve-metadata/) or the [aws s3 request-payer dataset](https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-public-data-files-and-plus-snapshots/)
- arxive metadata:  [arxiv_dataset](https://huggingface.co/datasets/arxiv_dataset)

to build a `Alias Identity` in local machine.

This is the goal about this article.

## Step by step

1. Download the metadata from website.
2. Install [Redis](https://redis.io/)
3. Start Redis Server

   ```bash
   redis-server --dir /temp/redis_cache
   ```
   > I recommand assign the redis cache `--dir` for reusing.
   >
4. Create the `paper_identity.jsonl`

   An inner object at  `aws s3 --endpoint-url=http://10.140.27.254:80 ls s3://OpenAlex/paper_identity.jsonl` )

   There are many ways to build this, you can refer `uparxive/build_redis_database` and `notebook/obstract_necessary_information_from_origin.ipynb`

   each line is the `{provider: provider_id}`

   ```
   {"openalex": "W4312243914", "doi": "10.3030/750533"}
   {"openalex": "W4312302063", "doi": "10.3030/657904"}
   {"openalex": "W4312372362", "doi": "10.3030/800242"}
   {"openalex": "W4312399684", "doi": "10.3030/703204"}
   {"openalex": "W4312556060", "doi": "10.3030/660480"}
   {"openalex": "W4312786850", "doi": "10.3030/704698"}
   {"openalex": "W4312935697", "doi": "10.3030/660883"}
   {"openalex": "W4313013700", "doi": "10.3030/702880"}
   {"openalex": "W4313017406", "doi": "10.3030/661646"}
   {"openalex": "W4313163147", "doi": "10.3030/701704"}
   ...................................................
   ```
   Then add it into redis via `uparxive\build_redis_database\write_data_into_redis.py`

   > You may want to parallel write data to redis. May script in `bash_script/batch_create_redis_database.sh` and `bash_script/batch_write_data_into_redis.sh` help you.
   >
5. use it~

   ```python
   import redis
   redis_host = "localhost"
   redis_port = 6379
   redis_password = ""
   r = redis.StrictRedis(host=redis_host, port=redis_port, password=redis_password, decode_responses=True)
   ```
