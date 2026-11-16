# ---- Étape 1 : installation des dépendances ----
FROM python:3.13-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- Étape 2 : image finale légère, utilisateur non-root ----
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
WORKDIR /srv
COPY --from=builder /install /usr/local
COPY app/ ./app/
RUN useradd --uid 10001 --no-create-home appuser
USER 10001
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
