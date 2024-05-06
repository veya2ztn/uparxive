# Uparxive

The [uparxive](https://github.com/LLM4Science/unique_data_build) aims to provide a llm-friendly dataest for the whole arxiv .tex source. A similiar dataset is the [unarxive](https://github.com/IllDepence/unarXive), while the uparxvie use a different tool chain.

# Download Url
 - uparxive[content only]
 - uparxive[with Reference]
 - upar5iv[with Reference]

# Collect data from arxiv source

If you want to collect the data from arxiv source by yourself, here is the tool chain we used:
- Download Arxiv Source Files
  - [arXiv Bulk Data Access](https://info.arxiv.org/help/bulk_data.html) from [aws s3 request-payer dataset](https://info.arxiv.org/help/bulk_data_s3.html)
  - [arXiv Api](https://info.arxiv.org/help/api/index.html)
    > Notice please crawel the arxiv source files from `export.arxiv.org` rather than the official `arxiv.org`

    > You may turn to the [arxiv.py](https://github.com/lukasschwab/arxiv.py)

- *Update 2025.04.30*: [@Deyan](https://github.com/dginev) had publish a nice `html` pack arxiv dataset, see [ar5iv](https://sigmathling.kwarc.info/resources/ar5iv-dataset-2024/). We can directly use the `html` file to extract the llm-friendly data.

### Starndard Usage:
obtain the `.json` format data
- Compile the `.tex` file to `.xml` file
  - [LaTeXML](https://dlmf.nist.gov/LaTeXML/)
- Convert the format `.xml` file to `.json` or `.md` file
  - [xml_to_dense_text.py](https://github.com/LLM4Science/unique_data_build/blob/main/uparxive/xml_to_json/xml_to_dense_text.py) 
- *Update 2025.04.30*: [html_to_dense_text.py](https://github.com/LLM4Science/unique_data_build/blob/main/uparxive/xml_to_json/html_to_dense_text.py) aim to convert the `ar5iv` dataset from `html` format to llm-friendly data.


### Advanced Usage: Referecne Retrieve: 
Turn to the [Citation Retreive](https://github.com/LLM4Science/unique_data_build) for more details

- **Resource**: in order to retrieve the digital url for each citation string, you need collect the citation metadata from 
  - openalex snapshot: [official page](https://docs.openalex.org/download-all-data/download-to-your-machine) or the [aws s3 opendata](https://registry.opendata.aws/openalex/)
  - crossref snapshot: [Metadata Retrieval](https://www.crossref.org/documentation/retrieve-metadata/) or the [aws s3 request-payer dataset](https://www.crossref.org/documentation/retrieve-metadata/rest-api/tips-for-using-public-data-files-and-plus-snapshots/)
  - arxive metadata:  [arxiv_dataset](https://huggingface.co/datasets/arxiv_dataset)

- **Tool Chain**:
  - Citation Structure Tool:
    - [Anystyle](https://github.com/inukshuk/anystyle)
    - [Grobid](https://github.com/kermitt2/grobid)
  - Citation Retreive Engine:
    - [Elasticsearch](https://github.com/elastic/elasticsearch)
  - [Citation_Retreive_Script](https://github.com/LLM4Science/unique_data_build/blob/main/uparxive/reference_reterive/citation_string_to_reference.py)
    

