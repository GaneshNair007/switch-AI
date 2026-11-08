"""Run on the VPS: consistent SQLite backup, with an optional restore check."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
import sqlite3
import os


def backup(source,destination):
    if not source.is_file():raise ValueError('Source database missing')
    destination.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if destination.exists():raise ValueError('Refusing to overwrite an existing backup')
    with sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(destination) as dst:
        src.backup(dst)
        if dst.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise RuntimeError('Backup integrity check failed')
    os.chmod(destination,0o600)
    return destination


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=Path('/opt/shipcourt/state/shipcourt.sqlite3'))
    p.add_argument('--directory',type=Path,default=Path('/opt/shipcourt/backups'))
    a=p.parse_args();path=backup(a.source,a.directory/('shipcourt-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.sqlite3'))
    print('Consistent application backup written:',path)
