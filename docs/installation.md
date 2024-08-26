# Installation
## From index
First of all, you need to have (or create) a **Personal Access Token**. You
can create it in your account settings. It should at least have the `read_api` scope.


```bash
GITLAB_TOKEN=... # see above
PYPI_URL=
pip install scholaretl --index-url https://__token__:$GITLAB_TOKEN@$PYPI_URL
```
## From source (development)

```bash
git clone git@bbpgitlab.epfl.ch:ml/bbs-etl.git
cd bbs-etl
pip install -e .[dev,doc]
```
