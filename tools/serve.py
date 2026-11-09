"""Serve only the website on loopback, with byte-range video seeking."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import shutil
from urllib.parse import unquote, urlsplit


class Handler(SimpleHTTPRequestHandler):
    def send_head(self):
        self.byte_range = None
        root = Path(self.directory).resolve()
        path = Path(self.translate_path(self.path)).resolve()
        parts = Path(unquote(urlsplit(self.path).path)).parts
        if not path.is_relative_to(root) or any(p.startswith(".") for p in parts):
            self.send_error(403)
            return None
        header = self.headers.get("Range")
        if not header or not path.is_file():
            return super().send_head()
        size = path.stat().st_size
        match = re.fullmatch(r"bytes=(\d*)-(\d*)", header)
        if not match or not any(match.groups()) or size == 0:
            return self.invalid_range(size)
        first, last = match.groups()
        if first:
            start = int(first)
            end = min(int(last), size - 1) if last else size - 1
        else:
            suffix = int(last)
            if suffix == 0:
                return self.invalid_range(size)
            start, end = max(0, size - suffix), size - 1
        if start > end or start >= size:
            return self.invalid_range(size)
        source = path.open("rb")
        source.seek(start)
        self.byte_range = end - start + 1
        self.send_response(206)
        self.send_header("Content-Type", self.guess_type(str(path)))
        self.send_header("Content-Length", str(self.byte_range))
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        return source

    def invalid_range(self, size):
        self.send_response(416)
        self.send_header("Content-Range", f"bytes */{size}")
        self.send_header("Content-Length", "0")
        self.end_headers()
        return None

    def copyfile(self, source, output):
        if self.byte_range is None:
            return shutil.copyfileobj(source, output)
        remaining = self.byte_range
        while remaining:
            block = source.read(min(65536, remaining))
            if not block:
                break
            output.write(block)
            remaining -= len(block)

    def list_directory(self, path):
        self.send_error(403, "Directory listing disabled")
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8774)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1] / "public"
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port), partial(Handler, directory=str(root))
    )
    print(f"Local project preview: http://127.0.0.1:{args.port}/", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
