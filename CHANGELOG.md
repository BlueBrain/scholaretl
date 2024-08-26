# Changelog

All notable changes to the ETL parser will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.8.3] - 23.04.2024

### Fixed
- Small issue in journal name for JATS Parser.

## [1.8.2] - 17.04.2024

### Fixed
- Strip the article type for jats and xocs.
- Strip the journal ISSN for jats and Pubmed.
- Slightly modify jats parser to remove "Author contributions" and label attributes.

## [1.8.1] - 19.10.2023

### Fixed
- Pubmed Parser failing.

## [1.8.0] - 06.10.2023

### Changed
- TEIXML and Pubmed parsers' constructors are ingesting string or data. They are not accepting path anymore.

## [1.7.0] - 30.08.2023

### Fixed
- Further refining of TEI XML

### Added
- Create a new parser for CORE articles

## [1.6.1] 25.08.2023


### Fixed
- TEI parsing logic to account for grobid generated documents.

## [1.6.0] - 18.08.2023

### Added
- article_type parsing

### Changed
- Date parsing for TEI XML

### Fixed
-Pubmed abstract and title parsing against bold and italic (hopefully)

## [v1.5.0] - 25-07-2023
### Added
- Date and journal parsing in every parser.
- New properties in the abstract article class.
### Fixed
- Fixed pubmed abstract parsing.
- Migrated scopus parser to `article_parser.py`.
### Improved
- Made Article inherit from pydantic so that schema shows up in the API.

## [v1.4.0] - 26-06-2023
### Added
- Added PDF parsing through GROBID.

## [v1.3.0] - 26-06-2023
### Added
- Added the PyPDF parser.

## [v1.2.0] - 11-04-2023
Added the scopus parser support.

## [v1] - ?
Initial version
