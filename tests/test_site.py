from functools import partial
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
import json
import re

from tools.serve import Handler
from tools.validate import validate


class QuietHandler(Handler):
    def log_message(self, *args):
        pass


class PreviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = TemporaryDirectory()
        root = Path(cls.temp.name)
        (root / "index.html").write_text("<h1>IDP</h1>", encoding="utf-8")
        (root / "sample.mp4").write_bytes(b"0123456789")
        (root / "empty.mp4").touch()
        (root / ".hidden").write_text("not served", encoding="utf-8")
        (root / "assets").mkdir()
        cls.server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(QuietHandler, directory=str(root))
        )
        cls.worker = Thread(target=cls.server.serve_forever, daemon=True)
        cls.worker.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.worker.join()
        cls.temp.cleanup()

    def request(self, path, range_header=None, method="GET"):
        connection = HTTPConnection(*self.server.server_address)
        headers = {"Range": range_header} if range_header else {}
        connection.request(method, path, headers=headers)
        response = connection.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        connection.close()
        return result

    def test_index(self):
        self.assertEqual(self.request("/")[0], 200)

    def test_video_ranges(self):
        for header, expected in [("bytes=2-5", b"2345"), ("bytes=8-", b"89"), ("bytes=-3", b"789")]:
            with self.subTest(header=header):
                status, headers, body = self.request("/sample.mp4", header)
                self.assertEqual(status, 206)
                self.assertEqual(body, expected)
                self.assertEqual(int(headers["Content-Length"]), len(expected))

    def test_invalid_ranges(self):
        for header in ["bytes=-0", "bytes=10-", "bytes=5-2", "bytes=-", "bytes=1-2,4-5"]:
            with self.subTest(header=header):
                self.assertEqual(self.request("/sample.mp4", header)[0], 416)
        self.assertEqual(self.request("/empty.mp4", "bytes=0-")[0], 416)

    def test_head_range(self):
        status, headers, body = self.request("/sample.mp4", "bytes=0-1", "HEAD")
        self.assertEqual(status, 206)
        self.assertEqual(headers["Content-Range"], "bytes 0-1/10")
        self.assertEqual(body, b"")

    def test_no_repository_or_directory_listing(self):
        for path in ["/.git/config", "/.hidden", "/assets/"]:
            with self.subTest(path=path):
                self.assertEqual(self.request(path)[0], 403)

    def test_site_integrity(self):
        self.assertEqual(validate()["errors"], [])

    def test_author_order(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "public/index.html").read_text(encoding="utf-8")
        authors = re.search(r'<ul class="publication-authors".*?</ul>', html, re.S)
        self.assertIsNotNone(authors)
        self.assertEqual(re.findall(r"<li>(.*?)</li>", authors.group()), [
            "Yeong Gwang Son", "Hyunchang Kang", "Youngbin Song",
            "Hyunjoon Cho", "Hyouk Ryeol Choi",
        ])

    def test_jig_video_uses_distance_plot(self):
        root = Path(__file__).resolve().parents[1]
        catalog = json.loads((root / "public/catalog.json").read_text(encoding="utf-8"))
        asset = next(a for a in catalog["assets"] if a["id"] == "sensor-jig-motion")
        self.assertEqual(asset["src"], "assets/sensor-jig-with-plot.mp4")
        html = (root / "public/index.html").read_text(encoding="utf-8")
        jig_section = re.search(r'<details[^>]*><summary>Watch the distance-estimation test jig</summary>.*?</details>', html, re.S)
        self.assertIsNotNone(jig_section)
        self.assertIn('data-video="sensor-jig-motion"', jig_section.group())
        self.assertIn("8× playback", jig_section.group())

    def test_reference_typography_and_navigation(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "public/index.html").read_text(encoding="utf-8")
        css = (root / "public/style.css").read_text(encoding="utf-8")
        self.assertIn("family=Source+Sans+Pro", html)
        self.assertIn('<h1 class="publication-title">Interactive Diffusion Policy</h1>', html)
        self.assertIn("--accent:#8c1515", css)
        self.assertIn('<nav class="footer-nav" aria-label="Page sections">', html)
        self.assertNotIn('class="site-nav"', html)
        self.assertIn("Coming soon.", html)

    def test_research_montage_is_the_hero(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "public/index.html").read_text(encoding="utf-8")
        catalog = json.loads((root / "public/catalog.json").read_text(encoding="utf-8"))
        hero = re.search(r'<video\b[^>]*id="hero-video"[^>]*>', html)
        self.assertIsNotNone(hero)
        self.assertIn('data-hero="idp-research-montage"', hero.group())
        self.assertTrue(any(a["id"] == "idp-research-montage" and a["kind"] == "video"
                            for a in catalog["assets"]))
        note = re.search(r'<p class="teaser-note">(.*?)</p>', html, re.S)
        self.assertIn("human-guided data collection", note.group())
        self.assertNotIn("two recorded trials", note.group())


if __name__ == "__main__":
    unittest.main()
