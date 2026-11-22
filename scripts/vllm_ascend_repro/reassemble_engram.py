"""Pinned two-target Engram assembly. Dry-run never reads weight contents."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat

try:
    from .download_assets import MARKER, OWNER, REVISION, RESERVE, DEFAULT_MANIFEST, inventory
except ImportError:
    from download_assets import MARKER, OWNER, REVISION, RESERVE, DEFAULT_MANIFEST, inventory

FINAL = ('51d28f161232e3bf600b92ef4e3c38ceb9164b801bd456503bb1a29da496ea9f',
         'bee6e08838c75d40c4b1f5f8d7e4716aba34f90c03c17e77ad406e36188cccaa')


def plan(manifest=DEFAULT_MANIFEST, revision=REVISION):
    if revision != REVISION:
        raise ValueError('unpinned revision')
    # The checked-in snapshot is the trust anchor, not per-file commit IDs.
    safe(Path(manifest).absolute())
    trusted = {r['Path']: r for r in inventory(DEFAULT_MANIFEST)}
    supplied = {r['Path']: r for r in inventory(manifest)}
    hashes = dict(line.split()[::-1] for line in
                  (DEFAULT_MANIFEST.parent / 'metadata/engram_int8/PARTS.sha256').read_text().splitlines()
                  if line and not line.startswith('#'))
    groups = []
    for layer, final in zip((1, 14), FINAL):
        target = f'engram_int8/layers_{layer}_engram_embed.weight.safetensors'
        rows = []
        for i in range(6):
            name = f'{target}.part-{i:02d}-of-06'
            row = supplied.get(name)
            if row != trusted[name] or row['Sha256'] != hashes[Path(name).name]:
                raise ValueError('manifest mismatch')
            rows.append(row)
        groups.append((target, final, rows))
    return groups


def safe(path):
    if '..' in path.parts:
        raise ValueError('path traversal')
    for p in (path, *path.parents):
        if p.is_symlink():
            raise ValueError('symlink forbidden')


def scan(path, output=None, combined=None):
    safe(path)
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as source:
        if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
            raise ValueError('not regular file')
        h, size = hashlib.sha256(), 0
        for data in iter(lambda: source.read(1024 * 1024), b''):
            h.update(data)
            size += len(data)
            if output is not None:
                output.write(data)
                combined.update(data)
        return size, h.hexdigest()


def run(root, groups, execute=False):
    safe(Path(root))
    root = Path(root).absolute()
    safe(root)
    safe(root / MARKER)
    if execute and (not root.is_dir() or json.loads((root / MARKER).read_text()) != OWNER):
        raise ValueError('owner mismatch')
    pending, report = [], []
    for target, expected, rows in groups:
        paths = [target, target + '.part'] + [r['Path'] for r in rows]
        for name in paths:
            if Path(name).is_absolute() or '..' in Path(name).parts:
                raise ValueError('path escape')
            safe(root / name)
        size = sum(r['Size'] for r in rows)
        entry = dict(path=target, sha256=expected, bytes=size, status='planned')
        report.append(entry)
        if (root / (target + '.part')).exists():
            raise FileExistsError('retained part')
        if (root / target).exists():
            if scan(root / target) != (size, expected):
                raise ValueError('existing target mismatch')
            entry['status'] = 'verified_existing'
        else:
            pending.append((target, expected, rows, entry))
    if not execute:
        return report
    remaining = sum(e['bytes'] for _, _, _, e in pending)
    for target, expected, rows, entry in pending:
        space = os.statvfs(root)
        if space.f_bavail * space.f_frsize < remaining + RESERVE:
            raise ValueError('insufficient space')
        for row in rows:
            if scan(root / row['Path']) != (row['Size'], row['Sha256']):
                raise ValueError('input mismatch')
        part = root / (target + '.part')
        safe(part)
        h, count = hashlib.sha256(), 0
        with part.open('xb') as out:
            for row in rows:
                size, digest = scan(root / row['Path'], out, h)
                if (size, digest) != (row['Size'], row['Sha256']):
                    raise ValueError('input changed')
                count += size
            if (count, h.hexdigest()) != (entry['bytes'], expected):
                raise ValueError('final mismatch')
            out.flush()
            os.fsync(out.fileno())
        safe(root / target)
        os.link(part, root / target)
        part.unlink()
        remaining -= count
        entry['status'] = 'complete'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dest', required=True)
    parser.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument('--revision', default=REVISION)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(run(args.dest, plan(args.manifest, args.revision), args.execute)))
    except (OSError, ValueError, KeyboardInterrupt):
        print(json.dumps({'status': 'failed', 'note': 'files retained; manual review required'}))
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
