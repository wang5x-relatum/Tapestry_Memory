"""Isolated fixtures for the documented Markdown subset, not full Markdown."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'check_docs.py'
SPEC = importlib.util.spec_from_file_location('check_docs', SCRIPT)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class DocsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        for name, peer, title in [('README.md', 'README.zh.md', 'Guide'), ('README.zh.md', 'README.md', '指南 🌙')]:
            self.put(name, f'# {title}\n\n[Language]({peer})\n\n## {title}\n\n- {title}\n1. {title}\n\n| A | B |\n| --- | --- |\n| x | y |\n\n```python\nprint("🌙")\n```\n')
        self.assertEqual(self.check(record=['README.md'], reviewed=True), [])

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')

    def check(self, **kwargs):
        return checker.validate(self.root, **kwargs)

    def mutate(self, old, new):
        path = self.root / 'README.zh.md'
        self.put(path.name, path.read_text(encoding='utf-8').replace(old, new))

    def test_success_unicode_and_blob(self):
        self.assertEqual(self.check(), [])
        raw = (self.root / 'README.zh.md').read_bytes()
        expected = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
        self.assertIn('README.zh.md: ' + expected, (self.root / 'README.i18n.yaml').read_text())

    def test_one_sided_change_and_explicit_record(self):
        self.mutate('指南', '手册')
        self.assertTrue(self.check())
        before = (self.root / 'README.i18n.yaml').read_bytes()
        for kwargs in ({'record': ['README.md']}, {'record': ['README.zh.md'], 'reviewed': True}, {'record': ['../outside.md'], 'reviewed': True}):
            self.assertTrue(self.check(**kwargs))
            self.assertEqual((self.root / 'README.i18n.yaml').read_bytes(), before)
        self.assertEqual(self.check(record=['README.md'], reviewed=True), [])
        self.assertEqual(self.check(), [])

    def test_missing_pair(self):
        for name in ('README.md', 'README.zh.md', 'README.i18n.yaml'):
            with self.subTest(name=name):
                path = self.root / name
                data = path.read_bytes()
                path.unlink()
                self.assertTrue(self.check())
                path.write_bytes(data)

    def test_orphans_and_exclusions(self):
        for name in ('orphan.zh.md', 'orphan.i18n.yaml', 'orphan.md'):
            self.put('docs/nested/' + name, '# Orphan\n')
            self.assertTrue(self.check())
            (self.root / 'docs/nested' / name).unlink()
        for name in ('AGENTS.md', 'CLAUDE.md', 'terminology.md'):
            self.put('docs/' + name, 'Excluded')
        self.assertEqual(self.check(), [])

    def test_structure_failures_do_not_write(self):
        original = (self.root / 'README.zh.md').read_text()
        before = (self.root / 'README.i18n.yaml').read_bytes()
        for old, new in (('[Language](README.md)', '[Language](README.zh.md)'), ('print("🌙")', 'print("x")'), ('## 指南', '#### 指南'), ('- 指南', '2. 指南'), ('| x | y |', '| x | y | z |'), ('| x | y |', '| x | y |\n| z | q |'), ('## 指南', '[missing](missing.md)\n## 指南'), ('## 指南', '[escape](../outside.md)\n## 指南')):
            with self.subTest(new=new):
                self.put('README.zh.md', original.replace(old, new))
                self.assertTrue(self.check(record=['README.md'], reviewed=True))
                self.assertEqual((self.root / 'README.i18n.yaml').read_bytes(), before)

    def test_nested_links_and_no_partial_record(self):
        for name, peer in [('guide.md', 'guide.zh.md'), ('guide.zh.md', 'guide.md')]:
            self.put('docs/' + name, f'# Guide\n[Language]({peer})\n')
        self.assertEqual(self.check(record=['docs/guide.md'], reviewed=True), [])
        for name, target in [('README.md', 'guide.md'), ('README.zh.md', 'guide.zh.md')]:
            path = self.root / name
            self.put(name, path.read_text() + f'\n[Guide](docs/{target})\n')
        self.assertEqual(self.check(record=['README.md'], reviewed=True), [])
        self.mutate('指南', '手册')
        (self.root / 'docs/guide.i18n.yaml').unlink()
        before = (self.root / 'README.i18n.yaml').read_bytes()
        self.assertTrue(self.check(record=['README.md'], reviewed=True))
        self.assertEqual((self.root / 'README.i18n.yaml').read_bytes(), before)

    def test_manifest_format_and_read_only(self):
        manifest = self.root / 'README.i18n.yaml'
        original = manifest.read_text()
        for text in (original.replace(': ', ': deadbeef # ', 1), original.splitlines()[0] + '\n', original + original):
            self.put(manifest.name, text)
            self.assertTrue(self.check())
            self.assertEqual(manifest.read_text(), text)

    def test_symlink_escape_refuses_record(self):
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other) / 'hashes.yaml'
            outside.write_text('untouched')
            manifest = self.root / 'README.i18n.yaml'
            manifest.unlink()
            manifest.symlink_to(outside)
            self.assertTrue(self.check(record=['README.md'], reviewed=True))
            self.assertEqual(outside.read_text(), 'untouched')

    def test_cli_from_other_cwd(self):
        self.put('scripts/check_docs.py', SCRIPT.read_text())
        result = subprocess.run([sys.executable, str(self.root / 'scripts/check_docs.py')], cwd='/', capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run([sys.executable, str(self.root / 'scripts/check_docs.py'), '--record', 'README.md'], cwd='/', capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)


if __name__ == '__main__':
    unittest.main()
