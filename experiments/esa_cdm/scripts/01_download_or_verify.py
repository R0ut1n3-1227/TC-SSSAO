from __future__ import annotations
import io
import shutil
import urllib.request
import zipfile
from pathlib import Path
from common import ARCHIVE, DATASET_URL, METADATA, RAW, ensure_dirs, save_json

def safe_extract_csvs(archive: Path) -> list[dict[str, object]]:
    extracted = []
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            if not info.is_dir() and Path(info.filename).name == 'train_data.zip':
                nested_bytes = zf.read(info)
                nested_archive = RAW / 'train_data.zip'
                nested_archive.write_bytes(nested_bytes)
                with zipfile.ZipFile(io.BytesIO(nested_bytes)) as nested:
                    member = nested.getinfo('train_data.csv')
                    target = RAW / member.filename
                    target.write_bytes(nested.read(member))
                    extracted.append({'archive_member': info.filename + '!/' + member.filename, 'file': target.name, 'bytes': target.stat().st_size})
                continue
            if info.is_dir() or not info.filename.lower().endswith(('.csv', '.txt', '.md')):
                continue
            name = Path(info.filename).name
            target = RAW / name
            with zf.open(info) as source, target.open('wb') as sink:
                shutil.copyfileobj(source, sink)
            extracted.append({'archive_member': info.filename, 'file': name, 'bytes': target.stat().st_size})
    return extracted

def main() -> None:
    ensure_dirs()
    if not ARCHIVE.exists():
        print(f'Downloading official Zenodo archive to {ARCHIVE}')
        urllib.request.urlretrieve(DATASET_URL, ARCHIVE)
    extracted = safe_extract_csvs(ARCHIVE)
    result = {'status': 'PASS', 'source_url': DATASET_URL, 'archive': ARCHIVE.name, 'archive_bytes': ARCHIVE.stat().st_size, 'extracted_files': extracted}
    save_json(METADATA / 'download_verification.json', result)
    print(f'PASS archive extracted={len(extracted)}')
if __name__ == '__main__':
    main()
