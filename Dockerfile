# -------------------------------
# Stage 1: Python base + pip deps
# -------------------------------
FROM public.ecr.aws/docker/library/python:3.14.5-slim AS pydeps

RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libmariadb-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Leverage Docker layer caching for Python deps
COPY ./pyproject.toml ./README.md /app/
COPY ./src/ /app/src/
RUN pip install .

# -------------------------------
# Stage 2: Node base + npm deps
# (use bookworm to align with python:*-slim base)
# -------------------------------
FROM public.ecr.aws/docker/library/node:22.14.0-bookworm-slim AS nodedeps

WORKDIR /app

# Leverage Docker layer caching for Node deps
COPY ./src/package*.json /app/
RUN npm ci --omit=dev

# -------------------------------
# Final image: Python runtime
# -------------------------------
FROM pydeps AS runtime

WORKDIR /app

# Copy application source
COPY ./src/ /app/

# Bring in node_modules produced in Node stage
COPY --from=nodedeps /app/node_modules /app/node_modules

RUN sed -i 's/\r$//' /app/entrypoint.sh && chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
