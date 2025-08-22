FROM python:3.12-slim

# Install Poetry
RUN pip install poetry

# Set working dir
WORKDIR /app

# Copy pyproject + lock first (better caching)
COPY pyproject.toml poetry.lock* /app/

# Install deps
RUN poetry install --no-root --only main

# Copy app code
COPY ./app ./app

# Expose FastAPI port
EXPOSE 8000

# Run via Poetry
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
