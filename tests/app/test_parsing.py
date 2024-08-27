"""Test parsing endpoints."""

from unittest.mock import AsyncMock

from fastapi.testclient import TestClient
from scholaretl.app.config import Settings
from scholaretl.app.dependencies import get_settings
from scholaretl.app.main import app


def test_parse_pubmed_xml(app_client, test_data_path):
    files = [
        (
            "inp",
            (
                "pubmed_article.xml",
                open(test_data_path / "pubmed_article.xml", "rb"),
                "text/xml",
            ),
        )
    ]
    response = app_client.post(
        "/parse/pubmed_xml",
        files=files,
    )

    response_json = response.json()
    assert response_json["title"] == "Article Title"
    assert response_json["authors"] == ["Forenames 1 Lastname 1", "Lastname 2"]
    assert response_json["abstract"] == ["Abstract Paragraph 1", "Abstract Paragraph 2"]
    assert response_json["section_paragraphs"] == []
    assert response_json["pubmed_id"] == "123456"
    assert response_json["pmc_id"] == "PMC12345"
    assert response_json["arxiv_id"] is None
    assert response_json["doi"] == "10.0123/issn.0123-4567"
    assert response_json["journal"] == "0123-4567"
    assert response_json["article_type"] == "Journal Article"


def test_parse_jats_xml(app_client, test_data_path):
    files = [
        (
            "inp",
            (
                "jats_article.xml",
                open(test_data_path / "jats_article.xml", "rb"),
                "text/xml",
            ),
        )
    ]
    response = app_client.post(
        "/parse/jats_xml",
        files=files,
    )

    response_json = response.json()
    assert response_json["title"] == "Article Title"
    assert response_json["authors"] == [
        "Author Given Names 1 Author Surname 1",
        "Author Given Names 2 Author Surname 2",
    ]
    assert response_json["abstract"] == ["Abstract Paragraph 1", "Abstract Paragraph 2"]
    assert response_json["section_paragraphs"] == [
        ["", "Paragraph 1"],
        ["", "Paragraph 2"],
        ["", "Paragraph 3"],
        ["Section Title 1", "Paragraph Section 1"],
        ["Section Title 2", "Paragraph Section 2"],
        ["Section Title 2", "Paragraph 2 Section 2"],
        ["Discussion", "Paragraph Discussion"],
        ["Figure Caption", "Figure 1 Caption"],
        ["Table Caption", "Table 1 Caption"],
        ["Table Caption", "Table 2 Caption"],
    ]
    assert response_json["pubmed_id"] == "PMID"
    assert response_json["pmc_id"] == "PMC"
    assert response_json["arxiv_id"] is None
    assert response_json["doi"] == "DOI"
    assert response_json["journal"] == "1234-5678"
    assert response_json["article_type"] == "research-article"


def test_parse_tei_xml(app_client, test_data_path):
    files = [
        (
            "inp",
            (
                "1411.7903v4.xml",
                open(test_data_path / "1411.7903v4.xml", "rb"),
                "text/xml",
            ),
        )
    ]
    response = app_client.post(
        "/parse/tei_xml",
        files=files,
    )
    response_json = response.json()
    assert response_json["title"] == "Article Title"
    assert response_json["authors"] == [
        "Forename 1 Middle 1 Surname 1",
        "Surname 2",
    ]
    assert response_json["abstract"] == [
        "Abstract Paragraph 1.",
    ]
    assert response_json["section_paragraphs"] == [
        ["Head 1", "Paragraph 1 of Head 1."],
        ["Head 1", "Paragraph 2 of Head 1."],
        ["Head 2", "Paragraph 1 of Head 2."],
        ["Head 2", "Paragraph 2 of (0) Head 2."],
        ["Figure Caption", "Fig. 1. Title."],
        ["Figure Caption", "Fig. 2. Title."],
        ["Table Caption", "Table 1. Title."],
    ]
    assert response_json["pubmed_id"] is None
    assert response_json["pmc_id"] is None
    assert response_json["arxiv_id"] == "arxiv:1411.7903v4"
    assert response_json["doi"] == "DOI 1"
    assert response_json["journal"] is None
    assert response_json["article_type"] is None


def test_parse_xocs_xml(app_client, test_data_path):
    files = [
        (
            "inp",
            (
                "scopus_fulltext.xml",
                open(test_data_path / "scopus_fulltext.xml", "rb"),
                "text/xml",
            ),
        )
    ]
    response = app_client.post(
        "/parse/xocs_xml",
        files=files,
    )
    response_json = response.json()
    assert (
        response_json["title"]
        == "The Rise and Fall of Frequency and Imageability: Noun and Verb Production"
        " in Semantic Dementia"
    )
    assert len(response_json["authors"]) == 4
    assert len(response_json["abstract"]) == 1
    assert len(response_json["section_paragraphs"]) == 0
    assert response_json["pubmed_id"] == "10872636"
    assert response_json["pmc_id"] is None
    assert response_json["arxiv_id"] is None
    assert response_json["doi"] == "10.1006/brln.2000.2293"
    assert response_json["journal"] == "0093-934X"
    assert response_json["article_type"] == "Regular Article"


def test_parse_pypdf(app_client, test_data_path):
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
    response = app_client.post(
        "/parse/pypdf",
        files=files,
    )
    response_json = response.json()
    assert response_json["title"] == ""
    assert len(response_json["authors"]) == 0
    assert len(response_json["abstract"]) == 0
    assert response_json["section_paragraphs"] == [["Article Chunk", "Hello world!"]]
    assert response_json["pubmed_id"] is None
    assert response_json["pmc_id"] is None
    assert response_json["arxiv_id"] is None
    assert response_json["doi"] is None
    assert response_json["journal"] is None
    assert response_json["article_type"] is None


def test_parse_grobid(app_client, test_data_path, monkeypatch):
    grobid_pdf_to_tei_xml_mock = AsyncMock()
    grobid_pdf_to_tei_xml_mock.return_value = open(
        test_data_path / "1411.7903v4.xml"
    ).read()
    monkeypatch.setattr(
        "scholaretl.app.routers.parsing.grobid_pdf_to_tei_xml",
        grobid_pdf_to_tei_xml_mock,
    )

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
    data = {"data": '{"name": "foo", "point": 0.13, "is_accepted": false}'}
    response = app_client.post(
        "/parse/grobidpdf",
        files=files,
        data=data,
    )
    response_json = response.json()
    assert response_json["title"] == "Article Title"
    assert response_json["authors"] == [
        "Forename 1 Middle 1 Surname 1",
        "Surname 2",
    ]
    assert response_json["abstract"] == [
        "Abstract Paragraph 1.",
    ]
    assert response_json["section_paragraphs"] == [
        ["Head 1", "Paragraph 1 of Head 1."],
        ["Head 1", "Paragraph 2 of Head 1."],
        ["Head 2", "Paragraph 1 of Head 2."],
        ["Head 2", "Paragraph 2 of (0) Head 2."],
        ["Figure Caption", "Fig. 1. Title."],
        ["Figure Caption", "Fig. 2. Title."],
        ["Table Caption", "Table 1. Title."],
    ]
    assert response_json["pubmed_id"] is None
    assert response_json["pmc_id"] is None
    assert response_json["arxiv_id"] == "arxiv:1411.7903v4"
    assert response_json["doi"] == "DOI 1"
    assert response_json["journal"] is None
    assert response_json["article_type"] is None

    assert grobid_pdf_to_tei_xml_mock.call_count == 1


def test_parse_grobid_no_url(test_data_path, monkeypatch):
    app_client = TestClient(app)
    test_settings = Settings(grobid={"url": None})
    app.dependency_overrides[get_settings] = lambda: test_settings

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
    data = {"data": '{"name": "foo", "point": 0.13, "is_accepted": false}'}

    response = app_client.post(
        "/parse/grobidpdf",
        files=files,
        data=data,
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": {"code": 1, "detail": "Grobid server is not available."}
    }
