"""Tests covering classes and tools to work with scientific articles data."""

from __future__ import annotations

import datetime
import pathlib
import xml.etree.ElementTree
import zipfile
from itertools import zip_longest

import pytest
from defusedxml import ElementTree
from scholaretl.article_parser import (
    ArticleParser,
    CORD19ArticleParser,
    JATSXMLParser,
    PDFParser,
    PubMedXMLParser,
    TEIXMLParser,
    XOCSXMLParser,
)


@pytest.mark.parametrize(
    ("path", "with_prefix", "expected_id"),
    (
        ("downloads/arxiv/arxiv/pdf/1802/1802.102998v99.xml", True, None),
        ("downloads/arxiv/q-bio/pdf/0309/0309.033v2.pdf", True, None),
        (
            "downloads/arxiv/arxiv/pdf/1802/1802.10298v99.xml",
            True,
            "arxiv:1802.10298v99",
        ),
        ("downloads/arxiv/arxiv/pdf/1411/1411.7903v4.json", True, "arxiv:1411.7903v4"),
        ("downloads/arxiv/q-bio/pdf/0309/0309033v2.pdf", True, "arxiv:q-bio/0309033v2"),
        ("downloads/arxiv/q-bio/pdf/0309/0309.033v2.pdf", False, None),
        ("downloads/arxiv/arxiv/pdf/1802/1802.10298v99.xml", False, "1802.10298v99"),
        ("downloads/arxiv/arxiv/pdf/1411/1411.7903v4.json", False, "1411.7903v4"),
        ("downloads/arxiv/q-bio/pdf/0309/0309033v2.pdf", False, "q-bio/0309033v2"),
        ("1411.7903v4.xml", True, "arxiv:1411.7903v4"),
        ("0309033v2.pdf", True, None),
    ),
)
class FakeParser(ArticleParser):
    def __init__(self, title="", authors=(), abstract=(), paragraphs=(), doi=None):
        self._title = title
        self._authors = authors
        self._abstract = abstract
        self._paragraphs = paragraphs
        self._doi = doi

    @property
    def title(self):
        return self._title

    @property
    def authors(self):
        yield from self._authors

    @property
    def abstract(self):
        yield from self._abstract

    @property
    def paragraphs(self):
        yield from self._paragraphs

    @property
    def doi(self):
        return self._doi


@pytest.fixture(scope="session", params=["article", "article-set"])
def jats_xml_parser(test_data_path, request):
    source = request.param
    if source == "article":
        path = pathlib.Path(test_data_path) / "jats_article.xml"
    else:
        path = pathlib.Path(test_data_path) / "jats_article_from_efetch.xml"
    parser = JATSXMLParser.from_xml(path.resolve())
    return parser


@pytest.fixture
def jats_meca_parser(test_data_path, tmp_path):
    test_xml_path = test_data_path / "biorxiv.xml"
    zip_path = tmp_path / "01234.meca"
    with zipfile.ZipFile(zip_path, "w") as myzip:
        myzip.write(test_xml_path, arcname="content/567.xml")
    parser = JATSXMLParser.from_zip(zip_path.resolve())

    return parser


@pytest.fixture(scope="session")
def tei_xml_parser(test_data_path):
    path = pathlib.Path(test_data_path) / "1411.7903v4.xml"
    with open(path) as f:
        data = f.read()
    data = data.replace('\n\t\t\t\t\t<idno type="arXiv">arxiv:1411.7903v4</idno>', "")
    data = bytes(data, "utf-8")
    parser = TEIXMLParser(data)
    return parser


@pytest.fixture(
    scope="session",
    params=[
        ("1234-5678", "1234-5678"),
        ("12345678", "1234-5678"),
        ("1234567X", "1234-567X"),
        ("TEI Consortium", None),
    ],
)
def tei_xml_parser_multi_journal(test_data_path, request):
    journal, expected = request.param
    path = pathlib.Path(test_data_path) / "1411.7903v4.xml"
    with open(path) as f:
        data = f.read()
    data = data.replace('\n\t\t\t\t\t<idno type="arXiv">arxiv:1411.7903v4</idno>', "")
    data = data.replace(
        "\n\t\t\t\t<publisher>TEI Consortium</publisher>",
        f"'\n\t\t\t\t<publisher>{journal}</publisher>'",
    )
    data = bytes(data, "utf-8")
    parser = TEIXMLParser(data)
    return parser, expected


@pytest.fixture(
    scope="session",
    params=[
        "12 Jan 2014",
        "12 January 2014",
        "12 01 2014",
        "2014 01 12",
        "2014 Jan 12",
        "2014 January 12",
    ],
)
def tei_xml_parser_multi_date(test_data_path, request):
    date = request.param
    path = pathlib.Path(test_data_path) / "1411.7903v4.xml"
    with open(path) as f:
        data = f.read()
    data = data.replace('\n\t\t\t\t\t<idno type="arXiv">arxiv:1411.7903v4</idno>', "")
    data = data.replace("<date>12 Jan 2014</date>", f"<date>{date}</date>")
    data = bytes(data, "utf-8")
    parser = TEIXMLParser(data)
    return parser


@pytest.fixture(scope="session")
def tei_xml_arxiv_parser(test_data_path):
    path = pathlib.Path(test_data_path) / "1411.7903v4.xml"
    with open(path, "rb") as f:
        data = f.read()
    parser = TEIXMLParser(data)
    return parser


@pytest.fixture(scope="session")
def pypdf_pdf_parsers(test_data_path):
    path = pathlib.Path(test_data_path) / "test.pdf"
    with open(path, "rb") as file:
        bytes_pdf = file.read()
    return [PDFParser(bytes_pdf, chunk_size) for chunk_size in [1, 2]]


class TestJATSXMLArticleParser:
    def test_init(self, jats_xml_parser):
        assert isinstance(
            jats_xml_parser.content, xml.etree.ElementTree.ElementTree
        ) or isinstance(jats_xml_parser.content, xml.etree.ElementTree.Element)

    def test_title(self, jats_xml_parser):
        title = jats_xml_parser.title
        assert title == "Article Title"

    def test_authors(self, jats_xml_parser):
        authors = jats_xml_parser.authors

        assert len(authors) == 2
        assert authors[0] == "Author Given Names 1 Author Surname 1"
        assert authors[1] == "Author Given Names 2 Author Surname 2"

    def test_abstract(self, jats_xml_parser):
        abstract = jats_xml_parser.abstract
        assert len(abstract) == 2
        assert abstract[0] == "Abstract Paragraph 1"
        assert abstract[1] == "Abstract Paragraph 2"

    def test_paragraphs(self, jats_xml_parser):
        paragraphs = jats_xml_parser.paragraphs
        assert len(paragraphs) == 7 + 1 + 2  # for paragraph, caption, table
        # There are 3 caption but one is empty

        for i, paragraph in enumerate(paragraphs):
            assert isinstance(paragraph, tuple)
            assert isinstance(paragraph[0], str)
            assert isinstance(paragraph[1], str)
            if i == 7:
                assert paragraph[0] == "Figure Caption"
            if i > 7:
                assert paragraph[0] == "Table Caption"

        assert paragraphs[0] == ("", "Paragraph 1")
        assert paragraphs[3] == ("Section Title 1", "Paragraph Section 1")
        assert paragraphs[4] == ("Section Title 2", "Paragraph Section 2")

    def test_pubmed_id(self, jats_xml_parser):
        pubmed_id = jats_xml_parser.pubmed_id
        assert isinstance(pubmed_id, str)
        assert pubmed_id == "PMID"

    def test_pmc_id(self, jats_xml_parser):
        pmc_id = jats_xml_parser.pmc_id
        assert isinstance(pmc_id, str)
        assert pmc_id == "PMC"

    def test_doi(self, jats_xml_parser):
        doi = jats_xml_parser.doi
        assert isinstance(doi, str)
        assert doi == "DOI"

    def test_uid(self, jats_xml_parser):
        uid = jats_xml_parser.uid
        assert isinstance(uid, str)
        assert len(uid) == 32

    def test_date(self, jats_xml_parser):
        date = jats_xml_parser.date
        assert isinstance(date, datetime.datetime)
        assert date == datetime.datetime(2019, 3, 12)

    def test_journal(self, jats_xml_parser):
        journal = jats_xml_parser.journal
        assert isinstance(journal, str)
        assert journal == "1234-5678"

    def test_article_type(self, jats_xml_parser):
        article_type = jats_xml_parser.article_type
        assert isinstance(article_type, str)
        assert article_type == "research-article"

    @pytest.mark.parametrize(
        ("input_xml", "expected_inner_text"),
        (
            ("<p>Simple paragraph.</p>", "Simple paragraph."),
            ("<p>Nested <p>paragraph</p>.</p>", "Nested paragraph."),
            (
                "<p>Paragraph <italic>with</italic> some <bold>styles</bold>.</p>",
                "Paragraph with some styles.",
            ),
            ("<p>Paragraph with &quot;escapes&#34;.</p>", 'Paragraph with "escapes".'),
            (
                "<p><p>Sub-tags</p> at beginning and <p>end</p>.</p>",
                "Sub-tags at beginning and end.",
            ),
            ("<p>My email is <email>me@epfl.ch</email></p>", "My email is"),
        ),
    )
    def test_inner_text_extraction(
        self, jats_xml_parser, input_xml, expected_inner_text
    ):
        element = ElementTree.fromstring(input_xml)
        inner_text = jats_xml_parser._inner_text(element)
        assert inner_text == expected_inner_text

    @pytest.mark.parametrize(
        ("input_xml", "expected_str"),
        (
            ("<p>Simple paragraph.</p>", "Simple paragraph."),
            ("<bold>Bold text</bold>", "Bold text"),
            ("<italic>Italic text</italic>", "Italic text"),
            ("<underline>Underlined text</underline>", "Underlined text"),
            ("<monospace>Monospaced text</monospace>", "Monospaced text"),
            ("<xref>Hawking20</xref>", "Hawking20"),
            ("<sc>Text in small caps</sc>", "Text in small caps"),
            ("<styled-content>Cool style</styled-content>", "Cool style"),
            ("<sub>subbed</sub>", "_subbed"),
            ("<sup>supped</sup>", "^supped"),
            ("<inline-formula>Completely ignored</inline-formula>", ""),
            ("<disp-formula>Block formula</disp-formula>", ""),
            ("<ext-link>https://www.google.com</ext-link>", ""),
            ("<uri>file:///path/to/file</uri>", ""),
            ("<email>me@domain.ai</email>", ""),
            (
                "<unknown-tag>Default: extract inner text.</unknown-tag>",
                "Default: extract inner text.",
            ),
        ),
    )
    def test_element_to_str_works(self, jats_xml_parser, input_xml, expected_str):
        element = ElementTree.fromstring(input_xml)
        element_str = jats_xml_parser._element_to_str(element)
        assert element_str == expected_str

    def test_element_to_str_of_none(self, jats_xml_parser):
        assert jats_xml_parser._element_to_str(None) == ""


class TestMecaArticleParser:
    def test_init(self, jats_meca_parser):
        assert isinstance(jats_meca_parser.content, xml.etree.ElementTree.ElementTree)

    def test_wrong_file(self, test_data_path, tmp_path):
        test_xml_path = test_data_path / "biorxiv.xml"
        zip_path = tmp_path / "01234.meca"
        with zipfile.ZipFile(zip_path, "w") as myzip:
            for i in range(2):
                myzip.write(test_xml_path, arcname=f"content/{i}.xml")
        with pytest.raises(ValueError):
            _ = JATSXMLParser.from_zip(zip_path.resolve())


@pytest.fixture(scope="session")
def pubmed_xml_parser(test_data_path):
    """Parse a 'PubmedArticle' in a 'PubmedArticleSet'."""
    path = pathlib.Path(test_data_path) / "pubmed_article.xml"
    with path.open() as f:
        parser = PubMedXMLParser(f.read())
    return parser


@pytest.fixture(scope="session")
def pubmed_xml_parser_minimal(test_data_path):
    """Parse a 'PubmedArticle' in a 'PubmedArticleSet' having only required elements."""
    path = pathlib.Path(test_data_path) / "pubmed_article_minimal.xml"
    with path.open() as f:
        parser = PubMedXMLParser(f.read())
        return parser


class TestPubMedXMLArticleParser:
    def test_init(self, pubmed_xml_parser):
        assert isinstance(pubmed_xml_parser.content, xml.etree.ElementTree.Element)

    def test_title(self, pubmed_xml_parser):
        title = pubmed_xml_parser.title
        assert title == "Article Title"

    def test_authors(self, pubmed_xml_parser):
        authors = pubmed_xml_parser.authors
        assert len(authors) == 2
        assert authors[0] == "Forenames 1 Lastname 1"
        assert authors[1] == "Lastname 2"

    def test_no_authors(self, pubmed_xml_parser_minimal):
        authors = pubmed_xml_parser_minimal.authors
        assert len(authors) == 0
        assert authors == []

    def test_abstract(self, pubmed_xml_parser):
        abstract = pubmed_xml_parser.abstract
        assert len(abstract) == 2
        assert abstract[0] == "Abstract Paragraph 1"
        assert abstract[1] == "Abstract Paragraph 2"

    def test_no_abstract(self, pubmed_xml_parser_minimal):
        abstract = pubmed_xml_parser_minimal.abstract
        assert len(abstract) == 0
        assert abstract == []

    def test_no_paragraphs(self, pubmed_xml_parser):
        paragraphs = pubmed_xml_parser.paragraphs
        assert len(paragraphs) == 0
        assert paragraphs == []

    def test_pubmed_id(self, pubmed_xml_parser):
        pubmed_id = pubmed_xml_parser.pubmed_id
        assert isinstance(pubmed_id, str)
        assert pubmed_id == "123456"

    def test_pmc_id(self, pubmed_xml_parser):
        pmc_id = pubmed_xml_parser.pmc_id
        assert isinstance(pmc_id, str)
        assert pmc_id == "PMC12345"

    def test_no_pmc_id(self, pubmed_xml_parser_minimal):
        pmc_id = pubmed_xml_parser_minimal.pmc_id
        assert pmc_id is None

    def test_doi(self, pubmed_xml_parser):
        doi = pubmed_xml_parser.doi
        assert isinstance(doi, str)
        assert doi == "10.0123/issn.0123-4567"

    def test_no_doi(self, pubmed_xml_parser_minimal):
        doi = pubmed_xml_parser_minimal.doi
        assert doi is None

    def test_date(self, pubmed_xml_parser):
        date = pubmed_xml_parser.date
        assert isinstance(date, datetime.datetime)
        assert date == datetime.datetime(2019, 1, 1)

    def test_journal(self, pubmed_xml_parser):
        journal = pubmed_xml_parser.journal
        assert isinstance(journal, str)
        assert journal == "0123-4567"

    def test_uid(self, pubmed_xml_parser):
        uid = pubmed_xml_parser.uid
        assert isinstance(uid, str)
        assert uid == "0e8400416a385b9a62d8178539b76daf"

    def test_article_type(self, pubmed_xml_parser):
        article_type = pubmed_xml_parser.article_type
        assert isinstance(article_type, str)
        assert article_type == "Journal Article"


class TestCORD19ArticleParser:
    def test_init(self, real_json_file):
        # Should be able to read real JSON files no problem.
        parser = CORD19ArticleParser(real_json_file)
        assert parser.data == real_json_file

        # If any of the mandatory top-level keys are missing in the JSON file
        # then an exception should be raised.
        with pytest.raises(ValueError, match="Incomplete JSON file"):
            CORD19ArticleParser({})

    def test_title(self, real_json_file):
        parser = CORD19ArticleParser(real_json_file)
        title = parser.title
        assert title != ""
        assert title == real_json_file["metadata"]["title"]

    def test_authors(self, real_json_file):
        parser = CORD19ArticleParser(real_json_file)
        authors = parser.authors

        # Check that all authors have been parsed
        assert len(authors) == len(real_json_file["metadata"]["authors"])

        # Check that all name parts of all authors have been collected
        for author, author_dict in zip(  # noqa
            authors, real_json_file["metadata"]["authors"]
        ):
            assert author_dict["first"] in author
            assert author_dict["last"] in author
            assert author_dict["suffix"] in author
            for middle in author_dict["middle"]:
                assert middle in author

    def test_abstract(self, real_json_file):
        parser = CORD19ArticleParser(real_json_file)
        abstract = parser.abstract

        if "abstract" in real_json_file:
            # Check that all paragraphs were parsed
            assert len(abstract) == len(real_json_file["abstract"])

            # Check that all paragraph texts match
            for paragraph, paragraph_dict in zip(  # noqa
                abstract, real_json_file["abstract"]
            ):
                assert paragraph == paragraph_dict["text"]
        else:
            # Check that if "abstract" is missing then an empty list is returned.
            # This should be true for all PMC parses.
            assert len(abstract) == 0

    def test_paragraphs(self, real_json_file):
        parser = CORD19ArticleParser(real_json_file)
        paragraphs = parser.paragraphs

        # Check that all paragraphs were parsed
        n_body_text = len(real_json_file["body_text"])
        n_ref_entries = len(real_json_file["ref_entries"])
        assert len(paragraphs) == n_body_text + n_ref_entries

        # Check that all paragraph texts match
        for (section, text), paragraph_dict in zip(  # noqa
            paragraphs, real_json_file["body_text"]
        ):
            assert section == paragraph_dict["section"]
            assert text == paragraph_dict["text"]

    def test_pubmed_id(self, real_json_file):
        # There is no Pubmed ID specified in the schema of CORD19 json files
        parser = CORD19ArticleParser(real_json_file)
        pubmed_id = parser.pubmed_id
        assert pubmed_id is None

    def test_pmc_id(self, real_json_file):
        parser = CORD19ArticleParser(real_json_file)
        pmc_id = parser.pmc_id
        assert isinstance(pmc_id, str)

    def test_doi(self, real_json_file):
        # There is no DOI specified in the schema of CORD19 json files
        parser = CORD19ArticleParser(real_json_file)
        doi = parser.doi
        assert doi is None

    def test_uid(self, real_json_file):
        parser = CORD19ArticleParser(real_json_file)
        uid = parser.uid
        assert isinstance(uid, str)
        assert len(uid) == 32

    def test_str(self, real_json_file):
        parser = CORD19ArticleParser(real_json_file)
        parser_str = str(parser)

        # Should be "CORD-19 article ID=<value>" or similar
        assert "CORD-19" in parser_str
        assert str(real_json_file["paper_id"]) in parser_str


class TestTEIXMLArticleParser:
    def test_title(self, tei_xml_parser):
        title = tei_xml_parser.title
        assert isinstance(title, str)
        assert title == "Article Title"

    def test_abstract(self, tei_xml_parser):
        abstract = list(tei_xml_parser.abstract)
        assert len(abstract) == 1
        assert abstract[0] == "Abstract Paragraph 1."

    def test_authors(self, tei_xml_parser):
        authors = list(tei_xml_parser.authors)
        assert len(authors) == 2
        assert authors[0] == "Forename 1 Middle 1 Surname 1"
        assert authors[1] == "Surname 2"

    def test_paragraphs(self, tei_xml_parser):
        paragraphs = list(tei_xml_parser.paragraphs)
        assert len(paragraphs) == 7
        assert paragraphs[0][0] == "Head 1"
        assert paragraphs[2][0] == "Head 2"
        assert paragraphs[4][0] == "Figure Caption"
        assert paragraphs[6][0] == "Table Caption"

        assert paragraphs[0][1] == "Paragraph 1 of Head 1."
        assert paragraphs[3][1] == "Paragraph 2 of (0) Head 2."
        assert paragraphs[4][1] == "Fig. 1. Title."
        assert paragraphs[6][1] == "Table 1. Title."

    def test_no_arxiv_id(self, tei_xml_parser):
        arxiv_id = tei_xml_parser.arxiv_id
        assert arxiv_id is None

    def test_arxiv_id(self, tei_xml_arxiv_parser):
        arxiv_id = tei_xml_arxiv_parser.arxiv_id
        assert isinstance(arxiv_id, str)
        assert arxiv_id == "arxiv:1411.7903v4"

    def test_doi(self, tei_xml_parser):
        doi = tei_xml_parser.doi
        assert isinstance(doi, str)
        assert doi == "DOI 1"

    def test_journal(self, tei_xml_parser_multi_journal):
        parser, expected = tei_xml_parser_multi_journal
        journal = parser.journal
        assert isinstance(journal, str) or journal is None
        assert journal == expected

    def test_date(self, tei_xml_parser_multi_date):
        date = tei_xml_parser_multi_date.date
        assert isinstance(date, datetime.datetime)
        assert date == datetime.datetime(2014, 1, 12)

    @pytest.mark.parametrize(
        ("xml_content", "expected_texts"),
        (
            ("", ()),
            ("<p></p>", ()),
            ("<p>Hello.</p>", ("Hello.",)),
            ("<p>Hello</p>", ("Hello.",)),
            ("<p>Hello.</p><p>There.</p>", ("Hello.", "There.")),
            ("<p>Hello</p><p>There.</p>", ("Hello.", "There.")),
            ("<p>Hello</p><p>there.</p>", ("Hello there.",)),
            (
                "<p>This is cool: </p><formula>a + b = c</formula>",
                ("This is cool: FORMULA.",),
            ),
            (
                "<p>As </p><formula>x = 5</formula><p>shows...</p>",
                ("As FORMULA shows...",),
            ),
        ),
    )
    def test_build_texts(self, xml_content, expected_texts):
        parser = TEIXMLParser(f"<xml>{xml_content}</xml>")
        # Patch the namespace because it's not used in test examples
        parser.tei_namespace["tei"] = ""

        texts = parser._build_texts(parser.content)
        for text, expected_text in zip_longest(texts, expected_texts, fillvalue=None):
            assert text == expected_text

    def test_build_texts_raises_for_unknown_tag(self):
        parser = TEIXMLParser("<xml><hahaha>HAHAHA</hahaha></xml>")
        with pytest.raises(RuntimeError, match=r"Unexpected tag"):
            for _ in parser._build_texts(parser.content):
                # Do nothing, just force the generator to run
                pass


class TestPDFParser:
    def test_title(self, pypdf_pdf_parsers):
        for parser in pypdf_pdf_parsers:
            assert parser.title == ""

    def test_abstract(self, pypdf_pdf_parsers):
        for parser in pypdf_pdf_parsers:
            assert parser.abstract == []

    def test_authors(self, pypdf_pdf_parsers):
        for parser in pypdf_pdf_parsers:
            assert parser.authors == []

    def test_paragraphs(self, pypdf_pdf_parsers):
        expected_chunks = [
            [("Article Chunk", "Hello"), ("Article Chunk", "world!")],
            [("Article Chunk", "Hello world!")],
        ]

        for i, parser in enumerate(pypdf_pdf_parsers):
            assert list(parser.paragraphs) == expected_chunks[i]


class TestIdentifiers:
    # By running this test several times and on different platforms during CI,
    # this test checks that UID generation is deterministic across platforms
    # and Python processes.

    @pytest.mark.parametrize(
        "identifiers, expected",
        [
            pytest.param(
                ("a", "b"), "aca14e654bc28ce1c1e8131004244d64", id="all-defined"
            ),
            pytest.param(
                ("b", "a"), "82ca240c4a3f5579a5c33404af58e41b", id="all-defined-reverse"
            ),
            pytest.param(
                ("a", None), "4b515f920fbbc7954fc5a68bb746b109", id="with-none"
            ),
            pytest.param(
                (None, "a"), "77f283f2e87b852ed7a881e6f638aa80", id="with-none-reverse"
            ),
            pytest.param((None, None), None, id="all-none"),
            pytest.param(
                (None, 0), "14536e026b2a39caf27f3da802e7fed6", id="none-and-zero"
            ),
        ],
    )
    def test_generate_uid_from_identifiers(self, identifiers, expected):
        if expected is None:
            with pytest.raises(ValueError):
                ArticleParser.get_uid_from_identifiers(identifiers)

        else:
            result = ArticleParser.get_uid_from_identifiers(identifiers)
            assert result == expected

            # Check determinism.
            result_bis = ArticleParser.get_uid_from_identifiers(identifiers)
            assert result == result_bis

    @pytest.mark.parametrize(
        "parser_kwargs, expected",
        [
            pytest.param(
                {
                    "title": "TITLE",
                    "abstract": ["ABS 1", "ABS 2"],
                    "paragraphs": [("PAR 1", "text 1"), ("PAR 2", "text 2")],
                    "authors": ["AUTH 1", "AUTH 2"],
                },
                "212f772faf801518f8dd9f745a1c94b2",
                id="no-ids-full-text",
            ),
            pytest.param(
                {
                    "title": "TITLE",
                    "abstract": ["ABS 1", "ABS 2"],
                },
                "7229b18916ba8b83b20d243d5caaf56a",
                id="no-ids-abstract-only",
            ),
            pytest.param(
                {"title": "TITLE", "abstract": ["ABS 1", "ABS 2"], "doi": "1.234"},
                "9cfc45f5817b544ac26e02a9071802b6",
                id="doi-with-text",
            ),
            pytest.param(
                {"doi": "1.234"},
                "9cfc45f5817b544ac26e02a9071802b6",
                id="doi-without-text",
            ),
        ],
    )
    def test_general_article_uid(self, parser_kwargs, expected):
        article_parser = FakeParser(**parser_kwargs)

        assert article_parser.uid == expected


def test_abstract_parser() -> None:
    parser = XOCSXMLParser(data=open("./tests/data/scopus_abstract.xml").read())
    assert (
        parser.title
        == "Single or multiple familial cognitive risk factors in schizophrenia?"
    )
    assert parser.doi == "10.1002/ajmg.1197"
    assert parser.type == "abstract"
    assert parser.date == datetime.datetime(2001, 3, 8)
    assert parser.abstract
    assert parser.authors
    assert len(list(parser.paragraphs)) == 0
    assert parser.journal == "1552-4841"
    assert parser.article_type is None


def test_fulltext_parser() -> None:
    parser = XOCSXMLParser(data=open("./tests/data/scopus_fulltext.xml").read())
    assert (
        parser.title
        == "The Rise and Fall of Frequency and Imageability: Noun and Verb Production"
        " in Semantic Dementia"
    )
    assert parser.doi == "10.1006/brln.2000.2293"
    assert parser.type == "full"
    assert parser.date == datetime.datetime(2000, 6, 1)
    assert parser.abstract
    assert parser.authors
    assert len(list(parser.paragraphs)) == 0
    assert parser.journal == "0093-934X"
    assert parser.article_type == "Regular Article"
    assert parser.pubmed_id == "10872636"


def test_fulltext_cell_parser() -> None:
    parser = XOCSXMLParser(data=open("./tests/data/scopus_fulltext_cell.xml").read())
    assert parser.title == "Reconstruction and Simulation of Neocortical Microcircuitry"
    assert parser.doi == "10.1016/j.cell.2015.09.029"
    assert parser.type == "full"
    assert parser.date == datetime.datetime(2015, 10, 8)
    assert parser.abstract
    assert parser.authors
    assert len(list(parser.paragraphs)) == 147
    assert parser.journal == "0092-8674"
    assert parser.article_type == "Resource"
    assert parser.pubmed_id == "26451489"
