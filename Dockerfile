FROM python:3.11-slim

# Keep Python output unbuffered (helps with Docker logs)
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install runtime dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy server sources
COPY . .

# Expose the server port (matches main.py DEFAULT PORT)
EXPOSE 8765

# Allow overriding host/port/mod password via env
ENV HOST=0.0.0.0
ENV PORT=8765
ENV MOD_PASSWORD=admin123

CMD ["python", "main.py"]
