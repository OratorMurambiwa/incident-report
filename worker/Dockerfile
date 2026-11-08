FROM python:3.12.16-slim-trixie AS dependencies
# Same Debian release, refreshed security packages before installing pinned CPU dependencies.
RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*
WORKDIR /app
ENV HF_HUB_DISABLE_TELEMETRY=1 HF_HUB_DISABLE_XET=1 DO_NOT_TRACK=1 \
    TOKENIZERS_PARALLELISM=false OMP_NUM_THREADS=2 \
    LANGCHAIN_TRACING_V2=false LANGSMITH_TRACING=false
COPY requirements.txt .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.10.0+cpu
COPY requirements.lock .
RUN pip install --no-cache-dir -r requirements.txt -c requirements.lock && pip check
COPY model.py download_model.py ./
RUN python download_model.py
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
RUN python -c "from model import LocalEmbeddings; assert len(LocalEmbeddings().embed_query('local embedding check')) == 384"

FROM dependencies AS test
RUN pip install --no-cache-dir pytest==8.4.1
COPY *.py ./
COPY tests ./tests
RUN python -m pytest -q

FROM dependencies AS runtime
RUN useradd --system --create-home worker
COPY --from=test /app/*.py /app/
USER worker
EXPOSE 8001
CMD ["python", "-u", "main.py"]
