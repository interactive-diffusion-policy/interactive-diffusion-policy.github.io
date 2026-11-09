# Interactive Diffusion Policy - Project Website

Project website for **Interactive Diffusion Policy: Safe Reactive Avoidance
through Proximity Sensing in Human-Robot Shared Environments**.

This repository contains the editable website and its selected figures and
videos. It does **not** contain robot-control software, training datasets,
checkpoints, the manuscript source, or internal correspondence.

Authors: Yeong Gwang Son, Hyunchang Kang, Youngbin Song, Hyunjoon Cho, and
Hyouk Ryeol Choi.

## Local Preview

Python 3.10 or newer is sufficient. No package installation or build step is
required.

```sh
python tools/validate.py
python -m unittest discover -s tests -v
python tools/serve.py --port 8774
```

Open <http://127.0.0.1:8774/>. Stop the server with Ctrl+C. The preview serves
only `public/`, binds to loopback, and supports video seeking with HTTP ranges.
It does not serve the Git repository or development files.

## Editing

| File | Purpose |
| --- | --- |
| `public/index.html` | Page sections, text, figure captions, and result table |
| `public/style.css` | Responsive styling |
| `public/app.js` | Video chapters, comparison tabs, and media dialogs |
| `public/catalog.json` | Selected media metadata |
| `public/catalog.js` | The same catalog for direct-file and HTTP previews |
| `public/assets/` | Selected video, figure, and thumbnail files |
| `tools/validate.py` | Links, media integrity, and credential/path checks |
| `tools/update_catalog.py` | Refresh catalog integrity fields and cache revisions |
| `tools/serve.py` | Local-only static preview |

After editing the catalog or replacing media, run `python tools/update_catalog.py`
to synchronize `catalog.js` with `catalog.json`. It records actual web-file and
thumbnail hashes while preserving legacy source-image identifiers in `sha256`.
The validator checks catalog equality and web-file hashes. Re-run validation and
tests after making changes. JavaScript can additionally be checked with
`node --check public/app.js` when Node.js is available.

## Repository And Publication

The repository is public. Its GitHub Pages address is
<https://interactive-diffusion-policy.github.io/>.
`.github/workflows/deploy-pages.yml` publishes the `public/` directory on changes
to `main`, or by manual workflow dispatch. A repository owner or administrator
must keep GitHub Pages configured to use **GitHub Actions** as its source.

Repository privacy is not website access control: the published site and its
media may be publicly accessible. All website resource paths are relative, so a
repository subpath is supported. The search-engine `noindex` directive is only
a crawler hint, not authentication.

The source snapshot follows the supplied October 2026 manuscript. Its result
table is a transcription of the manuscript, not a new trial-level evaluation.
Media preserve the distinction between autonomous execution and human-assisted
data collection. Do not relabel one as the other.

The current highlight is the full original recording shown in the two-event
comparison. It is encoded without audio and plays at 1.8x recorded speed at
the browser's default playback rate. The earlier two-excerpt edit is retained.
The previous 30.708-second teaser uses two recorded trials. `tools/hero-video.json`
preserves the source windows: DGB 3-20 s at 1x, DGB 32-48.3 s at 2x, and SAO
33-44 s at 2x. Render with the local `ffmpeg-skill` `render.py` and review the
result before updating the catalog. The full supplementary video remains under
the highlight. The DGB/SAO comparison controls play separate recordings together;
they do not imply paired starts or hardware time synchronization.

The previous public paper-page route is being retired separately from this
repository. The personal research portfolio and robotics implementation
repositories are separate projects.

## Rights

No new license is granted by this migration. Paper figures, videos, institution
logos, and source code may have different rights; obtain the relevant owners'
approval before redistribution or applying a repository-wide license.
