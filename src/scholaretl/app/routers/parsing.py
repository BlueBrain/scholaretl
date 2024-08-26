"""Endpoints for articles parsing."""

import logging
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import Json

from scholaretl.app.config import Settings
from scholaretl.app.dependencies import get_settings
from scholaretl.article import Article
from scholaretl.article_parser import (
    ArticleParser,
    JATSXMLParser,
    PDFParser,
    PubMedXMLParser,
    TEIXMLParser,
    XOCSXMLParser,
)
from scholaretl.utils import grobid_pdf_to_tei_xml

router = APIRouter(prefix="/parse", tags=["Parsing"])

logger = logging.getLogger(__name__)


async def call_parsing(
    inp: UploadFile, parser: str, **kwargs: dict[str, Any]
) -> Article:
    """Parse."""
    # instantiate a parser
    file_input = await inp.read()
    if parser == "pubmed-xml":
        parser_inst: ArticleParser = PubMedXMLParser(file_input)

    elif parser == "jats-xml":
        parser_inst = JATSXMLParser.from_string(file_input.decode("utf-8"))

    elif parser == "tei-xml":
        parser_inst = TEIXMLParser(file_input)

    elif parser == "xocs-xml":
        parser_inst = XOCSXMLParser(file_input)

    elif parser == "pypdf":
        parser_inst = PDFParser(file_input, kwargs["chunk_size"])  # type: ignore

    elif parser == "grobidpdf":
        grobid_url = kwargs.get("url")
        if grobid_url is None:
            raise ValueError("No GROBID-URL environment variable set for parser!")
        xml_data = await grobid_pdf_to_tei_xml(file_input, **kwargs)  # type: ignore
        parser_inst = TEIXMLParser(xml_data)

    else:
        raise NotImplementedError

    article = Article.parse(parser_inst)
    return article


@router.post(
    "/pubmed_xml",
    response_model=Article,
)
async def parse_pubmed_xml(
    inp: UploadFile = File(...),  # noqa: B008
) -> Article:
    """Parse pubmed XML.
    \f
    Parameters
    ----------
    inp
        Paper file sent to the server.

    Returns
    -------
        A single answer.
    """  # noqa: D301
    return await call_parsing(inp, "pubmed-xml")


@router.post(
    "/jats_xml",
    response_model=Article,
)
async def parse_jats_xml(
    inp: UploadFile = File(...),  # noqa: B008
) -> Article:
    """Parse jats XML.
    \f
    Parameters
    ----------
    inp
        Paper file sent to the server.

    Returns
    -------
        Parsed article.
    """  # noqa: D301
    return await call_parsing(inp, "jats-xml")


@router.post(
    "/tei_xml",
    response_model=Article,
)
async def parse_tei_xml(
    inp: UploadFile = File(...),  # noqa: B008
) -> Article:
    """Parse tei XML.
    \f
    Parameters
    ----------
    inp
        Paper file sent to the server.

    Returns
    -------
        Parsed article.
    """  # noqa: D301
    return await call_parsing(inp, "tei-xml")


@router.post(
    "/xocs_xml",
    response_model=Article,
)
async def parse_xocs_xml(
    inp: UploadFile = File(...),  # noqa: B008
) -> Article:
    """Parse xocs XML.
    \f
    Parameters
    ----------
    inp
        Paper file sent to the server.

    Returns
    -------
        Parsed article.
    """  # noqa: D301
    return await call_parsing(inp, "xocs-xml")


@router.post(
    "/pypdf",
    response_model=Article,
)
async def parse_pypdf(
    inp: UploadFile = File(...),  # noqa: B008
    chunk_size: int = 200,
) -> Article:
    """Parse PyPDF.
    \f
    Parameters
    ----------
    inp
        Paper file sent to the server.
    chunk_size
        How many tokens a 'paragraph' should consist of.

    Returns
    -------
        Parsed article.
    """  # noqa: D301
    return await call_parsing(inp, "pypdf", **{"chunk_size": chunk_size})  # type: ignore


@router.post(
    "/grobidpdf",
    response_model=Article,
    responses={
        500: {
            "description": "Grobid server is not available.",
            "content": {
                "application/json": {
                    "schema": {
                        "example": {
                            "detail": {
                                "code": 1,
                                "detail": "Message",
                            }
                        }
                    }
                }
            },
        },
    },
)
async def parse_grobidpdf(
    settings: Annotated[Settings, Depends(get_settings)],
    inp: UploadFile = File(...),  # noqa: B008
    data: Annotated[Json | None, Form(...)] = None,  # type: ignore
) -> Article:
    """Parse Grobid PDF.
    \f
    Parameters
    ----------
    settings
        Global settings of the application.
    inp
        Paper file sent to the server.
    data
        Request Body containing all kwargs for the grobid parsing.

    Returns
    -------
        Parsed article.
    """  # noqa: D301
    if data is None:
        params: dict[str, Any] = {"url": settings.grobid.url}
    else:
        params = {
            "url": settings.grobid.url,
            **data,
        }
    try:
        return await call_parsing(inp, "grobidpdf", **params)
    except ValueError:
        raise HTTPException(
            status_code=500,
            detail={
                "code": 1,
                "detail": "Grobid server is not available.",
            },
        )
