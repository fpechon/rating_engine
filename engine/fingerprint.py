import hashlib
from pathlib import Path


def tariff_hash(tariff_path, table_paths):
    h = hashlib.sha256()

    h.update(Path(tariff_path).read_bytes())

    for path in sorted(table_paths):
        h.update(Path(path).read_bytes())

    return h.hexdigest()
