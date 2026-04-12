FROM python:3.13-slim

WORKDIR /app

# Heavy deps first (rarely change, cached separately)
RUN pip install sentence-transformers==4.1.0

# App + dev deps (lighter, changes more often)
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

# Pre-download embedding model during build
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-base')"

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
