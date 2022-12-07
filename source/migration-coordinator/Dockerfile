FROM python:3.8
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt \
    && pip install --pre --upgrade kubernetes
ENV FLASK_APP main
#CMD flask init-db && flask run --host=0.0.0.0
CMD flask run --host=0.0.0.0
HEALTHCHECK CMD wget -q localhost || exit 1
RUN #mkdir /sqlite3
COPY wait-for-it.sh .
COPY main.py .
COPY app app
RUN chmod +x /app/wait-for-it.sh