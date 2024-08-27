"""Various utilities."""

from __future__ import annotations

import gzip
import json
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
from defusedxml import ElementTree

from scholaretl.article_parser import (
    ArticleParser,
    CORD19ArticleParser,
    JATSXMLParser,
    PubMedXMLParser,
    TEIXMLParser,
    XOCSXMLParser,
)


def iter_article_parsers(input_type: str, input_path: Path) -> Iterator[ArticleParser]:
    """Return an iterator of initialized parsers for the given input."""
    if input_type == "cord19-json":
        with input_path.open() as f:
            data = json.load(f)
            yield CORD19ArticleParser(data)

    elif input_type == "jats-xml":
        yield JATSXMLParser.from_xml(input_path)

    elif input_type == "jats-meca":
        yield JATSXMLParser.from_zip(input_path)

    elif input_type == "pubmed-xml":
        with input_path.open() as f:
            yield PubMedXMLParser(f.read())

    elif input_type == "pubmed-xml-set":
        with gzip.open(input_path) as xml_stream:
            articles = ElementTree.parse(xml_stream)
        for article in articles.iter("PubmedArticle"):
            article_str = ElementTree.tostring(
                article, encoding="unicode", xml_declaration=True
            )
            yield PubMedXMLParser(article_str)

    elif input_type.startswith("tei-xml"):
        with input_path.open("rb") as f:
            yield TEIXMLParser(f.read())

    elif input_type == "xocs-xml":
        with input_path.open("rb") as f:
            yield XOCSXMLParser(f.read())

    else:
        raise ValueError(f"Unsupported input type '{input_type}'!")


def find_files(
    input_path: Path,
    recursive: bool,
    match_filename: str | None = None,
) -> list[Path]:
    """Find files inside of `input_path`.

    Parameters
    ----------
    input_path
        File or directory to consider.
    recursive
        If True, directories and all subdirectories are considered in a recursive way.
    match_filename
        Only filename matching match_filename are kept.

    Returns
    -------
    inputs : list[Path]
        List of kept files.

    Raises
    ------
    ValueError
        If the input_path does not exists.
    """
    if input_path.is_file():
        return [input_path]

    elif input_path.is_dir():
        if recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        files = (x for x in input_path.glob(pattern) if x.is_file())

        if match_filename is None:
            selected = files
        elif match_filename == "":
            raise ValueError("Value for argument 'match-filename' should not be empty!")
        else:
            regex = re.compile(match_filename)
            selected = (x for x in files if regex.fullmatch(x.name))

        return sorted(selected)

    else:
        raise ValueError(
            "Argument 'input_path' should be a path to an existing file or directory!"
        )


async def grobid_pdf_to_tei_xml(pdf_content: bytes, url: str, **kwargs: Any) -> str:
    """Convert PDF file to TEI XML using GROBID server.

    This function uses the GROBID API service to convert PDF to a TEI XML format.
    In order to setup GROBID server, follow the instructions from
    https://grobid.readthedocs.io/en/latest/Grobid-docker/.

    Parameters
    ----------
    pdf_content
        PDF content
    url
        Url of the GROBID server.

    Returns
    -------
    str
        TEI XML parsing of the PDF content.
    """
    url = f"{url}/api/processFulltextDocument"
    files = {"input": pdf_content}
    headers = {"Accept": "application/xml"}
    timeout = 60

    response = await httpx.AsyncClient().post(
        url=url, files=files, headers=headers, timeout=timeout, params=kwargs
    )
    response.raise_for_status()
    return response.text


def adjust_abstract_and_section_paragraphs(
    abstract: list[str], section_paragraphs: list[tuple[str, str]]
) -> tuple[list[str], list[tuple[str, str]]]:
    """Send the first unnamed section_paragraphs to the abstract if it is empty.

    Parameters
    ----------
    abstract
        List of text parsed coming from the abstract in the article.
    section_paragraphs
        List of (section_name, text) parsed in the article.

    Return
    ------
    tuple[list[str], list[tuple[str, str]]]
        New adjusted abstract and section paragraphs.
    """
    if not abstract:
        nonempty_sections = (
            i for i, (section, _) in enumerate(section_paragraphs) if section
        )

        try:
            i_first = next(nonempty_sections)
        except StopIteration:
            i_first = len(section_paragraphs)

        new_section_paragraphs = section_paragraphs[i_first:]
        new_abstract_paragraphs = [
            paragraph for _, paragraph in section_paragraphs[:i_first]
        ]

        return new_abstract_paragraphs, new_section_paragraphs
    else:
        return abstract, section_paragraphs
