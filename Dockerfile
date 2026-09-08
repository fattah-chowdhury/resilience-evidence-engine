FROM python:3.12-slim
WORKDIR /app
COPY requirements-core.lock /app/
RUN python -m pip install --no-cache-dir -r requirements-core.lock
COPY pyproject.toml README.md LICENSE /app/
COPY src /app/src
RUN python -m pip install --no-cache-dir --no-deps /app && useradd --create-home ree
USER ree
WORKDIR /home/ree
ENTRYPOINT ["ree"]
CMD ["demo", "--output", "/home/ree/outputs"]
