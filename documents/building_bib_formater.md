> This article aim to help you build the bib parser system. For [Grobid ](https://github.com/kermitt2/grobid)or [Anystyle](https://github.com/inukshuk/anystyle)

# Introduction

The goal for this part is to find a nice solution to parser string bib into json-format.

For example, given bib string

```plaintext
C. Szegedy , 2015 IEEE Conference on Computer Vision and Pattern Recognition (CVPR). Jun. 2015.
```

we want to parser it into `Author`, `title`, `year`, `publish` and etc.

```json
[
    {
        "author": [
            {
                "family": "Szegedy",
                "given": "C."
            }
        ],
        "container-title": "IEEE Conference on Computer Vision and Pattern Recognition (CVPR). Jun",
        "language": "en",
        "type": "paper-conference",
        "issued": {
            "date-parts": [
                [
                    2015
                ]
            ]
        }
    }
```

Currently, I find two solution and use them in cross-validation. Each of them has their own advancement.

After we get the format bib format, we can search them in ES server and retreive the correct paper id. See `reference_retrieve.md`

## Grobid

```bash
pip install grobid-client-python
docker run --rm --init -d --ulimit core=0 --name grobid -p 0.0.0.0:8070:8070 -v grobid.yaml:/opt/grobid/grobid-home/config/grobid.yaml lfoppiano/grobid:0.8.0 
```

default config of grobid has very low concurrency setting, please modify the `grobid.yaml` properly to fit your computer

```yaml
# this is the configuration file for the GROBID instance

grobid:
  # where all the Grobid resources are stored (models, lexicon, native libraries, etc.), normally no need to change
  grobidHome: "grobid-home"

  # path relative to the grobid-home path (e.g. tmp for grobid-home/tmp) or absolute path (/tmp)
  temp: "tmp"
  
  # normally nothing to change here, path relative to the grobid-home path (e.g. grobid-home/lib)
  nativelibrary: "lib"

  pdf:
    pdfalto:
      # path relative to the grobid-home path (e.g. grobid-home/pdfalto), you don't want to change this normally
      path: "pdfalto"
      # security for PDF parsing
      memoryLimitMb: 6096
      timeoutSec: 120

    # security relative to the PDF parsing result
    blocksMax: 200000
    tokensMax: 1000000

  consolidation:
    # define the bibliographical data consolidation service to be used, either "crossref" for CrossRef REST API or 
    # "glutton" for https://github.com/kermitt2/biblio-glutton
    service: "crossref"
    #service: "glutton"
    glutton:
      url: "https://cloud.science-miner.com/glutton"
      #url: "http://localhost:8080" 
    crossref:
      mailto: 
      # to use crossref web API, you need normally to use it politely and to indicate an email address here, e.g. 
      #mailto: "toto@titi.tutu"
      token:
      # to use Crossref metadata plus service (available by subscription)
      #token: "yourmysteriouscrossrefmetadataplusauthorizationtokentobeputhere"

  proxy:
    # proxy to be used when doing external call to the consolidation service
    host: 
    port: 

  # CORS configuration for the GROBID web API service
  corsAllowedOrigins: "*"
  corsAllowedMethods: "OPTIONS,GET,PUT,POST,DELETE,HEAD"
  corsAllowedHeaders: "X-Requested-With,Content-Type,Accept,Origin"

  # the actual implementation for language recognition to be used
  languageDetectorFactory: "org.grobid.core.lang.impl.CybozuLanguageDetectorFactory"

  # the actual implementation for optional sentence segmentation to be used (PragmaticSegmenter or OpenNLP)
  #sentenceDetectorFactory: "org.grobid.core.lang.impl.PragmaticSentenceDetectorFactory"
  sentenceDetectorFactory: "org.grobid.core.lang.impl.OpenNLPSentenceDetectorFactory"
  
  # maximum concurrency allowed to GROBID server for processing parallel requests - change it according to your CPU/GPU capacities
  # for a production server running only GROBID, set the value slightly above the available number of threads of the server
  # to get best performance and security
  concurrency: 256
  # when the pool is full, for queries waiting for the availability of a Grobid engine, this is the maximum time wait to try 
  # to get an engine (in seconds) - normally never change it
  poolMaxWait: 60

  delft:
    # DeLFT global parameters
    # delft installation path if Deep Learning architectures are used to implement one of the sequence labeling model, 
    # embeddings are usually compiled as lmdb under delft/data (this parameter is ignored if only featured-engineered CRF are used)
    install: "../delft"
    pythonVirtualEnv:

  wapiti:
    # Wapiti global parameters
    # number of threads for training the wapiti models (0 to use all available processors)
    nbThreads: 0

  models:
    # we configure here how each sequence labeling model should be implemented
    # for feature-engineered CRF, use "wapiti" and possible training parameters are window, epsilon and nbMaxIterations
    # for Deep Learning, use "delft" and select the target DL architecture (see DeLFT library), the training 
    # parameters then depends on this selected DL architecture 
  
    - name: "segmentation"
      # at this time, must always be CRF wapiti, the input sequence size is too large for a Deep Learning implementation
      engine: "wapiti"
      #engine: "delft"
      wapiti:
        # wapiti training parameters, they will be used at training time only
        epsilon: 0.0000001
        window: 50
        nbMaxIterations: 2000
      delft:
        # deep learning parameters
        architecture: "BidLSTM_CRF_FEATURES"
        useELMo: false
        runtime:
          # parameters used at runtime/prediction
          max_sequence_length: 3000
          batch_size: 1
        training:
          # parameters used for training
          max_sequence_length: 3000
          batch_size: 10

    - name: "fulltext"
      # at this time, must always be CRF wapiti, the input sequence size is too large for a Deep Learning implementation
      engine: "wapiti"
      wapiti:
        # wapiti training parameters, they will be used at training time only
        epsilon: 0.0001
        window: 20
        nbMaxIterations: 1500

    - name: "header"
      engine: "wapiti"
      #engine: "delft"
      wapiti:
        # wapiti training parameters, they will be used at training time only  
        epsilon: 0.000001
        window: 30
        nbMaxIterations: 1500
      delft:
        # deep learning parameters
        architecture: "BidLSTM_ChainCRF_FEATURES"
        #transformer: "allenai/scibert_scivocab_cased"
        useELMo: false
        runtime:
          # parameters used at runtime/prediction
          #max_sequence_length: 510
          max_sequence_length: 3000
          batch_size: 1
        training:
          # parameters used for training
          #max_sequence_length: 510
          #batch_size: 6
          max_sequence_length: 3000
          batch_size: 9

    - name: "reference-segmenter"
      engine: "wapiti"
      #engine: "delft"
      wapiti:
        # wapiti training parameters, they will be used at training time only
        epsilon: 0.00001
        window: 20
      delft:
        # deep learning parameters
        architecture: "BidLSTM_ChainCRF_FEATURES"
        useELMo: false
        runtime:
          # parameters used at runtime/prediction (for this model, use same max_sequence_length as training)
          max_sequence_length: 3000
          batch_size: 2
        training:
          # parameters used for training
          max_sequence_length: 3000
          batch_size: 10

    - name: "name-header"
      engine: "wapiti"
      #engine: "delft"
      delft:
        # deep learning parameters
        architecture: "BidLSTM_CRF_FEATURES"

    - name: "name-citation"
      engine: "wapiti"
      #engine: "delft"
      delft:
        # deep learning parameters
        architecture: "BidLSTM_CRF_FEATURES"

    - name: "date"
      engine: "wapiti"
      #engine: "delft"
      delft:
        # deep learning parameters
        architecture: "BidLSTM_CRF_FEATURES"

    - name: "figure"
      engine: "wapiti"
      #engine: "delft"
      wapiti:
        # wapiti training parameters, they will be used at training time only
        epsilon: 0.00001
        window: 20
      delft:
        # deep learning parameters
        architecture: "BidLSTM_CRF"

    - name: "table"
      engine: "wapiti"
      #engine: "delft"
      wapiti:
        # wapiti training parameters, they will be used at training time only
        epsilon: 0.00001
        window: 20
      delft:  
        # deep learning parameters
        architecture: "BidLSTM_CRF"

    - name: "affiliation-address"
      engine: "wapiti"
      #engine: "delft"
      delft:
        # deep learning parameters
        architecture: "BidLSTM_CRF_FEATURES"

    - name: "citation"
      engine: "wapiti"
      #engine: "delft"
      wapiti:
        # wapiti training parameters, they will be used at training time only
        epsilon: 0.00001
        window: 50
        nbMaxIterations: 3000
      delft:
        # deep learning parameters
        architecture: "BidLSTM_CRF_FEATURES"
        #architecture: "BERT_CRF"
        #transformer: "michiyasunaga/LinkBERT-base"
        useELMo: false
        runtime:
          # parameters used at runtime/prediction
          max_sequence_length: 500
          batch_size: 30
        training:
          # parameters used for training
          max_sequence_length: 500  
          batch_size: 50

    - name: "patent-citation"
      engine: "wapiti"
      wapiti:
        # wapiti training parameters, they will be used at training time only
        epsilon: 0.0001
        window: 20

    - name: "funding-acknowledgement"
      engine: "wapiti"
      #engine: "delft"
      wapiti:
        # wapiti training parameters, they will be used at training time only
        epsilon: 0.00001
        window: 50
        nbMaxIterations: 2000
      delft:
        # deep learning parameters
        architecture: "BidLSTM_CRF_FEATURES"
        #architecture: "BERT_CRF"
        #transformer: "michiyasunaga/LinkBERT-base"
        useELMo: false
        runtime:
          # parameters used at runtime/prediction
          max_sequence_length: 800
          batch_size: 20
        training:
          # parameters used for training
          max_sequence_length: 500  
          batch_size: 40

  # for **service only**: how to load the models, 
  # false -> models are loaded when needed, avoiding putting in memory useless models (only in case of CRF) but slow down 
  #          significantly the service at first call
  # true -> all the models are loaded into memory at the server startup (default), slow the start of the services 
  #         and models not used will take some more memory (only in case of CRF), but server is immediatly warm and ready
  modelPreload: true

server:
    type: custom
    applicationConnectors:
    - type: http
      port: 8070
    adminConnectors:
    - type: http
      port: 8071
    registerDefaultExceptionMappers: false
    # change the following for having all http requests logged
    requestLog:
      appenders: []

# these logging settings apply to the Grobid service usage mode
logging:
  level: INFO
  loggers:
    org.apache.pdfbox.pdmodel.font.PDSimpleFont: "OFF"
    org.glassfish.jersey.internal: "OFF"
    com.squarespace.jersey2.guice.JerseyGuiceUtils: "OFF"
  appenders:
    - type: console
      threshold: WARN
      timeZone: UTC
      # uncomment to have the logs in json format
      #layout:
      #  type: json
    - type: file
      currentLogFilename: logs/grobid-service.log
      threshold: INFO
      archive: true
      archivedLogFilenamePattern: logs/grobid-service-%d.log
      archivedFileCount: 5
      timeZone: UTC
      # uncomment to have the logs in json format
      #layout:
      #  type: json

```

## Anystyle

[inukshuk/anystyle: Fast citation reference parsing (github.com)](https://github.com/inukshuk/anystyle)

anystyle is writen by ruby, which need the latest `gem` , it is recommanded to instal the latest `ruby` 

```bash
gpg2 --keyserver keyserver.ubuntu.com --recv-keys 409B6B1796C275462A1703113804BB82D39DC0E3 7D2BAF1CF37B13E2069D6956105BD0E739499BDB
curl -sSL https://get.rvm.io | bash -s stable
export RUBY_VER='2.5'
source /home/zhangtianning.di/.rvm/scripts/rvm
rvm install ${RUBY_VER}
gem install anystyle-cli
```

# Usage

please refer to `uparxive\reference_reterive` to `python_script\parse_citation.py` to see how we use anystyle and grobid for bib string retreive.
