"""Abstraction of scientific article data and related tools."""

from __future__ import annotations

import datetime
import enum
import hashlib
import html
import io
import logging
import re
import string
import unicodedata
from abc import ABC, abstractmethod
from collections.abc import Generator, Iterable
from io import StringIO
from pathlib import Path
from typing import IO, Any
from xml.etree.ElementTree import Element  # nosec
from zipfile import ZipFile

import dateparser
from defusedxml import ElementTree
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class ArticleSource(enum.Enum):
    """The source of an article."""

    ARXIV = "arxiv"
    BIORXIV = "biorxiv"
    MEDRXIV = "medrxiv"
    PMC = "pmc"
    PUBMED = "pubmed"
    XOCS = "xocs"
    UNKNOWN = "unknown"


class ArticleParser(ABC):
    """An abstract base class for article parsers."""

    @property
    @abstractmethod
    def title(self) -> str:
        """Get the article title.

        Returns
        -------
        str
            The article title.
        """

    @property
    @abstractmethod
    def authors(self) -> list[str]:
        """Get all author names.

        Returns
        -------
        list of str
            All authors.
        """

    @property
    @abstractmethod
    def abstract(self) -> list[str]:
        """Get a sequence of paragraphs in the article abstract.

        Returns
        -------
        list of str
            The paragraphs of the article abstract.
        """

    @property
    @abstractmethod
    def paragraphs(self) -> list[tuple[str, str]]:
        """Get all paragraphs and titles of sections they are part of.

        Returns
        -------
        list of (str, str)
            For each paragraph a tuple with two strings is returned. The first
            is the section title, the second the paragraph content.
        """

    @property
    def date(self) -> datetime.datetime | None:
        """Get the article date.

        Returns
        -------
        datetime.datetime
            The article date.
        """
        return None

    @property
    def journal(self) -> str | None:
        """Get the article journal.

        Returns
        -------
        str
            The article journal.
        """
        return None

    @property
    def article_type(self) -> str | None:
        """Get the article type.

        Returns
        -------
        str
            The article type.
        """
        return None

    @property
    def pubmed_id(self) -> str | None:
        """Get Pubmed ID.

        Returns
        -------
        str or None
            Pubmed ID if specified, otherwise None.
        """
        return None

    @property
    def pmc_id(self) -> str | None:
        """Get PMC ID.

        Returns
        -------
        str or None
            PMC ID if specified, otherwise None.
        """
        return None

    @property
    def arxiv_id(self) -> str | None:
        """Get arXiv ID.

        Returns
        -------
        str or None
            arXiv ID if specified, otherwise None.
        """
        return None

    @property
    def doi(self) -> str | None:
        """Get DOI.

        Returns
        -------
        str or None
            DOI if specified, otherwise None.
        """
        return None

    @staticmethod
    def get_uid_from_identifiers(identifiers: tuple[str | None, ...]) -> str:
        """Generate a deterministic UID for a list of given paper identifiers.

        Papers with the same values for the given identifiers get the same UID.
        Missing values should have the value `None`, which is considered a value
        by itself. Then, identifiers `(a, None)` and identifiers `(a, b)` have
        two different UIDs.

        Parameters
        ----------
        identifiers
            Values of the identifiers.

        Returns
        -------
        str
            A deterministic UID computed from the identifiers.

        Raises
        ------
        ValueError
            If all identifiers are `None`.
        """
        if all(x is None for x in identifiers):
            raise ValueError(
                f"Identifiers = {identifiers} are all `None`, UID cannot be computed."
            )
        else:
            data = str(identifiers).encode()
            hashed = hashlib.md5(data).hexdigest()  # nosec
            return hashed

    @property
    def uid(self) -> str:
        """Generate deterministic UID for an article.

        The UID is usually created by hashing the identifiers of the article.
        If no identifier is available, then the unique ID is computed by hashing
        the whole content of the article.

        Returns
        -------
        str
            A deterministic UID.
        """
        identifiers = (self.pubmed_id, self.pmc_id, self.arxiv_id, self.doi)

        # If no identifier is available, hash whole article content.
        if all(x is None for x in identifiers):
            logger.warning(
                "No identifier available, generating UID by hashing whole "
                f'content for article "{self.title}"'
            )
            m = hashlib.md5()  # nosec
            m.update(self.title.encode())
            m.update(str(list(self.authors)).encode())
            m.update(str(list(self.abstract)).encode())
            m.update(str(list(self.paragraphs)).encode())
            return m.hexdigest()

        # If at least one identifier is available, hash identifiers.
        else:
            return self.get_uid_from_identifiers(identifiers)


class JATSXMLParser(ArticleParser):
    """Parser for JATS XML files.

    This could be used for articles from PubMed Central, bioRxiv, and medRxiv.

    Parameters
    ----------
    xml_stream
        The xml stream of the article.
    """

    def __init__(self, xml_stream: IO[Any]) -> None:
        super().__init__()
        self.content = ElementTree.parse(xml_stream)
        if self.content.getroot().tag == "pmc-articleset":
            self.content = self.content.find("article")
        self.ids = self.get_ids()

    @classmethod
    def from_string(cls, xml_string: str) -> JATSXMLParser:
        """Read xml string and instantiate JATSXML Parser.

        Parameters
        ----------
        xml_string
            Raw content of the article

        Returns
        -------
        JATSXMLParser
            Parser containing the article content.
        """
        with StringIO(xml_string) as stream:
            obj = cls(stream)
        return obj

    @classmethod
    def from_xml(cls, path: str | Path) -> JATSXMLParser:
        """Read xml file and instantiate JATSXML Parser.

        Parameters
        ----------
        path
            Path to the article (with .xml extension)

        Returns
        -------
        JATSXMLParser
            Parser containing the article content.
        """
        with open(path) as fh:
            obj = cls(fh)
        return obj

    @classmethod
    def from_zip(cls, path: str | Path) -> JATSXMLParser:
        """Read xml file from a zipped .meca folder and instantiate JATSXML Parser.

        Parameters
        ----------
        path
            Path to the article (with .meca extension)

        Returns
        -------
        JATSXMLParser
            Parser containing the article content.
        """
        with ZipFile(path) as myzip:
            xml_files = [
                x
                for x in myzip.namelist()
                if x.startswith("content/") and x.endswith(".xml")
            ]

            if len(xml_files) != 1:
                raise ValueError(
                    "There needs to be exactly one .xml file inside of content/"
                )

            xml_file = xml_files[0]

            # Parsing logic
            with myzip.open(xml_file, "r") as fh:
                obj = cls(fh)
        return obj

    @property
    def title(self) -> str:
        """Get the article title.

        Returns
        -------
        str
            The article title.
        """
        titles = self.content.find("./front/article-meta/title-group/article-title")
        return self._element_to_str(titles)

    @property
    def authors(self) -> list[str]:
        """Get all author names.

        Returns
        -------
        list[str]
            Every author, in the format "Given_Name(s) Surname".
        """
        authors = self.content.findall(
            "./front/article-meta/contrib-group/contrib[@contrib-type='author']"
        )
        authors_list: list[str] = []
        for author in authors:
            given_names = self._element_to_str(author.find("name/given-names"))
            surname = self._element_to_str(author.find("name/surname"))
            if given_names == "" or surname == "":
                # In rare cases, an author may not have a given name or a surname,
                # e.g. it could be an organization. We decide to skip those.
                continue
            author_str = given_names + " " + surname
            authors_list.append(author_str.strip())
        return authors_list

    @property
    def abstract(self) -> list[str]:
        """Get a sequence of paragraphs in the article abstract.

        Returns
        -------
        list[str]
            The paragraphs of the article abstract.
        """
        abstract = self.content.find("./front/article-meta/abstract")
        abstract_list: list[str] = []
        if abstract:
            for _, text in self.parse_section(abstract):
                abstract_list.append(text)
        return abstract_list

    @property
    def paragraphs(self) -> list[tuple[str, str]]:
        """Get all paragraphs and titles of sections they are part of.

        Paragraphs can be parts of text body, or figure or table captions.

        Returns
        -------
        list[tuple[str, str]], where each tuple contains:
            section : str
                The section title.
            text : str
                The paragraph content.
        """
        paragraph_list: list[tuple[str, str]] = []

        # Paragraphs of text body
        body = self.content.find("./body")
        if body:
            paragraph_list.extend(self.parse_section(body))

        # Figure captions
        figs = self.content.findall("./body//fig")
        for fig in figs:
            fig_captions = fig.findall("caption")
            if fig_captions is None:
                continue
            caption = " ".join(self._element_to_str(c) for c in list(fig_captions))
            if caption:
                paragraph_list.append(("Figure Caption", caption))

        # Table captions
        tables = self.content.findall("./body//table-wrap")
        for table in tables:
            caption_elements = table.findall("./caption/p") or table.findall(
                "./caption/title"
            )
            if caption_elements is None:
                continue
            caption = " ".join(self._element_to_str(c) for c in caption_elements)
            if caption:
                paragraph_list.append(("Table Caption", caption))

        return paragraph_list

    @property
    def pubmed_id(self) -> str | None:
        """Get Pubmed ID.

        Returns
        -------
        str or None
            Pubmed ID if specified, otherwise None.
        """
        return self.ids.get("pmid")

    @property
    def pmc_id(self) -> str | None:
        """Get PMC ID.

        Returns
        -------
        str or None
            PMC ID if specified, otherwise None.
        """
        return self.ids.get("pmc")

    @property
    def doi(self) -> str | None:
        """Get DOI.

        Returns
        -------
        str or None
            DOI if specified, otherwise None.
        """
        return self.ids.get("doi")

    @property
    def date(self) -> datetime.datetime | None:
        """Get the publication date or the e-publication date if it exists.

        Returns
        -------
        datetime.datetime or None
            Date if specified, otherwise None.
        """
        all_dates = {}
        dates = self.content.findall("./front/article-meta/pub-date")

        for date in dates:
            if "pub-type" not in date.attrib.keys() or (
                date.attrib["pub-type"] != "pub" and date.attrib["pub-type"] != "epub"
            ):
                continue
            year = int(date.find("year").text)
            month = (
                int(date.find("month").text) if date.find("month") is not None else 1
            )
            day = int(date.find("day").text) if date.find("day") is not None else 1
            all_dates[date.attrib["pub-type"]] = datetime.datetime(year, month, day)

        return all_dates.get("pub") if all_dates.get("pub") else all_dates.get("epub")

    @property
    def journal(self) -> str | None:
        """Get journal.

        Returns
        -------
        str or None
            Journal if specified, otherwise None.
        """
        journal_info = self.content.findall("./front/journal-meta/issn")
        if journal_info is None or not journal_info or journal_info[0].text is None:
            return None

        return journal_info[0].text.strip()

    @property
    def article_type(self) -> str | None:
        """Get article type.

        Returns
        -------
        str or None
            Article Type if specified, otherwise None.
        """
        article_type = self.content.find(".").attrib.get("article-type")
        if article_type:
            return article_type.strip()
        else:
            return article_type

    def get_ids(self) -> dict[str, str]:
        """Get all specified IDs of the paper.

        Returns
        -------
        ids : dict
            Dictionary whose keys are ids type and value are ids values.
        """
        ids = {}
        article_ids = self.content.findall("./front/article-meta/article-id")

        for article_id in article_ids:
            if "pub-id-type" not in article_id.attrib.keys():
                continue

            ids[article_id.attrib["pub-id-type"]] = article_id.text

        return ids

    def parse_section(self, section: Element) -> Generator[tuple[str, str], None, None]:
        """Parse section children depending on the tag.

        Parameters
        ----------
        section
            The input XML element.

        Returns
        -------
        str
            The section title.
        str
            A parsed string representation of the input XML element.
        """
        sec_title = self._element_to_str(section.find("title"))
        if sec_title == "Author contributions":
            return
        for element in section:
            if element.tag == "sec":
                yield from self.parse_section(element)
            elif element.tag in {"title", "caption", "fig", "table-wrap", "label"}:
                continue
            else:
                text = self._element_to_str(element)
                if text:
                    yield sec_title, text

    def _inner_text(self, element: Element) -> str:
        """Convert all inner text and sub-elements to one string.

        In short, we collect all the inner text while also converting all
        sub-elements that we encounter to strings using ``self._element_to_str``.
        All escaped HTML in the raw text is unescaped.
        For example, if schematically the element is given by
            element = "<p>I <bold>like</bold> python &amp; ice cream.<p>"
        then ``_inner_text(element)`` would give
            "I like python & ice cream."
        provided that "<bold>like</bold>" is resolved to "like" by the
        ``self._element_to_str`` method.

        Parameters
        ----------
        element
            The input XML element.

        Returns
        -------
        str
            The inner text and sub-elements converted to one single string.
        """
        text_parts = [html.unescape(element.text or "")]
        for sub_element in element:
            # recursively parse the sub-element
            text_parts.append(self._element_to_str(sub_element))
            # don't forget the text after the sub-element
            text_parts.append(html.unescape(sub_element.tail or ""))
        return unicodedata.normalize("NFKC", "".join(text_parts)).strip()

    def _element_to_str(self, element: Element | None) -> str:
        """Convert an element and all its contents to a string.

        Parameters
        ----------
        element
            The input XML element.

        Returns
        -------
        str
            A parsed string representation of the input XML element.
        """
        if element is None:
            return ""

        if element.tag in {
            "bold",
            "italic",
            "monospace",
            "p",
            "sc",
            "styled-content",
            "underline",
            "xref",
        }:
            # Mostly styling tags for which getting the inner text is enough.
            # Currently this is the same as the default handling. Writing it out
            # explicitly here to decouple from the default handling, which may
            # change in the future.
            return self._inner_text(element)
        elif element.tag == "sub":
            return f"_{self._inner_text(element)}"
        elif element.tag == "sup":
            return f"^{self._inner_text(element)}"
        elif element.tag in {
            "disp-formula",
            "email",
            "ext-link",
            "inline-formula",
            "uri",
        }:
            return ""
        else:
            # Default handling for all other element tags
            return self._inner_text(element)


class PubMedXMLParser(ArticleParser):
    """Parser for PubMed abstract."""

    def __init__(self, data: str | bytes) -> None:
        super().__init__()
        self.content = ElementTree.fromstring(data)

    @property
    def title(self) -> str:
        """Get the article title.

        Returns
        -------
        str
            The article title.
        """
        title = self.content.find("./MedlineCitation/Article/ArticleTitle")
        if title is None:
            raise ValueError("No title found in the article.")
        return "".join(title.itertext())

    @property
    def authors(self) -> list[str]:
        """Get all author names.

        Returns
        -------
        list[str]
            All authors.
        """
        authors = self.content.find("./MedlineCitation/Article/AuthorList")

        if authors is None:
            # No author to parse: stop and return an empty iterable.
            return []  # noqa

        authors_list: list[str] = []
        for author in authors:
            # Author entries with 'ValidYN' == 'N' are incorrect entries:
            # https://dtd.nlm.nih.gov/ncbi/pubmed/doc/out/190101/att-ValidYN.html.
            if author.get("ValidYN") == "Y":
                # 'LastName' is a required field if there is no 'CollectiveName'.
                lastname = author.find("LastName")
                # 'ForeName' is an optional field only used with 'LastName'.
                forenames = author.find("ForeName")

                parts = (forenames, lastname)
                name = [x.text for x in parts if x is not None]
                if len(name) > 0:
                    authors_list.append(" ".join(name))
        return authors_list

    @property
    def abstract(self) -> list[str]:
        """Get a sequence of paragraphs in the article abstract.

        Returns
        -------
        list[str]
            The paragraphs of the article abstract.
        """
        abstract = self.content.find("./MedlineCitation/Article/Abstract")

        if abstract is None:
            # No paragraphs to parse: stop and return an empty iterable.
            return []  # noqa

        paragraphs = abstract.iter("AbstractText")
        abstract_list: list[str] = []
        if paragraphs is not None:
            for paragraph in paragraphs:
                abstract_list.append("".join(paragraph.itertext()))
        return abstract_list

    @property
    def paragraphs(self) -> list[tuple[str, str]]:
        """Get all paragraphs and titles of sections they are part of.

        Returns
        -------
        list of (str, str)
            For each paragraph a tuple with two strings is returned. The first
            is the section title, the second the paragraph content.
        """
        # No paragraph to parse in PubMed article sets: return an empty iterable.
        return []

    @property
    def pubmed_id(self) -> str | None:
        """Get Pubmed ID.

        Returns
        -------
        str or None
            Pubmed ID if specified, otherwise None.
        """
        pubmed_id = self.content.find("./MedlineCitation/PMID")
        return pubmed_id.text

    @property
    def pmc_id(self) -> str | None:
        """Get PMC ID.

        Returns
        -------
        str or None
            PMC ID if specified, otherwise None.
        """
        pmc_id = self.content.find(
            "./PubmedData/ArticleIdList/ArticleId[@IdType='pmc']"
        )
        return None if pmc_id is None else pmc_id.text

    @property
    def doi(self) -> str | None:
        """Get DOI.

        Returns
        -------
        str or None
            DOI if specified, otherwise None.
        """
        doi = self.content.find("./PubmedData/ArticleIdList/ArticleId[@IdType='doi']")
        return None if doi is None else doi.text

    @property
    def date(self) -> datetime.datetime | None:
        """Get the 'pubmed' date if it exists.

        Returns
        -------
        datetime.datetime or None
            Date if specified, otherwise None.
        """
        dates = self.content.findall("./PubmedData/History/PubMedPubDate")

        if dates is None:
            return None

        # Extract the date of the first publication on PubMed.
        possible_dates = [
            dates[i] for i in range(len(dates)) if dates[i].get("PubStatus") == "pubmed"
        ]

        if not possible_dates:
            return None

        date = possible_dates[0]

        year = int(date.find("Year").text)
        month = int(date.find("Month").text)
        day = int(date.find("Day").text)
        dt = datetime.datetime(year, month, day)
        return dt

    @property
    def journal(self) -> str | None:
        """Get journal.

        Returns
        -------
        str or None
            Journal if specified, otherwise None.
        """
        journal_issn = self.content.find("./MedlineCitation/Article/Journal/ISSN")
        return None if journal_issn is None else journal_issn.text.strip()

    @property
    def article_type(self) -> str | None:
        """Get article type.

        Returns
        -------
        str or None
            Article Type if specified, otherwise None.
        """
        publication_types = self.content.findall(
            "./MedlineCitation/Article/PublicationTypeList/PublicationType"
        )
        pt_str = [pt.text for pt in publication_types]
        return pt_str[0]


class CORD19ArticleParser(ArticleParser):
    """Parser for CORD-19 JSON files.

    Parameters
    ----------
    json_file
        The contents of a JSON-file from the CORD-19 database.
    """

    def __init__(self, json_file: dict[str, Any]) -> None:
        # data is a reference to json_file, so we shouldn't modify its contents
        self.data = json_file

        # Check top-level keys
        # the spec also includes "abstract" but it's missing from the PMC parses
        top_level_keys = {
            "paper_id",
            "metadata",
            "body_text",
            "bib_entries",
            "ref_entries",
            "back_matter",
        }
        if not top_level_keys.issubset(json_file.keys()):
            raise ValueError(
                "Incomplete JSON file. Missing keys: "
                f"{top_level_keys - set(json_file.keys())}"
            )

    @property
    def title(self) -> str:
        """Get the article title.

        Returns
        -------
        str
            The article title.
        """
        return self.data["metadata"]["title"]

    @property
    def authors(self) -> list[str]:
        """Get all author names.

        Returns
        -------
        list[str]
            Every author.
        """
        authors_list: list[str] = []
        for author in self.data["metadata"]["authors"]:
            author_str = " ".join(
                filter(
                    lambda part: part != "",
                    (
                        author["first"],
                        " ".join(author["middle"]),
                        author["last"],
                        author["suffix"],
                    ),
                )
            )
            authors_list.append(author_str)
        return authors_list

    @property
    def abstract(self) -> list[str]:
        """Get a sequence of paragraphs in the article abstract.

        Returns
        -------
        list of str
            The paragraphs of the article abstract.
        """
        if "abstract" not in self.data:
            return []

        return [paragraph["text"] for paragraph in self.data["abstract"]]

    @property
    def paragraphs(self) -> list[tuple[str, str]]:
        """Get all paragraphs and titles of sections they are part of.

        Returns
        -------
        list[tuple[str, str]], where each tuple contains:
            section : str
                The section title.
            text : str
                The paragraph content.
        """
        paragraph_list: list[tuple[str, str]] = []
        for paragraph in self.data["body_text"]:
            paragraph_list.append((paragraph["section"], paragraph["text"]))
        # We've always included figure/table captions like this
        for ref_entry in self.data["ref_entries"].values():
            paragraph_list.append(("Caption", ref_entry["text"]))
        return paragraph_list

    @property
    def pmc_id(self) -> str | None:
        """Get PMC ID.

        Returns
        -------
        str or None
            PMC ID if specified, otherwise None.
        """
        return self.data.get("paper_id")

    def __str__(self) -> str:
        """Get the string representation of the parser instance."""
        return f'CORD-19 article ID={self.data["paper_id"]}'


class TEIXMLParser(ArticleParser):
    """Parser for TEI XML files.

    Parameters
    ----------
    data
        String of a TEI XML file.
    """

    def __init__(self, data: str | bytes):
        self.content = ElementTree.fromstring(data)

        self.tei_namespace = {"tei": "http://www.tei-c.org/ns/1.0"}
        self._tei_ids: dict[str, str] | None = None

    @property
    def title(self) -> str:
        """Get the article title.

        Returns
        -------
        str
            The article title.
        """
        title = self.content.find(
            "./tei:teiHeader/tei:fileDesc/tei:titleStmt/", self.tei_namespace
        )
        if title is None:
            raise ValueError("No title found in the article.")
        return self._element_to_str(title)

    @property
    def authors(self) -> list[str]:
        """Get all author names.

        Returns
        -------
        list[str]
            Every author, in the format "Given_Name(s) Surname".
        """
        authors_list: list[str] = []
        for pers_name in self.content.findall(
            (
                "./tei:teiHeader/tei:fileDesc/tei:sourceDesc/tei:biblStruct/tei:analytic"
                "/tei:author/tei:persName"
            ),
            self.tei_namespace,
        ):
            parts = [
                pers_name.find("./tei:forename[@type='first']", self.tei_namespace),
                pers_name.find("./tei:forename[@type='middle']", self.tei_namespace),
                pers_name.find("./tei:surname", self.tei_namespace),
            ]

            parts = [self._element_to_str(part) for part in parts]
            author_list = " ".join([part for part in parts if part]).strip()
            if not author_list:
                raise ValueError("No author found.")
            authors_list.append(author_list)
        return authors_list

    @property
    def abstract(self) -> list[str]:
        """Get a sequence of paragraphs in the article abstract.

        Returns
        -------
        list[str]
            The paragraphs of the article abstract.
        """
        content = self.content.findall(
            "./tei:teiHeader/tei:profileDesc/tei:abstract/tei:div",
            self.tei_namespace,
        )
        abstract_list: list[str] = []
        if not content:
            content = self.content.findall(
                "./tei:teiHeader/tei:profileDesc/tei:abstract/tei:p",
                self.tei_namespace,
            )
            for elem in content:
                abstract_list.append(self._element_to_str(elem))
        else:
            text_elements = []
            for div in content:
                for child in div:
                    if not child.tag.endswith("head"):
                        text_elements.append(child)
            abstract_list.extend(self._build_texts(text_elements))
        return abstract_list

    @property
    def paragraphs(self) -> list[tuple[str, str]]:
        """Get all paragraphs and titles of sections they are part of.

        Paragraphs can be parts of text body, or figure or table captions.

        Returns
        -------
        list[tuple[str, str]], where each tuple contains:
            section : str
                The section title.
            text : str
                The paragraph content.
        """
        paragraph_list = []
        for div in self.content.findall(
            "./tei:text/tei:body/tei:div",
            self.tei_namespace,
        ):
            head = div.find("./tei:head", self.tei_namespace)
            section_title = self._element_to_str(head)
            text_elements = []
            for child in div:
                if not child.tag.endswith("head"):
                    text_elements.append(child)
            for text in self._build_texts(text_elements):
                paragraph_list.append((section_title, text))

        # Figure and Table Caption
        for figure in self.content.findall(
            "./tei:text/tei:body/tei:figure", self.tei_namespace
        ):
            caption = figure.find("./tei:figDesc", self.tei_namespace)
            caption_str = self._element_to_str(caption)
            if not caption_str:
                continue
            if figure.get("type") == "table":
                paragraph_list.append(("Table Caption", caption_str))
            else:
                paragraph_list.append(("Figure Caption", caption_str))
        return paragraph_list

    @property
    def arxiv_id(self) -> str | None:
        """Get arXiv ID.

        Returns
        -------
        str or None
            arXiv ID if specified, otherwise None.
        """
        return self.tei_ids.get("arXiv")

    @property
    def doi(self) -> str | None:
        """Get DOI.

        Returns
        -------
        str or None
            DOI if specified, otherwise None.
        """
        return self.tei_ids.get("DOI")

    @property
    def date(self) -> datetime.datetime | None:
        """Get the publication date if it exists.

        Returns
        -------
        datetime.datetime or None
            Date if specified, otherwise None.
        """
        date = self.content.find(
            "./tei:teiHeader/tei:fileDesc/tei:publicationStmt/tei:date",
            self.tei_namespace,
        )
        if date is None or date.text is None:
            return None
        date_str = self._element_to_str(date)
        return dateparser.parse(
            date_str,
            settings={
                "DATE_ORDER": "YMD",
                "PREFER_DAY_OF_MONTH": "first",
                "REQUIRE_PARTS": ["year"],
            },
        )

    @property
    def journal(self) -> str | None:
        """Get journal.

        Returns
        -------
        str or None
            Journal if specified, otherwise None.
        """
        journal = self.content.find(
            "./tei:teiHeader/tei:fileDesc/tei:publicationStmt/tei:publisher",
            self.tei_namespace,
        )
        if journal is None or journal.text is None:
            return None
        pattern = re.compile(r"\d{4}-?\d{3}[\dXx]")  # Match XXXX-XXXX and XXXXXXXX
        journal_issn = self._element_to_str(journal)
        match = pattern.match(journal_issn)
        if match:
            journal = match.group()
            if journal[4] != "-":
                journal = journal[:4] + "-" + journal[4:]
            return journal

        return None

    @property
    def tei_ids(self) -> dict[str, str]:
        """Extract all IDs of the TEI XML.

        Returns
        -------
        dict
            Dictionary containing all the IDs of the TEI XML content
            with the key being the ID type and the value being the ID value.
        """
        if self._tei_ids is None:
            self._tei_ids = {}
            for idno in self.content.findall(
                "./tei:teiHeader/tei:fileDesc/tei:sourceDesc/tei:biblStruct/tei:idno",
                self.tei_namespace,
            ):
                id_type = idno.get("type")
                self._tei_ids[id_type] = idno.text

        return self._tei_ids

    @staticmethod
    def _element_to_str(element: Element | None) -> str:
        """Convert an element and all its contents to a string.

        Parameters
        ----------
        element
            The input XML element.

        Returns
        -------
        str
            A parsed string representation of the input XML element.
        """
        if element is None:
            return ""
        return "".join(element.itertext())

    def _build_texts(self, elements: Iterable[Element]) -> Generator[str, None, None]:
        """Compose paragraphs and formulas to meaningful texts.

        In the abstract and main text of TEI XML parsers one finds a mix of
        <p> and <formula> tags. Several of these tags could be part of one
        sentence. This method tries to reconstruct sentences that are
        partitioned in this way. The formulas are replaced by the FORMULA
        placeholder.

        Parameters
        ----------
        elements
            An iterable of <p> and <formula> elements.

        Yields
        ------
        str
            One or more sentences as one string.

        Raises
        ------
        RuntimeError
            If a tag is encountered that is neither <p> nor <formula>.
        """
        # In TEI XML all tags are prefixed with the namespace.
        ns = self.tei_namespace["tei"]
        prefix = f"{{{ns}}}" if ns else ""
        # At every change ensure that there's no space at the end of text
        text = ""

        def if_non_empty(text_: str) -> Generator[str, None, None]:
            """Yield if text is non-empty and make sure it ends with a period."""
            if text_:
                if not text_.endswith("."):
                    text_ += "."
                yield text_

        for child in elements:
            if child.tag == prefix + "p":
                p_text = self._element_to_str(child).strip()
                if not p_text:
                    continue
                # Shouldn't this be p_text[-1] == "." ??
                if p_text[0] in string.ascii_uppercase:
                    # The sentence in the text has finished.
                    # Yield and start a new one
                    yield from if_non_empty(text)
                    text = p_text
                else:
                    # The sentence in the text continues
                    text += " " + p_text
            elif child.tag == prefix + "formula":
                # Maybe use FORMULA-BLOCK instead?
                text += " FORMULA"
            elif child.tag == prefix + "note":
                # Skip the note tags as it is most likely missparsing by grobid.
                continue
            elif child.tag == prefix + "ref" or child.tag == prefix + "figure":
                # Most likely a missparsing from grobid but still contains relevant info
                ref_text = self._element_to_str(child).strip()
                text += " " + ref_text

            else:
                all_text = "".join(self._element_to_str(e) for e in elements)
                raise RuntimeError(
                    f"Unexpected tag: {child.tag}\nall text:\n{all_text}"
                )

        # Yield the last remaining text
        yield from if_non_empty(text)


class XOCSXMLParser(ArticleParser):
    """Parser for the XML format of the SCOPUS article XML."""

    def __init__(self, data: str | bytes) -> None:
        super().__init__()

        self.content = ElementTree.fromstring(data)

        if "full-text-retrieval-response" in self.content.tag:
            self.type = "full"
            self.namespace = {
                "ce": "http://www.elsevier.com/xml/common/dtd",
                "dc": "http://purl.org/dc/elements/1.1/",
                "default": "http://www.elsevier.com/xml/svapi/article/dtd",
                "ja": "http://www.elsevier.com/xml/ja/dtd",
                "prism": "http://prismstandard.org/namespaces/basic/2.0/",
                "xocs": "http://www.elsevier.com/xml/xocs/dtd",
            }

        elif "abstracts-retrieval-response" in self.content.tag:
            self.type = "abstract"
            self.namespace = {
                "ce": "http://www.elsevier.com/xml/ani/common",
                "dc": "http://purl.org/dc/elements/1.1/",
                "default": "http://www.elsevier.com/xml/svapi/abstract/dtd",
                "prism": "http://prismstandard.org/namespaces/basic/2.0/",
                "xocs": "http://www.elsevier.com/xml/xocs/dtd",
            }
        else:
            raise ValueError("Invalid XML format.")

    @staticmethod
    def _strip_text(text: str) -> str:
        """Strip text.

        Parameters
        ----------
        text
            The input text.

        Returns
        -------
        str
            The stripped text.
        """
        return "\n".join(line.strip() for line in text.split("\n") if line.strip())

    @property
    def title(self) -> str:
        """Get title.

        Returns
        -------
        str or None
            Title if specified, otherwise None.
        """
        return self._strip_text(
            self.content.find("default:coredata", self.namespace)
            .find("dc:title", self.namespace)
            .text
        )

    @property
    def abstract(self) -> list[str]:
        """Get abstract.

        Returns
        -------
        list[str]
            Abstract if specified, otherwise None.
        """
        if self.type == "abstract":
            abstract = self.content.find(
                "default:coredata/dc:description/abstract", self.namespace
            )
        else:
            abstract = self.content.find(
                "default:coredata/dc:description", self.namespace
            )
        abstract_list = []
        if abstract.find("ce:para", self.namespace) is not None:
            abstract_list.append(
                self._strip_text(abstract.find("ce:para", self.namespace).text)
            )
        else:
            abstract_list.append(self._strip_text(abstract.text))
        return abstract_list

    @property
    def authors(self) -> list[str]:
        """Get authors.

        Returns
        -------
        list[str]
            List of authors.
        """
        if self.type == "abstract":
            authors = self.content.findall(
                "default:authors/default:author", self.namespace
            )
        else:
            authors = self.content.findall(
                "default:coredata/dc:creator", self.namespace
            )

        authors_list: list[str] = []
        for author in authors:
            if author.find("ce:indexed-name", self.namespace) is not None:
                authors_list.append(
                    author.find("ce:indexed-name", self.namespace).text.strip()
                )
            else:
                authors_list.append(author.text.strip())
        return authors_list

    @property
    def pubmed_id(self) -> str | None:
        """Get PubMed ID.

        Returns
        -------
        str or None
            PubMed ID if specified, otherwise None.
        """
        if self.content.find("default:pubmed-id", self.namespace) is not None:
            return self.content.find("default:pubmed-id", self.namespace).text
        else:
            return None

    @property
    def pmc_id(self) -> str | None:
        """Get PMC ID."""
        return None

    @property
    def doi(self) -> str | None:
        """Get DOI.

        Returns
        -------
        str or None
            DOI if specified, otherwise None.
        """
        if self.content.find("default:coredata/prism:doi", self.namespace) is not None:
            return self.content.find("default:coredata/prism:doi", self.namespace).text
        else:
            return None

    @property
    def date(self) -> datetime.datetime | None:
        """Get date.

        Returns
        -------
        datetime.datetime or None
            Date if specified, otherwise None.
        """
        date = self.content.find("default:coredata/prism:coverDate", self.namespace)

        if date is None:
            return None
        year, month, day = date.text.split("-")

        return datetime.datetime(int(year), int(month), int(day))

    @property
    def journal(self) -> str:
        """Get journal.

        Returns
        -------
        str or None
            Date if specified, otherwise None.
        """
        journal = self.content.find(
            "default:coredata/prism:issn", self.namespace
        ).text.split(" ")[0]
        if len(journal.split("-")) == 1:
            journal = journal[:4] + "-" + journal[4:]
        return journal

    @property
    def uid(self) -> str:
        """Get UID.

        Returns
        -------
        str or None
            UID if specified, otherwise None.
        """
        return self.content.find("default:coredata/prism:doi", self.namespace).text

    @property
    def paragraphs(self) -> list[tuple[str, str]]:
        """Get paragraphs.

        Returns
        -------
        list[tuple[str, str]]
            Paragraphs generator.
        """
        paragraphs_list: list[tuple[str, str]] = []
        if self.type == "full":
            xdoc = self.content.find(
                "default:originalText/xocs:doc/xocs:serial-item", self.namespace
            )
            body = self.content.find(".//ja:body", self.namespace)
            floats = (
                self.content.findall(".//ce:figure", self.namespace)
                + self.content.findall(".//ce:table", self.namespace)
                + self.content.findall(".//ce:text-box", self.namespace)
            )

            if body:
                if xdoc.find("ja:simple-article", self.namespace):
                    sections = body.findall(".//ce:section", self.namespace)
                    for section in sections:
                        for paragraph in section.findall("ce:para", self.namespace):
                            paragraphs_list.append(
                                ("", self._strip_text(paragraph.text))
                            )

                elif xdoc.find("ja:article", self.namespace):
                    all_sections = self.content.findall(".//ce:section", self.namespace)
                    for section in all_sections:
                        section_title = "".join(
                            section.find("ce:section-title", self.namespace).itertext()
                        )
                        for paragraph in section.findall("ce:para", self.namespace):
                            paragraphs_list.append(
                                (
                                    self._strip_text(section_title),
                                    self._strip_text("".join(paragraph.itertext())),
                                )
                            )
                elif xdoc.find("ja:converted-article", self.namespace):
                    raise NotImplementedError("converted-article not implemented.")
                else:
                    raise ValueError("Invalid XOCS-ARTICLE format.")

            if floats:
                for float_ in floats:
                    label = float_.find(".//ce:label", self.namespace)
                    if label is None:
                        label = ""
                    else:
                        label = label.text.strip()

                    full_par = ""
                    for par in float_.findall(
                        ".//ce:caption/ce:simple-para", self.namespace
                    ):
                        full_par += par.text.strip()

                    paragraphs_list.append((label, full_par))
        return paragraphs_list

    @property
    def article_type(self) -> str | None:
        """Get article type.

        Returns
        -------
        str or None
            Article Type if specified, otherwise None.
        """
        dochead = self.content.find(".//ce:dochead", self.namespace)
        if dochead is None or dochead.find("ce:textfn", self.namespace) is None:
            return None
        else:
            return dochead.find("ce:textfn", self.namespace).text.strip()


class PDFParser(ArticleParser):
    """Parser for general PDF files using PyPDF2.

    Parameters
    ----------
    pdf_bytes
        The contents of a PDF file
    chunk_size
        How many tokens a 'paragraph' should consist of.
    """

    def __init__(self, pdf_bytes: bytes, chunk_size: int):
        # We convert the bytes object back for the PDFReader
        reader = PdfReader(io.BytesIO(pdf_bytes))
        self.chunk_size = chunk_size
        self.pdf_text = " ".join(page.extract_text() for page in reader.pages)

    @property
    def paragraphs(self) -> list[tuple[str, str]]:
        """Get all paragraphs from the PDF file.

        A paragraph here is not a logical part of the PDF, rather it is
        arbitrarily defined by the chunk_size parameter.

        Returns
        -------
        list[tuple[str, str]], where each tuple contains:
           section : str
               The section title.
           text : str
               The paragraph content.
        """
        paragraph_list: list[tuple[str, str]] = []
        tokens = self.pdf_text.split()
        chunk_size = min(len(tokens), self.chunk_size)
        n_paragraphs = len(tokens) // chunk_size
        for i in range(n_paragraphs):
            paragraph_list.append(
                (
                    "Article Chunk",
                    " ".join(tokens[i * chunk_size : (i + 1) * chunk_size]),
                )
            )
        return paragraph_list

    @property
    def title(self) -> str:
        """We cannot get the article title from an arbitrary PDF."""
        return ""

    @property
    def authors(self) -> list[str]:
        """We cannot get the authors from an arbitrary PDF."""
        return []

    @property
    def abstract(self) -> list[str]:
        """We cannot get the abstract from an arbitrary PDF."""
        return []
