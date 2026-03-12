FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first to leverage Docker layer cache
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Make sure imports from root directory work
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Run database migrations before starting the main worker
CMD bash -c "python -m db.migrations && python main.py"
