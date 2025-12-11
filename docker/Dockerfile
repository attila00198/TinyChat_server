FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install build dependencies required for some packages (cryptography, wheels)
# Keep the image lean by removing apt lists after install.
RUN apt-get update && \
	apt-get install -y --no-install-recommends \
		build-essential \
		libssl-dev \
		libffi-dev \
		cargo \
	&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --upgrade pip setuptools wheel && \
	pip install --no-cache-dir -r requirements.txt

# Copy application sources (from parent directory context)
COPY main.py generate_certs.py ./
COPY . .

# Create a non-root user for running the app
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8765

# Default environment (can be overridden at runtime)
ENV HOST=0.0.0.0
ENV PORT=8765

# Default command
CMD ["python", "main.py"]
