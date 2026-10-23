FROM python:3.13-slim

# Sortida sense buffers per veure els logs en directe a Dokploy
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Usuari sense privilegis per executar l'aplicació
RUN addgroup --system app && adduser --system --ingroup app app

# Dependències (capa cachejable)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Codi de l'aplicació
COPY . .
RUN chmod +x /app/entrypoint.sh && chown -R app:app /app

USER app

EXPOSE 8000

# Migracions + collectstatic + gunicorn (envia SIGTERM correctament a gunicorn)
ENTRYPOINT ["/app/entrypoint.sh"]
