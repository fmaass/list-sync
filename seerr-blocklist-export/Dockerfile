# Seerr Blocklist Export Service
# Lightweight Python container for exporting Seerr blacklist to JSON

FROM python:3.11-alpine

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy export script
COPY export_seerr_blocklist.py .
RUN chmod +x export_seerr_blocklist.py

# Create data directory
RUN mkdir -p /data

# Environment defaults
ENV SEERR_URL=http://jellyseerr:5055 \
    OUTPUT_FILE=/data/blocklist.json \
    LOG_LEVEL=INFO

# Run export script
CMD ["python", "-u", "export_seerr_blocklist.py"]

