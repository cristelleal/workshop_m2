FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN grep -v matplotlib requirements.txt > req-detector.txt \
 && pip install --no-cache-dir -r req-detector.txt \
 && useradd --system --uid 10001 detector

COPY resilience_ml/ resilience_ml/
COPY detector.py .
COPY models/ models/

USER detector
EXPOSE 9105
ENTRYPOINT ["python", "detector.py"]
CMD ["--prom-url", "http://prometheus:9090", "--loki-url", "http://loki:3100", "--model", "models/baseline.joblib"]
