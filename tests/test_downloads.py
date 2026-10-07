import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests
import rddownloader as rd


class Response:
    def __init__(self, chunks, status=200, headers=None):
        self.chunks = chunks
        self.status_code = status
        self.headers = headers or {}
        self.closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.closed = True

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))

    def iter_content(self, chunk_size):
        yield from self.chunks


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.job = self.new_job()

    def new_job(self):
        return rd.DownloadJob('test', '', 'magnet', 'magnet:test', self.folder.name)

    def download(self, job=None, name='file.bin'):
        return (job or self.job)._download_file(
            'test', 'https://example.invalid/file', name, 0, 8, time.time())

    def test_resume_preserves_bytes_and_uses_range(self):
        def chunks():
            yield b'abcd'
            self.job.pause()
            yield b'efgh'
        first = Response(chunks(), headers={'Content-Length': '8'})
        self.job.api.session.get = Mock(return_value=first)
        with self.assertRaises(rd._Paused):
            self.download()
        self.assertTrue(first.closed)
        self.assertEqual(Path(self.job._partial_path).read_bytes(), b'abcd')
        self.job.resume()
        second = Response([b'efgh'], 206, {'Content-Range': 'bytes 4-7/8', 'Content-Length': '4'})
        self.job.api.session.get.return_value = second
        self.assertEqual(self.download(), 8)
        self.assertEqual(self.job.api.session.get.call_args.kwargs['headers']['Range'], 'bytes=4-')
        self.assertEqual(Path(self.folder.name, 'file.bin').read_bytes(), b'abcdefgh')
        self.assertTrue(second.closed)

    def test_network_retry_resumes_partial(self):
        def chunks():
            yield b'abcd'
            raise requests.ConnectionError('connection lost')
        first = Response(chunks())
        self.job.api.session.get = Mock(return_value=first)
        with self.assertRaises(requests.ConnectionError):
            self.download()
        self.assertTrue(first.closed)
        self.job.api.session.get.return_value = Response(
            [b'efgh'], 206, {'Content-Range': 'bytes 4-7/8'})
        self.assertEqual(self.download(), 8)
        self.assertEqual(Path(self.folder.name, 'file.bin').read_bytes(), b'abcdefgh')

    def test_server_ignoring_range_restarts_without_duplicate_data(self):
        def chunks():
            yield b'abcd'
            raise requests.ConnectionError()
        self.job.api.session.get = Mock(return_value=Response(chunks()))
        with self.assertRaises(requests.ConnectionError):
            self.download()
        self.job.api.session.get.return_value = Response([b'abcdefgh'])
        self.assertEqual(self.download(), 8)
        self.assertEqual(Path(self.folder.name, 'file.bin').read_bytes(), b'abcdefgh')

    def test_invalid_range_does_not_append(self):
        fd = Path(self.folder.name, 'partial.part')
        fd.write_bytes(b'abcd')
        self.job._partial_path = str(fd)
        self.job.api.session.get = Mock(return_value=Response(
            [b'abcdefgh'], 206, {'Content-Range': 'bytes 0-7/8'}))
        with self.assertRaises(requests.RequestException):
            self.download()
        self.assertEqual(fd.read_bytes(), b'abcd')

    def test_completed_partial_handles_416(self):
        fd = Path(self.folder.name, 'partial.part')
        fd.write_bytes(b'abcdefgh')
        self.job._partial_path = str(fd)
        self.job.api.session.get = Mock(return_value=Response(
            [], 416, {'Content-Range': 'bytes */8'}))
        self.assertEqual(self.download(), 8)
        self.assertEqual(Path(self.folder.name, 'file.bin').read_bytes(), b'abcdefgh')

    def test_cancel_before_run_does_not_submit(self):
        self.job.api.add_magnet = Mock()
        self.job.cancel()
        self.job.run()
        self.job.api.add_magnet.assert_not_called()

    def test_cancel_last_file_does_not_signal_done(self):
        self.job.api.add_magnet = Mock(return_value='id')
        self.job.api.info = Mock(return_value={'status': 'downloaded', 'links': ['link']})
        self.job.api.unrestrict = Mock(return_value={
            'filename': 'file.bin', 'download': 'fake', 'filesize': 8})
        def chunks():
            yield b'abcd'
            self.job.cancel()
            yield b'efgh'
        response = Response(chunks())
        self.job.api.session.get = Mock(return_value=response)
        done = []
        self.job.signals.done.connect(lambda *args: done.append(args))
        self.job.run()
        self.assertFalse(done)
        self.assertFalse(Path(self.folder.name, 'file.bin').exists())
        self.assertFalse(list(Path(self.folder.name).glob('*.part')))
        self.assertTrue(response.closed)

    def test_same_name_concurrent_downloads_keep_all_contents(self):
        Path(self.folder.name, 'file.bin').write_bytes(b'original')
        barrier = threading.Barrier(2)
        errors = []
        def run(payload):
            try:
                job = self.new_job()
                def chunks():
                    barrier.wait(timeout=3)
                    yield payload
                job.api.session.get = Mock(return_value=Response(chunks()))
                self.download(job)
            except Exception as exc:
                errors.append(exc)
        threads = [threading.Thread(target=run, args=(data,)) for data in (b'AAAAAAAA', b'BBBBBBBB')]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertFalse(errors)
        self.assertEqual({p.read_bytes() for p in Path(self.folder.name).glob('*.bin')},
                         {b'original', b'AAAAAAAA', b'BBBBBBBB'})
        self.assertFalse(list(Path(self.folder.name).glob('*.part')))

    def test_filesystem_without_hardlinks_preserves_existing_file(self):
        Path(self.folder.name, 'file.bin').write_bytes(b'original')
        self.job.api.session.get = Mock(return_value=Response([b'abcdefgh']))
        with patch.object(rd.os, 'link', side_effect=OSError('unsupported')):
            self.download()
        self.assertEqual(Path(self.folder.name, 'file.bin').read_bytes(), b'original')
        self.assertEqual(Path(self.folder.name, 'file (1).bin').read_bytes(), b'abcdefgh')

    def test_incomplete_file_not_published(self):
        self.job.api.session.get = Mock(return_value=Response([b'abcd'], headers={'Content-Length': '8'}))
        with self.assertRaises(requests.RequestException):
            self.download()
        self.assertFalse(Path(self.folder.name, 'file.bin').exists())

    def test_magnet_display_name(self):
        self.assertEqual(rd.magnet_display_name(
            'magnet:?xt=urn:btih:ABCDEF0123456789XYZ&dn=Big+Buck+Bunny'), 'Big Buck Bunny')
        self.assertEqual(rd.magnet_display_name(
            'magnet:?xt=urn:btih:ABCDEF0123456789XYZ'), 'magnet:ABCDEF0123456789…')

    def test_human_duration(self):
        self.assertEqual(rd.human_duration(42), '42s')
        self.assertEqual(rd.human_duration(125), '2m 05s')
        self.assertEqual(rd.human_duration(3 * 3600 + 120), '3h 02m')


if __name__ == '__main__':
    unittest.main()
