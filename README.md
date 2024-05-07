# Uparxive

The [uparxive](https://github.com/LLM4Science/unique_data_build) aims to provide a llm-friendly dataest for the whole arxiv .tex source. A similiar dataset is the [unarxive](https://github.com/IllDepence/unarXive), while the uparxvie use a different tool chain.

The Uparxive dataset is stored in `.json` format, which can be seamlessly converted into Markdown `.md` format.

### Format Rules

The Uparxive dataset adheres to the following rules:

- **Tables and Figures**: Elements enclosed within `\begin{table} \end{table}` and `\begin{figure} \end{figure}` tags are extracted and appended at the end of the document for clarity and organization.

- **Citations and References**: Citations (`\cite{}`) and references (`\ref{}`) are converted to more explicit forms to improve readability. Examples include:
  - Direct mentions: `(See [Ref. [1,2] of ArXiv.1512.03385])`
  - Contextual references: `in [Ref. [1,2] of ArXiv.1512.03385]`
  - Equation/Section/Figures/Tables references: `in [Equation [1] of ArXiv.1512.03385]`, depending on the usage context.
  
- **Mathematical Notations**:
  - **In-line Math**: Single dollar signs `$` are used for in-line mathematical expressions, e.g., `$\alpha$`.
  - **Block Math**: Double dollar signs `$$` denote block mathematical expressions, e.g., `$$\mathbf{y}=\mathcal{F}(\mathbf{x},\{W_{i}\})+\mathbf{x}.$$`

# Download Url
 - uparxive[content only]
 - uparxive[with Reference]
 - upar5iv[content only] 
 - upar5iv[content only] 

# Build from arxiv source

To effectively collect and process data from the arXiv source, follow the outlined tool chain and resources provided below:

### Tools and Resources for Data Collection

#### 1. **Download Arxiv Source Files**
   - **arXiv Bulk Data Access**: Access and download bulk data directly from arXiv using the AWS S3 `request-payer` dataset. Detailed instructions and access points can be found here: [arXiv Bulk Data Access](https://info.arxiv.org/help/bulk_data.html).
   - **arXiv API**: For more specific data needs or metadata, use the arXiv API. Documentation and usage guidelines are available here: [arXiv API](https://info.arxiv.org/help/api/index.html).
     - **Important Note**: When crawling arXiv source files, ensure to use `export.arxiv.org` instead of the official `arxiv.org` domain to avoid overloading the main site.

#### 2. **Python Wrapper for arXiv API**
   - To simplify API interactions, consider using the [`arxiv.py`](https://github.com/lukasschwab/arxiv.py) Python library. This wrapper facilitates easier querying and data retrieval from the arXiv API.

#### 3. **HTML Packed Dataset**
   - **Update as of 2025.04.30**: Deyan Ginev (@Deyan) has published an HTML-packed arXiv dataset, known as [ar5iv](https://sigmathling.kwarc.info/resources/ar5iv-dataset-2024/). This dataset provides HTML files that are more friendly for data extraction aimed at language model training or other NLP tasks.

### Starndard Usage:
obtain the `.json` format data
- Compile the `.tex` file to `.xml` file
  - [LaTeXML](https://dlmf.nist.gov/LaTeXML/) 
  - `python python_script/tex_to_xml.py --root [SourPath]`
- Convert the format `.xml` file to `.json` or `.md` file
  - ``python python_script/xml_to_json.py --root [SourPath]``
- *Update 2025.04.30*: [html_to_dense_text.py](https://github.com/LLM4Science/unique_data_build/blob/main/uparxive/xml_to_json/html_to_dense_text.py) aim to convert the `ar5iv` dataset from `html` format to llm-friendly data.
  - `python python_script/html_to_json.py --root [SourPath]`



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
    

