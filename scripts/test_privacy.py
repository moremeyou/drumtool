import unittest
import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
from check_privacy import check_blob, findings, private_path, scan


class PrivacyTests(unittest.TestCase):
    def test_portable_defaults(self):
        self.assertEqual(findings('http://localhost:5173 http://127.0.0.1:8000 [::1] contributor@example.invalid'), [])

    def test_sensitive_examples(self):
        # Synthetic test values assembled to keep the repository itself clean.
        values = [
            '/Us' + 'ers/sample/project',
            'sample@' + 'mail.test',
            '192.' + '168.5.6',
            '8.' + '8.8.8',
            ':'.join(['fd00', '', '1234']),
            'aa:bb:' + 'cc:dd:ee:ff',
            'studio' + '.local',
            'ghp_' + 'x' * 36,
            'https://sample:' + 'credential@' + 'host.test',
            '-----BEGIN RSA ' + 'PRIVATE KEY-----',
            'password = ' + '"not-a-real-secret"',
        ]
        for value in values:
            with self.subTest(kind=values.index(value)):
                self.assertTrue(findings(value))

    def test_private_artifacts(self):
        for path in ['.env', '.env.production', 'backend/.env', 'local/settings.json',
                     'capture.mid', 'trace.har', 'auth.pem', 'frontend/.npmrc']:
            self.assertTrue(private_path(path))
        self.assertFalse(private_path('.env.example'))
        self.assertFalse(private_path('backend/app/midi/mapping.json'))

    def test_binary_not_silently_skipped(self):
        self.assertTrue(check_blob('image.png', bytes([255, 254])))


class GitSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.previous = Path.cwd()
        os.chdir(self.directory.name)
        self.git('init', '-q')

    def tearDown(self):
        os.chdir(self.previous)
        self.directory.cleanup()

    def git(self, *args):
        return subprocess.run(['git', *args], check=True, capture_output=True)

    def scan_quietly(self, history=False):
        with contextlib.redirect_stdout(io.StringIO()) as report:
            result = scan(history)
        return result, report.getvalue()

    def test_staged_content_is_checked_even_if_worktree_is_cleaned(self):
        sensitive = 'sample@' + 'mail.test'
        Path('fixture.txt').write_text(sensitive)
        self.git('add', 'fixture.txt')
        Path('fixture.txt').write_text('clean working copy')
        failed, report = self.scan_quietly()
        self.assertTrue(failed)
        self.assertNotIn(sensitive, report)
        self.git('add', 'fixture.txt')
        self.assertFalse(self.scan_quietly()[0])

    def test_history_checks_previous_blobs_and_email_metadata(self):
        self.git('config', 'user.name', 'Test contributor')
        self.git('config', 'user.email', 'sample@' + 'mail.test')
        Path('fixture.txt').write_text('192.' + '168.5.6')
        self.git('-c', 'core.hooksPath=/dev/null', 'add', 'fixture.txt')
        self.git('-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Synthetic fixture')
        self.git('config', 'user.email', 'contributor@example.invalid')
        Path('fixture.txt').write_text('clean')
        self.git('add', 'fixture.txt')
        self.git('-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', 'commit', '-qm', 'Clean fixture')
        failed, report = self.scan_quietly(history=True)
        self.assertTrue(failed)
        self.assertIn('commit metadata', report)
        self.assertIn('non-loopback IP address', report)


if __name__ == '__main__':
    unittest.main()
