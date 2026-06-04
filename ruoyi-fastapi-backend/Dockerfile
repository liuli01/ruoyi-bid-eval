FROM python:3.12-slim
WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install pymysql（用于启动时数据库初始化）
RUN pip install pymysql --no-cache-dir

# Copy dependency files
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy source and install project
COPY . .
RUN uv sync --frozen --no-dev

EXPOSE 9100

# 使用启动脚本（自动初始化数据库 + 启动应用）
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
ENTRYPOINT ["/docker-entrypoint.sh"]
