#!/usr/bin/env python3
"""Check README and docs English/.zh.md/.i18n.yaml triples (stdlib only).

Subset: ATX headings, pipe tables with separator rows, bullet/ordered lists,
backtick/tilde fences, and inline links/images with whitespace-free destinations.
No full Markdown parsing or semantic translation checks; reference/HTML links,
Setext headings, inline-code masking and anchor validation are not supported.
Local link paths (not fragments/queries) must exist, stay inside the repository,
and match in order after .zh.md normalization. The first nonempty line after
H1 must link to the other language; labels may differ. YAML is a flat mapping
of both Markdown basenames to full Git blob SHA-1s, not a recoverable snapshot.
--record PATH [PATH ...] --reviewed records only explicitly reviewed English
paths (relative to ROOT or absolute); any validation error prevents all writes.
"""
import argparse
import hashlib
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
LINK = re.compile(r'!?\[[^\]\n]*\]\(([^\s)]+)\)')
EXCLUDED = {'AGENTS', 'CLAUDE', 'terminology'}


def blob(path):
    data = path.read_bytes()
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def inside(path, root):
    if not path.resolve().is_relative_to(root):
        raise ValueError(f'path outside repository: {path}')
    return path


def local_links(line, path, root):
    targets = []
    for destination in LINK.findall(line):
        url = urlsplit(destination)
        if url.scheme or url.netloc or not url.path:
            continue
        relative = Path(unquote(url.path))
        if relative.is_absolute():
            raise ValueError(f'absolute local link: {destination}')
        target = inside(path.parent / relative, root).resolve()
        if not target.exists():
            raise ValueError(f'missing local link: {destination}')
        targets.append(target)
    return targets


def cells(line):
    return re.split(r'(?<!\\)\|', line.strip().strip('|'))


def structure(path, peer, root):
    lines = path.read_text(encoding='utf-8').splitlines()
    result, headings, fence, body, table = [], [], None, [], None
    for i, line in enumerate(lines):
        if fence:
            if re.fullmatch(r' {0,3}' + re.escape(fence[0]) + '{' + str(fence[1]) + r',}\s*', line):
                result.append(('code', fence[2], tuple(body)))
                fence, body = None, []
            else:
                body.append(line)
            continue
        opening = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if opening:
            mark, info = opening.groups()
            fence = (mark[0], len(mark), info.strip())
            table = None
            continue
        heading = re.match(r'^ {0,3}(#{1,6})\s+\S', line)
        if heading:
            level = len(heading[1])
            if level > (headings[-1] if headings else 0) + 1 or (level == 1 and headings):
                raise ValueError('invalid heading hierarchy')
            headings.append(level)
            result.append(('heading', level))
            if level == 1:
                switch = next((s for s in lines[i + 1:] if s.strip()), '')
                if peer.resolve() not in local_links(switch, path, root):
                    raise ValueError('H1 must be followed by a link to the other language')
        item = re.match(r'^( *)([-+*]|\d+[.)])\s+', line)
        if item:
            result.append(('list', len(item[1]), 'bullet' if item[2] in '-+*' else 'ordered'))
        separator = i + 1 < len(lines) and '|' in lines[i + 1] and all(
            re.fullmatch(r'\s*:?-{3,}:?\s*', c) for c in cells(lines[i + 1]))
        if table is None and '|' in line and separator:
            table = len(cells(line))
            result.append(('table', table))
        if table is not None:
            if '|' not in line:
                table = None
            else:
                width = len(cells(line))
                if width != table:
                    raise ValueError('inconsistent table columns')
                result.append(('row', width))
        for target in local_links(line, path, root):
            result.append(('link', re.sub(r'\.zh\.md$', '.md', target.relative_to(root).as_posix())))
    if fence or not headings:
        raise ValueError('unclosed code fence or missing H1')
    return result


def validate(root=ROOT, record=(), reviewed=False):
    """Return error strings; writes occur only after the entire check succeeds."""
    root = Path(root).resolve()
    errors, pending, selected = [], [], set()
    try:
        if record and not reviewed:
            raise ValueError('--record requires --reviewed (caller confirms human review)')
        for entry in record:
            selected.add(inside(root / entry, root).resolve())
        docs = inside(root / 'docs', root)
        candidates = {root / name for name in ('README.md', 'README.zh.md', 'README.i18n.yaml')}
        candidates.update(docs.rglob('*.md'))
        candidates.update(docs.rglob('*.i18n.yaml'))
        bases = set()
        for path in candidates:
            stem = re.sub(r'(\.zh\.md|\.i18n\.yaml|\.md)$', '', path.name)
            if stem not in EXCLUDED:
                inside(path, root)
                bases.add(path.with_name(stem + '.md'))
        if selected - bases:
            raise ValueError('--record accepts only in-scope English Markdown paths')
        for english in sorted(bases):
            try:
                chinese = english.with_name(english.stem + '.zh.md')
                manifest = english.with_suffix('.i18n.yaml')
                for path in (english, chinese, manifest):
                    inside(path, root)
                    if not path.is_file() and not (path == manifest and english in selected):
                        raise ValueError(f'missing pair file: {path.name}')
                if structure(english, chinese, root) != structure(chinese, english, root):
                    raise ValueError('Markdown structure/code/local-link mismatch')
                expected = {p.name: blob(p) for p in (english, chinese)}
                if english in selected:
                    pending.append((manifest, ''.join(f'{k}: {v}\n' for k, v in expected.items())))
                else:
                    rows = [s for s in manifest.read_text(encoding='utf-8').splitlines() if s.strip() and not s.lstrip().startswith('#')]
                    matches = [re.fullmatch(r'([^:]+): ([0-9a-f]{40})', s) for s in rows]
                    if len(matches) != 2 or not all(matches) or dict(m.groups() for m in matches) != expected:
                        raise ValueError('manifest must contain both basenames and current full Git blob hashes')
            except (OSError, ValueError) as exc:
                errors.append(f'{english.relative_to(root)}: {exc}')
        if not errors:
            for path, text in pending:
                path.write_text(text, encoding='utf-8')
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--record', nargs='+', metavar='ENGLISH_PATH')
    parser.add_argument('--reviewed', action='store_true')
    args = parser.parse_args()
    errors = validate(record=args.record or (), reviewed=args.reviewed)
    print('\n'.join(errors) if errors else 'Documentation subset checks passed.')
    return bool(errors)


if __name__ == '__main__':
    raise SystemExit(main())
