"""Fetch only the hash-pinned official amd64 Ollama executable layer, not GPU libraries."""
import hashlib
import io
import json
from pathlib import Path
import tarfile
import urllib.request

REPOSITORY = 'ollama/ollama'
# Official 0.6.8 linux/amd64 executable layer (11,418,507 compressed bytes).
DIGEST = '2ace2f9dde9e03c2b920e6f482ad34fd7dc7fb992b8a75cc0343945f36d2e9f7'
MAX_BYTES = 16_000_000

def main() -> None:
    url = 'https://auth.docker.io/token?service=registry.docker.io&scope=repository:' + REPOSITORY + ':pull'
    with urllib.request.urlopen(url, timeout=30) as response:
        token = json.load(response)['token']
    request = urllib.request.Request('https://registry-1.docker.io/v2/' + REPOSITORY + '/blobs/sha256:' + DIGEST,
                                     headers={'Authorization': 'Bearer ' + token})
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES or hashlib.sha256(data).hexdigest() != DIGEST:
        raise RuntimeError('Ollama runtime layer exceeded limit or failed SHA-256 verification')
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        member = archive.getmember('usr/bin/ollama')
        if not member.isfile() or member.size > 40_000_000:
            raise RuntimeError('Unexpected executable layer')
        target = Path('/out/ollama')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(archive.extractfile(member).read())
        target.chmod(0o755)
    print('Verified official Ollama 0.6.8 CPU executable layer:', len(data), 'bytes')

if __name__ == '__main__':
    main()
