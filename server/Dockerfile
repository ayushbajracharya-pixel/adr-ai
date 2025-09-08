FROM python:3.13-slim

# Install Poetry
RUN pip install poetry

# Set working dir
WORKDIR /app

# Copy pyproject + lock first (better caching)
COPY pyproject.toml poetry.lock* /app/

# Install dependencies and debugpy
RUN poetry install --no-root --only main && \
    poetry add debugpy

# Copy app code
COPY ./app ./app

# Expose the FastAPI port
EXPOSE 8000

# The default command to run the application
# This will be overridden by the 'command' in your docker-compose.yml for debugging
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
