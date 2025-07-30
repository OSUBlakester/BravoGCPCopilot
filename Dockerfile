# Multi-environment Docker build for Bravo AAC Application
FROM python:3.12-slim

# Recommended: Set environment variables for non-interactive commands
ENV DEBIAN_FRONTEND=noninteractive

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for psycopg2-binary and others
# libpq-dev for psycopg2-binary
# build-essential for general compilation if any other packages need it in the future
# curl for health checks
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY . .

# Install uv for MCP server
RUN pip install uv

# Create keys directory for service account files
RUN mkdir -p /keys

# Cloud Run expects the application to listen on the port specified by the PORT environment variable
ENV PORT 8080
ENV PYTHONPATH=/app

# Default environment (can be overridden)
ENV ENVIRONMENT=production

# Expose the port (informative, Cloud Run uses health checks)
EXPOSE ${PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Command to run your application using Gunicorn
# Direct Gunicorn's stdout/stderr to the console, which Cloud Logging captures.
# --error-logfile - : direct errors to stderr (Cloud Logging captures stderr well)
# --access-logfile - : direct access logs to stdout
# --log-file - : (deprecated/overridden) should not be used if using above
CMD ["sh", "-c", "exec gunicorn --worker-class uvicorn.workers.UvicornWorker --bind \"0.0.0.0:$PORT\" server:app --error-logfile - --access-logfile -"]