FROM python:3.13-slim
WORKDIR /app
COPY apps/server/pyproject.toml .
COPY apps/server/app app
RUN pip install --no-cache-dir .
EXPOSE 4000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "4000"]
