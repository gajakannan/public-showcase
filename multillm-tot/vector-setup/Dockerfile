FROM python:3.11-slim-bullseye

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir "openai" "qdrant-client>=1.6.4,<2.0.0"

# CMD ["python", "upload_underwriting_to_qdrant.py", "--host", "qdrant", "--port", "6333"]
CMD ["python", "upload_underwriting_to_qdrant.py"]
