FROM python:3.11-slim

# Install system dependencies (needed for some grpc/cryptography builds if wheels miss)
# netcat is useful for checking DB readiness
RUN apt-get update && apt-get install -y \
    gcc \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make entrypoint executable
RUN chmod +x entrypoint.sh

# Expose gRPC port
EXPOSE 50051

# Default environment variables
ENV PYTHONUNBUFFERED=1

ENTRYPOINT ["./entrypoint.sh"]
