import gzip
import json
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from scholaretl.app.config import Settings
from scholaretl.app.dependencies import get_settings
from scholaretl.app.main import app

ROOT_PATH = Path(__file__).resolve().parent.parent  # root of the repository
CORD19_SAMPLE_PATH = ROOT_PATH / "tests" / "data" / "cord19"
CORD19_SAMPLE_ALL_JSON_PATHS = sorted(CORD19_SAMPLE_PATH.rglob("*.json"))

os.environ["SCOPUS_API_KEY"] = "3c5bd42cd3009af76434be909daee62a"


@pytest.fixture(scope="session")
def test_data_path():
    """Path to data folder."""
    return ROOT_PATH / "tests" / "data"


@pytest.fixture(scope="session")
def jsons_path():
    """Path to a directory where jsons are stored."""
    jsons_path = CORD19_SAMPLE_PATH
    assert jsons_path.exists()

    return jsons_path


@pytest.fixture(
    params=CORD19_SAMPLE_ALL_JSON_PATHS,
    ids=(path.name for path in CORD19_SAMPLE_ALL_JSON_PATHS),
)
def real_json_file(request):
    with request.param.open() as fp:
        yield json.load(fp)


@pytest.fixture()
def pubmed_xml_gz_path(test_data_path, tmp_path):
    pubmed_path = test_data_path / "pubmed_articles.xml"
    zip_pubmed_path = tmp_path / "pubmed_articles.xml.gz"
    with (
        open(pubmed_path, "rb") as file_in,
        gzip.open(zip_pubmed_path, "wb") as gzip_out,
    ):
        gzip_out.writelines(file_in)
    return zip_pubmed_path


@pytest.fixture(name="app_client")
def client_fixture():
    """Get client and clear app dependency_overrides."""
    app_client = TestClient(app)
    test_settings = Settings(grobid={"url": "fake-grobid-url"})
    app.dependency_overrides[get_settings] = lambda: test_settings
    yield app_client
    app.dependency_overrides.clear()
