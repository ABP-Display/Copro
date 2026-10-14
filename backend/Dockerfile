FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
RUN useradd --uid 10001 --create-home copro && mkdir -p /app/media && chown copro:copro /app/media
USER copro
EXPOSE 8000
CMD ["python", "bootstrap.py"]
