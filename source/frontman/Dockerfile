FROM python:3.8
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
CMD flask run --host=0.0.0.0
COPY app.py .
