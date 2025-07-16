FROM python:3.9-slim

WORKDIR /app

# Set Python path
ENV PYTHONPATH=/app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Create temp dir
RUN mkdir -p /app/tmp

# Start services
CMD sh -c "uvicorn backend.app:app --host 0.0.0.0 --port 8000 & python -m bot.main"