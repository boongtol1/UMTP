FROM python:3.11.11-slim

WORKDIR /UMTP

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .

CMD ["python", "src/run_csv_umtp.py"]