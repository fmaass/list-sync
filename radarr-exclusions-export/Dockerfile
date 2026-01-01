# Radarr Exclusions Export Service
# Lightweight Python container for exporting Radarr exclusions to JSON

FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy export script
COPY export_radarr_exclusions.py .
RUN chmod +x export_radarr_exclusions.py

# Create data directory
RUN mkdir -p /data

# Environment defaults
ENV RADARR_URL=http://radarr:7878 \
    OUTPUT_FILE=/data/blocklist.json \
    LOG_LEVEL=INFO

# Run export script
CMD ["python", "-u", "export_radarr_exclusions.py"]

