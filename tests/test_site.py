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

    def test_author_order_and_profile_links(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "public/index.html").read_text(encoding="utf-8")
        authors = re.search(r'<ul class="publication-authors".*?</ul>', html, re.S)
        self.assertIsNotNone(authors)
        names = [
            re.sub(r"<[^>]+>", "", item).strip(" ,")
            for item in re.findall(r"<li>(.*?)</li>", authors.group(), re.S)
        ]
        self.assertEqual(names, [
            "Yeong Gwang Son", "Hyunchang Kang", "Youngbin Song", "Hyunjoon Cho", "Hyouk Ryeol Choi",
        ])
        links = re.findall(r'<a\b[^>]*\bhref="([^"]+)"[^>]*>([^<]+)</a>', authors.group())
        self.assertEqual(links, [
            ("https://sonyeonggwang.github.io/", "Yeong Gwang Son"),
            ("https://hyunchangkang.github.io/MyWebsite/", "Hyunchang Kang"),
            ("https://dudqls10.github.io/", "Youngbin Song"),
            ("https://cheesss.github.io/", "Hyunjoon Cho"),
        ])
        self.assertNotIn("pure.skku.edu", html)
        self.assertEqual(html.count('href="https://cheesss.github.io/"'), 1)

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
        self.assertIn("family=Google+Sans", html)
        self.assertIn("family=Noto+Sans", html)
        self.assertNotIn("Source+Sans+Pro", html)
        self.assertIn('<h1 class="publication-title">Interactive Diffusion Policy</h1>', html)
        self.assertIn("--sans:'Noto Sans'", css)
        self.assertIn("--display:'Google Sans'", css)
        self.assertIn('<nav class="footer-nav" aria-label="Page sections">', html)
        self.assertNotIn('class="site-nav"', html)
        self.assertNotIn("Submitted to IEEE Robotics and Automation Letters", html)
        self.assertNotIn("Awaiting review", html)
        self.assertNotIn('id="resources"', html)

    def test_abstract_is_the_manuscript_abstract(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "public/index.html").read_text(encoding="utf-8")
        abstract = re.search(r'<div class="abstract">(.*?)</div>', html, re.S)
        self.assertIsNotNone(abstract)
        paragraphs = re.findall(r"<p>(.*?)</p>", abstract.group(1), re.S)
        self.assertEqual(len(paragraphs), 1)
        self.assertTrue(paragraphs[0].startswith("Manipulators sharing a workspace with humans must avoid"))
        self.assertIn("out-of-distribution states. In this paper, we propose Interactive Diffusion Policy (IDP)", paragraphs[0])
        self.assertIn("achieved a task success rate of 91.3%.", paragraphs[0])
        self.assertIn("<strong>91.3%</strong>", html)

    def test_captions_are_prose_without_paper_numbering(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "public/index.html").read_text(encoding="utf-8")
        captions = re.findall(r"<figcaption>(.*?)</figcaption>", html, re.S)
        captions += re.findall(r'<p id="table1-caption" class="table-caption">(.*?)</p>', html, re.S)
        self.assertEqual(len(captions), 12)
        for caption in captions:
            with self.subTest(caption=caption[:40]):
                self.assertNotRegex(caption, r"\b(?:Figure|Fig\.|Table)\s*[0-9IVX]+")
                self.assertNotIn("<strong>", caption)

    def test_runtime_diagnostic_videos_are_removed(self):
        root = Path(__file__).resolve().parents[1]
        js = (root / "public/app.js").read_text(encoding="utf-8")
        catalog = json.loads((root / "public/catalog.json").read_text(encoding="utf-8"))
        self.assertNotIn("Inspect observation and guidance plots", js)
        self.assertNotIn("notion-lpb-", js)
        self.assertEqual([a["id"] for a in catalog["assets"] if a["id"].startswith("notion-lpb-")], [])
        self.assertEqual(list((root / "public/assets").glob("notion-lpb-*")), [])

    def test_robot_is_called_a_manipulator(self):
        root = Path(__file__).resolve().parents[1]
        for name in ["public/index.html", "public/app.js", "public/catalog.json"]:
            with self.subTest(file=name):
                text = (root / name).read_text(encoding="utf-8")
                self.assertNotRegex(text, r"(?i)\bRB-?10\b|Rainbow Robotics")
        html = (root / "public/index.html").read_text(encoding="utf-8")
        self.assertIn("Wide-range pick-and-place on a single-arm manipulator.", html)

    def test_trajectory_analysis_captions_omit_sync_details(self):
        root = Path(__file__).resolve().parents[1]
        catalog = json.loads((root / "public/catalog.json").read_text(encoding="utf-8"))
        analyses = [a for a in catalog["assets"] if a["id"].startswith("fig9-sync-")]
        self.assertEqual(len(analyses), 6)
        for asset in analyses:
            with self.subTest(asset=asset["id"]):
                self.assertNotRegex(asset["caption"], r"(?i)synchroni[sz]ed|alignment|0624")

    def test_title_block_logo_and_affiliation(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "public/index.html").read_text(encoding="utf-8")
        logo = html.find('<img src="skku-robotics-innovatory-logo.png"')
        self.assertGreater(logo, 0)
        self.assertLess(logo, html.find('<h1 class="publication-title">'))
        affiliation = re.search(r'<div class="publication-affiliation">(.*?)</div>', html, re.S)
        self.assertIsNotNone(affiliation)
        text = re.sub(r"<[^>]+>", "", affiliation.group(1)).replace("&nbsp;", " ")
        self.assertEqual(text, "Department of Mechanical Engineering · Sungkyunkwan University")

    def test_title_block_links(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "public/index.html").read_text(encoding="utf-8")
        catalog = json.loads((root / "public/catalog.json").read_text(encoding="utf-8"))
        block = re.search(r'<div class="publication-links">.*?</div>', html, re.S)
        self.assertIsNotNone(block)
        paper = re.search(r'<a\b[^>]*\bhref="(assets/[^"]+\.pdf)"[^>]*>.*?<span>Paper</span></a>', block.group(), re.S)
        self.assertIsNotNone(paper)
        self.assertTrue((root / "public" / paper.group(1)).is_file())
        video = re.search(r'<a\b[^>]*\bhref="([^"]+)"[^>]*\bdata-open-media="([^"]+)"', block.group())
        self.assertIsNotNone(video)
        asset = next(a for a in catalog["assets"] if a["id"] == video.group(2))
        self.assertEqual(video.groups(), (asset["src"], "idp-project-video"))
        code = re.search(r'<span class="publication-link is-disabled">(.*?)</span></span>', block.group(), re.S)
        self.assertIsNotNone(code)
        self.assertIn("Code (coming soon)", code.group(1))
        self.assertNotIn("<a", code.group(1))

    def test_annotated_interaction_video_is_the_hero(self):
        root = Path(__file__).resolve().parents[1]
        html = (root / "public/index.html").read_text(encoding="utf-8")
        js = (root / "public/app.js").read_text(encoding="utf-8")
        catalog = json.loads((root / "public/catalog.json").read_text(encoding="utf-8"))
        hero = re.search(r'<video\b[^>]*id="hero-video"[^>]*>', html)
        self.assertIsNotNone(hero)
        hero_id = "idp-human-interaction-annotated"
        self.assertIn(f'data-hero="{hero_id}"', hero.group())
        asset = next(a for a in catalog["assets"] if a["id"] == hero_id)
        self.assertEqual(asset["kind"], "video")
        self.assertEqual(asset["src"], f"assets/{hero_id}.mp4")
        self.assertTrue(asset["thumbnail"])
        autoplay = re.search(r"const autoplay = \[([^\]]*)\]", js)
        self.assertIn(f"'{hero_id}'", autoplay.group(1))
        note = re.search(r'<p class="teaser-note">(.*?)</p>', html, re.S)
        self.assertEqual(note.group(1), asset["caption"])
        self.assertIn("(1× and 2× speed)", note.group(1))
        # Earlier highlights stay in the catalog; only the hero binding moves.
        self.assertIn("idp-human-interaction-full-1p8x", {a["id"] for a in catalog["assets"]})


if __name__ == "__main__":
    unittest.main()
