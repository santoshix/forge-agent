FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home forge
COPY . .
RUN mkdir -p /app/runtime && chown -R forge:forge /app
USER forge
EXPOSE 8001
CMD ["python", "-m", "uvicorn", "forge.api:app", "--host", "0.0.0.0", "--port", "8001"]
