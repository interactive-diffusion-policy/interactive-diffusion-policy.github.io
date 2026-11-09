"""Refresh web-file integrity fields, the JS catalog, and resource revisions."""

from hashlib import sha256
import json
from pathlib import Path
import re


SITE = Path(__file__).resolve().parents[1] / "public"


def local_file(relative):
    target = (SITE / relative).resolve()
    if not target.is_relative_to(SITE.resolve()) or not target.is_file():
        raise ValueError(f"Missing or unsafe media path: {relative}")
    return target


def main():
    catalog = json.loads((SITE / "catalog.json").read_text(encoding="utf-8"))
    for asset in catalog["assets"]:
        file = local_file(asset["src"])
        asset["file_sha256"] = sha256(file.read_bytes()).hexdigest()
        asset["bytes"] = file.stat().st_size
        # Legacy sha256 identifies the input image before web conversion.
        asset.setdefault("sha256", asset["file_sha256"])
        if asset.get("thumbnail"):
            thumbnail = local_file(asset["thumbnail"])
            asset["thumbnail_sha256"] = sha256(thumbnail.read_bytes()).hexdigest()
    (SITE / "catalog.json").write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (SITE / "catalog.js").write_text(
        "window.IDP_CATALOG = " + json.dumps(catalog, ensure_ascii=False) + ";\n",
        encoding="utf-8",
    )
    html = (SITE / "index.html").read_text(encoding="utf-8")
    for name in ["app.js", "style.css", "catalog.js"]:
        revision = sha256((SITE / name).read_bytes()).hexdigest()[:12]
        html = re.sub(
            r'"' + re.escape(name) + r'(?:\?v=[^"\s]+)?"',
            f'"{name}?v={revision}"', html,
        )
    (SITE / "index.html").write_text(html, encoding="utf-8")
    print(f"Updated {len(catalog['assets'])} media records; source IDs preserved.")


if __name__ == "__main__":
    main()
