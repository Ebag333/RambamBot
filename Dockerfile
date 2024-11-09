from python:3.13

workdir /
copy ./ .

ENV POETRY_HOME=/var/tmp/poetry
run curl -o poetry_install.py -sSL http://install.python-poetry.org && \
    python3 poetry_install.py && \
    rm poetry_install.py && \
    /var/tmp/poetry/bin/poetry config virtualenvs.create false && \
    /var/tmp/poetry/bin/poetry lock --no-update && \
    /var/tmp/poetry/bin/poetry install

EXPOSE 443

CMD ["python3", "rambam.py"]
