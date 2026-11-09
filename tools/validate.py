"""Validate the portable static site without third-party dependencies."""

from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "public"
TEXT_SUFFIXES = {".html", ".js", ".css", ".json", ".md", ".py", ".svg"}
PRIVATE_PATTERNS = {
    "GitHub credential": re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,})"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "local user path": re.compile(r"[A-Za-z]:[\\/]Users[\\/]", re.I),
    "signed download URL": re.compile(r"X-Amz-(?:Credential|Signature|Security-Token)=", re.I),
}


def validate():
    errors = []
    catalog = json.loads((SITE / "catalog.json").read_text(encoding="utf-8"))
    script = (SITE / "catalog.js").read_text(encoding="utf-8")
    if not script.startswith("window.IDP_CATALOG = "):
        errors.append("catalog.js has an unexpected format")
    else:
        embedded = json.loads(script.removeprefix("window.IDP_CATALOG = ").rstrip().removesuffix(";"))
        if embedded != catalog:
            errors.append("catalog.js and catalog.json disagree")
    html = (SITE / "index.html").read_text(encoding="utf-8")
    ids = re.findall(r'\bid="([^"]+)"', html)
    if len(ids) != len(set(ids)):
        errors.append("Duplicate HTML IDs")
    for anchor in re.findall(r'href="#([^"]+)"', html):
        if anchor not in ids:
            errors.append(f"Missing anchor: {anchor}")
    for reference in re.findall(r'(?:src|href)="([^"#]+)"', html):
        parsed = urlsplit(reference)
        if parsed.scheme or parsed.netloc:
            continue
        target = (SITE / unquote(parsed.path)).resolve()
        if not target.is_relative_to(SITE.resolve()) or not target.is_file():
            errors.append(f"Missing or unsafe page asset: {reference}")
    assets = catalog["assets"]
    bindings = {identifier for a in assets for identifier in [a["id"], *a.get("aliases", [])]}
    if len({a["id"] for a in assets}) != len(assets):
        errors.append("Duplicate catalog IDs")
    for binding in re.findall(r'data-(?:feature|video)="([^"]+)"', html):
        if binding not in bindings:
            errors.append(f"Unresolved media binding: {binding}")
    for asset in assets:
        for field in ("src", "thumbnail"):
            if not asset.get(field):
                continue
            target = (SITE / asset[field]).resolve()
            if not target.is_relative_to(SITE.resolve()) or not target.is_file():
                errors.append(f"Missing or unsafe media asset: {asset[field]}")
        target = SITE / asset["src"]
        if target.is_file():
            if target.stat().st_size != asset["bytes"]:
                errors.append(f"Media size mismatch: {asset['src']}")
            if sha256(target.read_bytes()).hexdigest() != asset["file_sha256"]:
                errors.append(f"Media SHA-256 mismatch: {asset['src']}")
        if asset.get("thumbnail") and (SITE / asset["thumbnail"]).is_file():
            thumbnail = SITE / asset["thumbnail"]
            if sha256(thumbnail.read_bytes()).hexdigest() != asset["thumbnail_sha256"]:
                errors.append(f"Thumbnail SHA-256 mismatch: {asset['thumbnail']}")
    files = [p for p in SITE.rglob("*") if p.is_file()]
    for file in files:
        if file.stat().st_size >= 100 * 1024 * 1024:
            errors.append(f"File exceeds GitHub limit: {file.relative_to(ROOT)}")
        if file.suffix.lower() in {".h5", ".hdf5", ".ckpt", ".pt", ".pth", ".pem", ".key"}:
            errors.append(f"Disallowed research or credential file: {file.relative_to(ROOT)}")
    scanned = 0
    for file in ROOT.rglob("*"):
        relative = file.relative_to(ROOT)
        if any(p in {".git", "__pycache__", ".venv", "qa", "tmp"} for p in relative.parts):
            continue
        if file.is_file() and file.suffix.lower() in TEXT_SUFFIXES:
            scanned += 1
            text = file.read_text(encoding="utf-8")
            for label, pattern in PRIVATE_PATTERNS.items():
                if pattern.search(text):
                    errors.append(f"{label} in {relative}")
    return {
        "assets": len(assets),
        "site_files": len(files),
        "site_bytes": sum(p.stat().st_size for p in files),
        "text_files_scanned": scanned,
        "errors": errors,
    }


if __name__ == "__main__":
    result = validate()
    print(json.dumps(result, indent=2))
    raise SystemExit(bool(result["errors"]))
