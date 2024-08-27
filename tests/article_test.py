from __future__ import annotations

from itertools import chain

from scholaretl.article import Article
from scholaretl.article_parser import ArticleParser


class SimpleTestParser(ArticleParser):
    def __init__(self):
        self._title = "Test Title"
        self._authors = ["Author 1", "Author 2"]
        self._abstract = ["Abstract paragraph 1", "Abstract paragraph 2"]
        self._paragraphs = [
            ("Section 1", "Paragraph 1."),
            ("Section 1", "Paragraph 2."),
            ("Section 2", "Paragraph 1."),
        ]
        self._pubmed_id = "pubmed_id"
        self._pmc_id = "pmc_id"
        self._doi = "doi"
        self._uid = "fake_uid"
        self._article_type = "research-article"

    @property
    def title(self):
        return self._title

    @property
    def authors(self) -> list[str]:
        return self._authors

    @property
    def abstract(self) -> list[str]:
        return self._abstract

    @property
    def paragraphs(self) -> list[tuple[str, str]]:
        return self._paragraphs

    @property
    def pubmed_id(self):
        return self._pubmed_id

    @property
    def pmc_id(self):
        return self._pmc_id

    @property
    def doi(self):
        return self._doi

    @property
    def uid(self):
        return self._uid

    @property
    def article_type(self):
        return self._article_type


class TestArticle:
    def test_optional_defaults(self):
        article = Article(
            title="",
            authors=[""],
            abstract=[""],
            section_paragraphs=[("", "")],
        )
        optional_fields = ["pubmed_id", "pmc_id", "doi", "uid", "article_type"]
        for field in optional_fields:
            assert getattr(article, field) is None

    def test_parse(self):
        # Test article parsing
        parser = SimpleTestParser()
        article = Article.parse(parser)
        assert article.title == parser.title
        assert article.authors == list(parser.authors)

        # Test iterating over all paragraphs in the article. By default the
        # abstract is not included
        for text, text_want in zip(  # noqa
            article.iter_paragraphs(), parser.paragraphs
        ):
            assert text == text_want

        # This time test with the abstract paragraphs included.
        abstract_paragraphs = [("Abstract", text) for text in parser.abstract]
        for text, text_want in zip(  # noqa
            article.iter_paragraphs(with_abstract=True),
            chain(abstract_paragraphs, parser.paragraphs),
        ):
            assert text == text_want

    def test_str(self):
        parser = SimpleTestParser()
        article = Article.parse(parser)
        article_str = str(article)
        assert parser.title in article_str
        for author in parser.authors:
            assert author in article_str

    def test_serialization(self):
        a = Article(
            title="a", authors=["a"], abstract=["a"], section_paragraphs=[("a", "bbb")]
        )

        serialized = a.model_dump_json()
        a_recreated = Article.model_validate_json(serialized)

        assert a == a_recreated
