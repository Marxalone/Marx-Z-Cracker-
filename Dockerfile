FROM python:3.9-slim

WORKDIR /app

# Copy requirements first to cache dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the code
COPY . .

# Create temp directory
RUN mkdir -p /app/tmp

# Start both FastAPI and the bot
CMD sh -c "uvicorn backend.app:app --host 0.0.0.0 --port 8000 & python -m bot.main"
