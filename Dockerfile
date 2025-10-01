FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 museum && \
    mkdir -p /app /tmp && \
    chown -R museum:museum /app /tmp

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY app.py .

# Switch to non-root user
USER museum

# Resource limits will be set via docker-compose
# Network isolation will be set via docker-compose

EXPOSE 5000

CMD ["python", "app.py"]
