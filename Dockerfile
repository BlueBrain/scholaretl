FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get -y update
RUN apt-get -y install curl

RUN pip install --no-cache-dir --upgrade pip
COPY ./ /code
RUN pip install --no-cache-dir /code
RUN rm -rf /code

WORKDIR /

EXPOSE 8080
CMD python -c "from scholaretl import __version__; print(__version__)"
