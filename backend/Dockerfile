FROM python:3.9-slim-bookworm

ARG DB_TYPE

# Only DB_TYPE=mssql needs a system package: ODBC Driver 18 (required by pyodbc)
# from Microsoft's apt repo. PostgreSQL and MySQL use pure-wheel drivers.
RUN set -e; \
    if [ "$DB_TYPE" = "mssql" ]; then \
        apt-get update; \
        apt-get install -y --no-install-recommends curl gnupg ca-certificates; \
        curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg; \
        curl -fsSL https://packages.microsoft.com/config/debian/12/prod.list -o /etc/apt/sources.list.d/mssql-release.list; \
        apt-get update; \
        ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 unixodbc-dev; \
        apt-get purge -y curl gnupg; \
        rm -rf /var/lib/apt/lists/*; \
    fi

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project
COPY . .
RUN uv sync --frozen

EXPOSE 8000
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
