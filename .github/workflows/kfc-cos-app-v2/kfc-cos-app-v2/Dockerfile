FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create directory for database
RUN mkdir -p /app/data

# Set environment variables
ENV DB_PATH=/app/data/kfc_cos.db
ENV NORMATIVI_PATH=/app/normativi.xlsx
ENV PORT=8080

# Expose port
EXPOSE 8080

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "--timeout", "120", "app:app"]

