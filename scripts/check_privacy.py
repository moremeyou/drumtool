#!/usr/bin/env python3
"""Check staged blobs or all local Git history without echoing matched values.

This is a small project guard, not a complete secret/PII detection system.
Only the Python standard library and Git are required.
"""
import argparse
import ipaddress
import re
import subprocess
from pathlib import PurePosixPath

RULES = {
    'personal filesystem path': re.compile(r'(?:/(?:Users|home)/[^/\s]+|[A-Za-z]:[\\/]Users[\\/][^\\/\s]+)'),
    'private key': re.compile(r'-----BEGIN (?:[A-Z]+ )*PRIVATE KEY-----'),
    'credential-like token': re.compile(r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16}|sk-[A-Za-z0-9_-]{20,}|xox[baprs]-[A-Za-z0-9-]{10,})\b'),
    'credential in URL': re.compile(r'\b[a-z]+://[^\s/@:]+:[^\s/@]+@', re.I),
    'MAC address': re.compile(r'(?<![\w:])(?:[0-9a-f]{2}:){5}[0-9a-f]{2}(?![\w:])', re.I),
    'local network hostname': re.compile(r'\b[a-z0-9][a-z0-9-]*\.(?:local|lan|internal)\b', re.I),
    'assigned secret': re.compile(r'''(?i)\b(?:password|api[_-]?key|access[_-]?token|client[_-]?secret)\b["']?\s*[:=]\s*["'][^"'\s]{8,}["']'''),
}
EMAIL = re.compile(r'\b[A-Za-z0-9.!#$%&\x27*+/=?^_`{|}~-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)\b')
IPV4 = re.compile(r'(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w.])')
IPV6 = re.compile(r'(?<![\w:])(?:[0-9a-f]{0,4}:){2,}[0-9a-f]{0,4}(?![\w:])', re.I)
SAFE_EMAIL_DOMAINS = {'example.com', 'example.org', 'example.net', 'example.invalid', 'users.noreply.github.com'}
PRIVATE_PARTS = {'.env', '.aws', '.ssh', '.venv', 'venv', 'node_modules', 'dist', 'build',
                 'local', 'private', 'secrets', 'credentials', 'captures', 'recordings',
                 'screenshots', 'logs', '.codex', '.idea', '.vscode', '__pycache__'}
PRIVATE_SUFFIXES = {'.pem', '.key', '.p12', '.pfx', '.log', '.mid', '.midi', '.pcap', '.pcapng',
                    '.sqlite', '.sqlite3', '.db', '.har', '.dump', '.bak', '.pyc', '.tsbuildinfo'}


def git(*args):
    return subprocess.check_output(['git', *args], stderr=subprocess.PIPE)


def findings(text):
    result = set()
    for label, pattern in RULES.items():
        if pattern.search(text):
            result.add(label)
    for match in EMAIL.finditer(text):
        domain = match.group(1).lower()
        if domain not in SAFE_EMAIL_DOMAINS and not domain.endswith('.invalid'):
            result.add('personal or non-example email')
    for pattern in (IPV4, IPV6):
        for match in pattern.finditer(text):
            try:
                address = ipaddress.ip_address(match.group())
            except ValueError:
                continue
            if not address.is_loopback:
                result.add('non-loopback IP address')
    return sorted(result)


def private_path(path):
    p = PurePosixPath(path)
    return (any(part in PRIVATE_PARTS for part in p.parts)
            or (p.name.startswith('.env.') and p.name != '.env.example')
            or p.name in {'.npmrc', '.pypirc', '.netrc', '.DS_Store', 'Thumbs.db'}
            or p.suffix in PRIVATE_SUFFIXES or '.local.' in p.name or p.name.endswith('.local'))


def check_blob(path, content):
    issues = []
    if private_path(path):
        issues.append('private or generated file is tracked')
    issues.extend(findings(path))
    try:
        text = content.decode('utf-8')
    except UnicodeDecodeError:
        issues.append('binary artifact requires explicit privacy review; keep it untracked')
    else:
        issues.extend(findings(text))
    return sorted(set(issues))


def scan(history=False):
    failures = 0
    seen = set()
    revisions = git('rev-list', '--all').decode().splitlines() if history else [None]
    for revision in revisions:
        if revision:
            metadata = git('show', '-s', '--format=%an%n%ae%n%cn%n%ce%n%B', revision).decode()
            for issue in findings(metadata):
                print(f'{revision[:12]}: commit metadata: {issue}')
                failures += 1
            entries = git('ls-tree', '-r', '-z', revision).split(b'\0')
        else:
            entries = git('ls-files', '--stage', '-z').split(b'\0')
        for entry in filter(None, entries):
            info, raw_path = entry.split(b'\t', 1)
            fields = info.decode().split()
            object_id = fields[2] if revision else fields[1]
            path = raw_path.decode('utf-8')
            if (path, object_id) in seen:
                continue
            seen.add((path, object_id))
            if fields[0] in {'120000', '160000'}:
                issues = ['symlinks/submodules require review; not supported by this guard']
            else:
                issues = check_blob(path, git('cat-file', 'blob', object_id))
            for issue in issues:
                # Hide suspicious filenames as well as values.
                label = '[redacted path]' if findings(path) else path
                print(f'{label}: {issue}')
                failures += 1
    print(f'Privacy check: {len(seen)} file versions checked; {failures} finding(s).')
    return bool(failures)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history', action='store_true', help='scan all local refs and commit metadata')
    args = parser.parse_args()
    try:
        raise SystemExit(scan(args.history))
    except (subprocess.CalledProcessError, UnicodeError, ValueError):
        print('Privacy check could not inspect Git content; refusing to pass.')
        raise SystemExit(2)
