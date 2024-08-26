# Endpoints

## Parsing

### Response Format

The response format of every parsing endpoint is the same and represents the article with a json schema.

```json
{
  "title": "This is the title of the article.",
  "authors": [
    "Author 1",
    "Author 2",
    "Author 3"
  ],
  "abstract": [
    "This is the paragraph 1 of the abstract.", 
    "This is the paragraph 2 of the abstract."
  ],
  "section_paragraphs": [
    ["Section 1", "Paragraph 1"],
    ["Section 2", "Paragraph 2"]
  ],
  "pubmed_id": "PUBMED_ID",
  "pmc_id": "PMC_ID",
  "arxiv_id": "ARXIV_ID",
  "doi": "DOI",
  "uid": "UNIQUE_ID",
  "date": "2017-03-01",
  "journal": "JOURNAL",
  "figures": [
    "Figure 1",
    "Figure 2"
  ],
  "tables": [
    "Table 1",
    "Table 2"
  ],
  "article_type": "Article Type"
}
```

#### Fields properties

| Fields parameter     | Description                                                            |
|----------------------|------------------------------------------------------------------------|
| `title`              | Title of this article.                                                 |
| `authors`            | A list of authors.                                                     |
| `abstract`           | The list of paragraphs of the abstract for this article.               |
| `section_paragraphs` | The list of paragraphs with their corresponding section name.          |
| `pubmed_id`          | A unique identifier used in the PubMed database.                       |
| `pmc_id`             | A unique identifier used in the PubMed Central (PMC) database.         |
| `arxiv_id`           | A unique identifier used in the ArXiv ID database.                     |
| `doi`                | Digital Object Identifier of this article.                             |
| `uid`                | Unique identifier of this article given based on the hash of the file. |
| `date`               | Publication date of this article.                                      |
| `journal`            | The journal **International Standard Serial Number** of the article.   |
| `figures`            | Figures list.                                                          |
| `tables`             | Tables list.                                                           |
| `article_type`       | Type of the article.                                                   |


### Parsing XMLs

#### Calling the endpoint

All XMLs parsing endpoints are following the same schema. 
One just needs to specify/change the right schema at the end of the endpoint path.

=== "cURL"

    ``` bash
    curl --location 'https://localhost/parse/jats_xml' \
    --form 'inp=@"jats_article.xml"'
    ```

=== "Python"

    ``` Python
    import requests
    import json

    url = "https://localhost/parse/jats_xml"

    files = [
        (
            "inp",
            (
                "jats_article.xml",
                open("jats_article.xml", "rb"),
                "text/xml",
            ),
        )
    ]

    response = requests.request("POST", url, files=files)

    print(response.json())
    ```

#### Schemas

##### JATS XML

If one needs to parse an article following the JATS-XML schema, this is the endpoint that has to be used. 
This is the case of scientific papers coming from [Pubmed Central (PMC)](https://www.ncbi.nlm.nih.gov/pmc/). 

##### PubMed XML

If one needs to parse an article following the PubMed schema, this is the endpoint that has to be used. 
This is the case of scientific papers coming from [PubMed](https://pubmed.ncbi.nlm.nih.gov/). Note that 
the pubmed xml files contain only the abstract. The field `section_paragraphs` is going to be empty.

##### TEI XML

If one needs to parse an article following the TEI-XML schema, this is the endpoint that has to be used. 
This is the case of scientific papers coming from [ArXiv](https://arxiv.org/). This is also the schema returned by Grobid server.

##### XOCS XML

If one needs to parse an article following the XOCS-XML schema, this is the endpoint that has to be used. 
This is the case of scientific papers coming from [scopus](https://www.scopus.com/search/form.uri?display=basic#basic). 


### Parsing PDFs

The package contains two endpoints to parse PDFs (PyPDF and Grobid).

#### PyPDF

##### Calling the endpoint

=== "cURL"

    ``` bash
    curl --location 'https://localhost/parse/pypdf' \
    --form 'inp=@"article.pdf"'
    ```

=== "Python"

    ``` Python
    import requests
    import json

    url = "https://localhost/parse/pypdf"

    files = [
        (
            "inp",
            (
                "test.pdf",
                open(test_data_path / "test.pdf", "rb"),
                "application/pdf",
            ),
        )
    ]

    # This line is not mandatory, but user can change the chunk_size if wanted.
    data = {"chunk_size": 500}
    response = requests.request("POST", url, files=files, data=data)

    print(response.json())
    ```

#### Grobid PDF

##### Calling the endpoint

=== "cURL"

    ``` bash
    curl --location 'https://localhost/parse/grobidpdf' \
    --form 'inp=@"article.pdf"'
    ```

=== "Python"

    ``` Python
    import requests
    import json

    url = "https://localhost/parse/grobidpdf"

    files = [
        (
            "inp",
            (
                "test.pdf",
                open(test_data_path / "test.pdf", "rb"),
                "application/pdf",
            ),
        )
    ]
    # This line is not mandatory, but user can change the parameters if wanted.
    data = {"data": '{"param1": "value1", "param2": "value2"}'}

    response = requests.request("POST", url, files=files, data=data)

    print(response.json())
    ```
