from pathlib import Path

import pytest
from scholaretl.utils import (
    adjust_abstract_and_section_paragraphs,
    iter_article_parsers,
)


@pytest.mark.parametrize(
    "input_type, path, article_uids",
    [
        pytest.param(
            "cord19-json",
            "cord19/document_parses/pmc_json/PMC7140272.xml.json",
            ["d1810cbd0384f5ea16d7fc0aed117b6e"],
            id="cord19-json",
        ),
        pytest.param(
            "jats-xml",
            "jats_article.xml",
            ["34eaed1a1a05166c0b8610336aee638d"],
            id="jats-xml",
        ),
        pytest.param(
            "pubmed-xml",
            "pubmed_article.xml",
            ["0e8400416a385b9a62d8178539b76daf"],
            id="pubmed-xml",
        ),
        pytest.param(
            "tei-xml",
            "1411.7903v4.xml",
            ["26f61b81976907d1fa5b779511fb1360"],
            id="tei-xml",
        ),
        pytest.param(
            "xocs-xml",
            "scopus_fulltext.xml",
            ["10.1006/brln.2000.2293"],
            id="xocs-xml",
        ),
    ],
)
def test_iter_parsers(input_type, path, article_uids):
    input_path = Path("tests/data/") / path
    parsers = iter_article_parsers(input_type, input_path)
    for parser, uid in zip(parsers, article_uids):  # noqa
        assert parser.uid == uid


def test_iter_parsers_pubmed_xml_set(pubmed_xml_gz_path):
    parsers = iter_article_parsers("pubmed-xml-set", pubmed_xml_gz_path)
    article_uids = [
        "0e8400416a385b9a62d8178539b76daf",
        "6b49530911527984509a202e7cf083ce",
    ]
    for parser, uid in zip(parsers, article_uids):  # noqa
        assert parser.uid == uid


@pytest.mark.parametrize(
    "abstract,section_paragraphs,expected_abstract,expected_section_paragraphs",
    [
        (
            ["This abstract is well parsed"],
            [("Section 1", "Amazing paragraphs"), ("Section 2", "Great paper")],
            ["This abstract is well parsed"],
            [("Section 1", "Amazing paragraphs"), ("Section 2", "Great paper")],
        ),
        (
            ["This abstract is well parsed"],
            [("", "Amazing paragraphs"), ("Section 2", "Great paper")],
            ["This abstract is well parsed"],
            [("", "Amazing paragraphs"), ("Section 2", "Great paper")],
        ),
        (
            ["This abstract is well parsed"],
            [("", "Amazing paragraphs"), ("", "Great paper")],
            ["This abstract is well parsed"],
            [("", "Amazing paragraphs"), ("", "Great paper")],
        ),
        (
            [],
            [("Section 1", "Amazing paragraphs"), ("Section 2", "Great paper")],
            [],
            [("Section 1", "Amazing paragraphs"), ("Section 2", "Great paper")],
        ),
        (
            [],
            [("", "Amazing paragraphs"), ("Section 2", "Great paper")],
            ["Amazing paragraphs"],
            [("Section 2", "Great paper")],
        ),
        (
            [],
            [
                ("", "Amazing paragraphs"),
                ("", "Great paper"),
                ("Conclusion", "Finally a section with a title"),
            ],
            ["Amazing paragraphs", "Great paper"],
            [("Conclusion", "Finally a section with a title")],
        ),
    ],
)
def test_adjust_abstract_and_section_paragraphs(
    abstract, section_paragraphs, expected_abstract, expected_section_paragraphs
):
    abstract, section_paragraphs = adjust_abstract_and_section_paragraphs(
        abstract, section_paragraphs
    )
    assert abstract == expected_abstract
    assert section_paragraphs == expected_section_paragraphs
