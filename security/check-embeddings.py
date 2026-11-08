"""Run inside the candidate worker with network disabled; compare real MiniLM outputs."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import numpy as np
from model import LocalEmbeddings, MODEL_PATH, MODEL_NAME, MODEL_REVISION

baseline=json.loads(Path(sys.argv[1]).read_text())
old=np.asarray(baseline['vectors'],dtype=np.float64)
new=np.asarray(LocalEmbeddings().embed_documents(baseline['queries']),dtype=np.float64)
assert old.shape==new.shape==(5,384)
cosines=(old*new).sum(axis=1)/(np.linalg.norm(old,axis=1)*np.linalg.norm(new,axis=1))
maximum=float(np.abs(old-new).max())
assert maximum<0.00002 and float(cosines.min())>0.999999,(maximum,cosines.tolist())
with (Path(MODEL_PATH)/'model.safetensors').open('rb') as handle:
    weight_hash=hashlib.file_digest(handle,'sha256').hexdigest()
assert weight_hash == baseline['weight_sha256']
assert MODEL_NAME == baseline['model'] and MODEL_REVISION == baseline['revision']
print(json.dumps({'queries':len(new),'dimensions':384,'maximum_absolute_difference':maximum,
                  'minimum_cosine':float(cosines.min()),'model':MODEL_NAME,'revision':MODEL_REVISION,
                  'weight_sha256':weight_hash,'offline':True,
                  'versions':{name:importlib.metadata.version(name) for name in ('torch','sentence-transformers','transformers','langchain','langchain-core','kafka-python')}},indent=2))
