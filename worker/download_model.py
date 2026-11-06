"""Build-time download of a fixed, public model revision, not an inference service."""
from huggingface_hub import snapshot_download
from model import MODEL_NAME, MODEL_PATH, MODEL_REVISION

snapshot_download(repo_id=MODEL_NAME, revision=MODEL_REVISION, local_dir=MODEL_PATH,
                  allow_patterns=["*.json", "*.txt", "model.safetensors", "1_Pooling/*"])
