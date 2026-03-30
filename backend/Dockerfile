FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends git curl && rm -rf /var/lib/apt/lists/* \
    && git config --global user.email "pipeline@scm-portal.local" \
    && git config --global user.name "SCM Portal" \
    && curl -fsSL https://get.docker.com | sh

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /data

ENV DATABASE_URL=sqlite+aiosqlite:////data/audit.db
ENV REPO_PATH=/repo

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
