FROM mtkhmcr.mediatek.inc/public/python:3.11-slim AS internalimage

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ---------------------------------------------------------------------------
# Configure PIP to use internal mirror
# ---------------------------------------------------------------------------
ENV PIP_INDEX_URL=http://oa-mirror.mediatek.inc/repository/pypi/simple
ENV PIP_TRUSTED_HOST=oa-mirror.mediatek.inc

WORKDIR /app

COPY requirements.txt .

ARG PIP_INDEX_URL
RUN python -m pip install --upgrade pip \
    && if [ -n "$PIP_INDEX_URL" ]; \
    then \
        pip install --no-cache-dir --index-url "$PIP_INDEX_URL" -r requirements.txt; \
    else \
        pip install --no-cache-dir -r requirements.txt; \
    fi

COPY . .

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "api.server:app", "--host", "0.0.0.0", "--port", "8000"]
