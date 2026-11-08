"""Export synthetic-query vectors from the preserved baseline image, offline."""
import hashlib
import json
from pathlib import Path
from model import LocalEmbeddings, MODEL_PATH, MODEL_NAME, MODEL_REVISION

queries = [
    'PostgreSQL too many clients connection pool exhausted SQLSTATE 08006',
    'HTTP 500 exceptions after deployment',
    'Memory exhausted container OOM killed',
    'Kafka consumer lag growing offsets',
    'Authentication JWT expired unauthorized',
]
with (Path(MODEL_PATH) / 'model.safetensors').open('rb') as stream:
    weight_hash = hashlib.file_digest(stream, 'sha256').hexdigest()
print(json.dumps({'queries': queries, 'vectors': LocalEmbeddings().embed_documents(queries),
                  'model': MODEL_NAME, 'revision': MODEL_REVISION, 'weight_sha256': weight_hash}))
