"""ZIP64 transport package: existing IoStore content is already compressed."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument('--release', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = args.release.resolve()
output = args.output.resolve()
output.parent.mkdir(parents=True, exist_ok=True)
temporary = output.with_suffix(output.suffix + '.partial')
manifest = json.loads((root / 'checksums.json').read_text(encoding='utf-8'))
for name, entry in manifest.items():
    path = root / name
    if not path.resolve().is_relative_to(root):
        raise ValueError('Invalid release manifest path')
    with path.open('rb') as source:
        if path.stat().st_size != entry['bytes'] or hashlib.file_digest(source, 'sha256').hexdigest() != entry['sha256']:
            raise ValueError(f'Release integrity check failed: {name}')
with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
    for path in sorted(root.rglob('*')):
        if path.is_file():
            archive.write(path, 'WISEYE/' + path.relative_to(root).as_posix())
with zipfile.ZipFile(temporary) as archive:
    bad = archive.testzip()
    if bad:
        raise ValueError(f'Archive CRC verification failed: {bad}')
with temporary.open('rb') as source:
    digest = hashlib.file_digest(source, 'sha256').hexdigest()
temporary.rename(output)
output.with_suffix(output.suffix + '.sha256').write_text(digest + '  ' + output.name + '\n', encoding='ascii')
report = {'path': str(output), 'bytes': output.stat().st_size, 'sha256': digest, 'release_id': json.loads((root / 'release.json').read_text())['release_id'], 'zip_crc_verified': True}
output.with_suffix(output.suffix + '.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report, indent=2))
