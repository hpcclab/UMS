FROM python:3.8
HEALTHCHECK CMD wget -q localhost:8080/healthz || exit 1
WORKDIR /src
COPY requirements.txt .
RUN pip install -r requirements.txt \
    && pip install --pre --upgrade kubernetes
CMD kopf run app/index.py app/pods.py --verbose --all-namespaces --liveness=http://0.0.0.0:8080/healthz
ENV PYTHONPATH /src
COPY share share/
COPY app app/