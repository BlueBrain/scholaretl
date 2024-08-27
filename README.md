# Scholaretl

An Extract, Transfrom and Load (ETL) API made to parse scientific papers. This package is meant to be used with scholarag, our Retreival Augmented Generation (RAG) tool. It is mainly used to parse scientific paper coming from different sources, to make it compatible with ususal databases.

0. [Quickstart](#quickstart)
1. [List of endpoints](#list-of-endpoints)
2. [Docker Image](#docker-image)
3. [Grobid parsing](#grobid-parsing)
4. [Funding and Acknowledgement](#funding-and-acknowledgement)


## Quickstart

#### Step 1 : Install the package.

Simply install the package with PyPi.

```bash
pip install scholaretl
```

You can also clone the GitHub repo and install the package yourself.

#### Step 2 : Run the FastApi app.

A simple script is installed with the package, and allows to run the app locally. By default the API is open on port 8000.

```bash
scholaretl-api
```

See the `-h` flag for non default arguments.

#### Step 3 : Test the app.

Now that the server is running, you can either curl it to get information.

```bash
curl http://localhost:8000/settings
```

Or open a browser at : `http://localhost:8000/docs` and try some of the endpoints. For example, use the `parse/pypdf` endpoint to parse a local pdf file. Parsing xml files works out of the box. Keep in mind that the xml parsing endpoints are meant to be used with files comming from specific scientific journals. (see [List of endpoints](#list-of-endpoints))


## List of endpoints

Once the app is deployed, all these endpoints will be available to use :
* `/parse/pubmed_xml`: parses XMLs coming from PubMed.
* `/parse/jats_xml`: Parses XMLs coming from PMC.
* `/parse/tei_xml`: Parses XMLs produced by Grobid.
* `/parse/xocs_xml`: Parses XMLs coming from Scopus (Elsevier)
* `/parse/pypdf`: Parses PDFs without keeping the structure of the document.
* `/parse/grobidpdf`: Parses PDFs keeping the structure of the document (REQUIRES grobid, see [Grobid parsing](#grobid-parsing)).

## Docker image

If a docker container is required, it can be build using the provided Dockerfile. Make sure you have Docker installed.

```bash
docker build -t scholaretl:latest . --platform linux/amd64
```
It can then be tested by runing the container locally. The flag `--platform linux/amd64` depends on the desired deployement and should be changed accordingly. `Scholaretl:latest` can be sutomized at will.
The image can then be activated using :
```bash
docker run -d -p 8080:8080 scholaretl:latest
```
The Api will accept requests on port `8080`, ie you can acces the UI at : `http://localhost:8080/docs`.

## Grobid parsing


To parse documents with the Grobid enpoint, It requires a Grobid server to be running. To deploy it, simply run

```bash
docker run -p 8070:8070 -d lfoppiano/grobid:0.7.3
```

Then pass the server's url to the script in a .env file:

```bash
echo SCHOLARETL__GROBID__URL=http://localhost:8070 > .env
scholaretl-api
```
You can also add the server's url in the `.env` manually. See the `env.example` file for more information.

If using docker, pass the server's URL as an environment variable.

```bash
docker run -p 8080:8080 -d -e SCHOLARETL__GROBID__URL=http://host.docker.internal:8070 scholaretl:latest
```

## Funding and Acknowledgement

The development of this software was supported by funding to the Blue Brain Project, a research center of the École polytechnique fédérale de Lausanne (EPFL), from the Swiss government’s ETH Board of the Swiss Federal Institutes of Technology.

Copyright (c) 2024 Blue Brain Project/EPFL
