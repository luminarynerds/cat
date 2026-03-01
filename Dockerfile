FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY app.py analyzer.py importer.py mustie.py dewey_tables.py ./
COPY templates/ templates/
COPY static/ static/
COPY data/ data/
COPY sample_data/ sample_data/

RUN mkdir -p uploads

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--timeout", "120", "app:app"]
