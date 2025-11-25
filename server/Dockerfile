FROM python:3.12-slim

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working dir
WORKDIR /app

# Copy pyproject.toml and uv.lock (if exists) for dependency caching
COPY pyproject.toml uv.lock* /app/

# Install dependencies using UV
# Use build arg to optionally include dev dependencies (for debug mode)
ARG INSTALL_DEV=false
RUN if [ "$INSTALL_DEV" = "true" ]; then \
    uv sync --frozen; \
    else \
    uv sync --frozen --no-dev; \
    fi

# Copy app code
COPY ./app ./app

# Expose the FastAPI port
EXPOSE 8000

# The default command to run the application
# This will be overridden by the 'command' in your docker-compose.yml for debugging
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
