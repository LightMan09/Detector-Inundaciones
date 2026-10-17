# SAPO API — imagen de producción (Docker 2 la consume vía JSON)
FROM python:3.12-slim

WORKDIR /srv/sapo

COPY pyproject.toml README.md ./
COPY src ./src
COPY data ./data
COPY visual ./visual

RUN pip install --no-cache-dir uv && uv pip install --system -e .

EXPOSE 8000
CMD ["uvicorn", "rally.main:app", "--host", "0.0.0.0", "--port", "8000"]
