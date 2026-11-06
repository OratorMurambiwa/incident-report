"""Download a bounded, SHA-256 pinned upstream CPU library source archive."""
import hashlib
from pathlib import Path
import urllib.request

URL = 'https://codeload.github.com/ollama/ollama/tar.gz/refs/tags/v0.6.8'
SHA256 = '46e3953373be41fae1699eaca97eb0e5f35b9a83d9652f38901938c1a988634d'
with urllib.request.urlopen(URL, timeout=60) as response:
    data = response.read(12_000_001)
if len(data) > 12_000_000 or hashlib.sha256(data).hexdigest() != SHA256:
    raise RuntimeError('Ollama CPU source exceeded limit or failed SHA-256 verification')
Path('/out/source.tar.gz').write_bytes(data)
print('Verified Ollama CPU source:', len(data), 'bytes')
