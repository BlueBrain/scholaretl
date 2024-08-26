"""Article class."""

from __future__ import annotations

from collections.abc import Generator, Sequence

from pydantic import BaseModel, ConfigDict

from scholaretl.article_parser import ArticleParser
from scholaretl.utils import adjust_abstract_and_section_paragraphs


class Article(BaseModel):
    """Abstraction of a scientific article and its contents."""

    title: str
    authors: Sequence[str]
    abstract: Sequence[str]
    section_paragraphs: Sequence[tuple[str, str]]
    pubmed_id: str | None = None
    pmc_id: str | None = None
    arxiv_id: str | None = None
    doi: str | None = None
    uid: str | None = None
    date: str | None = None
    journal: str | None = None
    figures: Sequence[bytes] | None = None
    tables: Sequence[str] | None = None
    article_type: str | None = None

    model_config = ConfigDict(extra="forbid")

    @classmethod
    def parse(cls, parser: ArticleParser) -> Article:
        """Parse an article through a parser.

        Parameters
        ----------
        parser
            An article parser instance.
        """
        title = parser.title
        authors = parser.authors
        abstract = parser.abstract
        section_paragraphs = parser.paragraphs
        # Often times, Grobid parses the abstract as being the first paragraph without a section title.
        # This should affect only the TEI parser, hence why the condition is so strict to avoid side effects.
        abstract, section_paragraphs = adjust_abstract_and_section_paragraphs(
            abstract, section_paragraphs
        )
        pubmed_id = parser.pubmed_id
        pmc_id = parser.pmc_id
        arxiv_id = parser.arxiv_id
        doi = parser.doi
        uid = parser.uid
        journal = parser.journal
        article_type = parser.article_type

        date_dt = parser.date
        if date_dt is None:
            date = None
        else:
            date_format = "%Y-%m-%d"
            date = date_dt.strftime(date_format)

        return cls(
            title=title,
            authors=authors,
            abstract=abstract,
            section_paragraphs=section_paragraphs,
            pubmed_id=pubmed_id,
            pmc_id=pmc_id,
            arxiv_id=arxiv_id,
            doi=doi,
            uid=uid,
            date=date,
            journal=journal,
            article_type=article_type,
        )

    def iter_paragraphs(
        self, with_abstract: bool = False
    ) -> Generator[tuple[str, str], None, None]:
        """Iterate over all paragraphs in the article.

        Parameters
        ----------
        with_abstract : bool
            If true the abstract paragraphs will be included at the beginning.

        Yields
        ------
        str
            Section title of the section the paragraph is in.
        str
            The paragraph text.
        """
        if with_abstract:
            for paragraph in self.abstract:
                yield "Abstract", paragraph
        yield from self.section_paragraphs

    def __str__(self) -> str:
        """Get a short summary of the article statistics.

        Returns
        -------
        str
            A summary of the article statistics.
        """
        # Collection information on text/paragraph lengths
        abstract_length = sum(map(len, self.abstract))
        section_lengths = {}
        for section_title, text in self.section_paragraphs:
            if section_title not in section_lengths:
                section_lengths[section_title] = 0
            section_lengths[section_title] += len(text)
        main_text_length = sum(section_lengths.values())
        all_text_length = abstract_length + main_text_length

        # Construct the return string
        info_str = (
            f'Title    : "{self.title}"\n'
            f'Authors  : {", ".join(self.authors)}\n'
            f"Abstract : {len(self.abstract)} paragraph(s), "
            f"{abstract_length} characters\n"
            f"Sections : {len(section_lengths)} section(s) "
            f"{main_text_length} characters\n"
        )
        for section in section_lengths:
            info_str += f"- {section}\n"
        info_str += f"Total text length : {all_text_length}\n"

        return info_str.strip()
