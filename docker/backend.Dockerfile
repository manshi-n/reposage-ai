FROM python:3.11-slim

WORKDIR /app

# System deps: git (cloning), node (eslint/npm audit via npx), build tools for a few python wheels
RUN apt-get update && apt-get install -y --no-install-recommends \
        git curl build-essential \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
