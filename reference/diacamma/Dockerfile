FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=deployment.settings \
    SYNDIC_DATA_DIR=/data

RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libglib2.0-0 libgl1 libegl1 libxkbcommon0 libdbus-1-3 \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements-web.txt
RUN apt-get update && apt-get install -y --no-install-recommends libmagic1 poppler-utils locales \
    && localedef -i fr_FR -f UTF-8 fr_FR.UTF-8 \
    && localedef -i en_US -f UTF-8 en_US.UTF-8 \
    && rm -rf /var/lib/apt/lists/*
ENV LANG=fr_FR.UTF-8
COPY . .
RUN pip install --no-cache-dir --no-deps . \
    && useradd --uid 10001 --create-home syndic \
    && mkdir /data && chown syndic:syndic /data

USER syndic
EXPOSE 8000
ENTRYPOINT ["python", "-m", "deployment.bootstrap"]
CMD ["gunicorn", "deployment.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-"]
