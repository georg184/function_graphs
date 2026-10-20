"""Build a deterministic MuWeb artifact and an optional standalone offline page."""

import argparse
import json
from pathlib import Path
import re
import tempfile

from muweb import build_artifact, module_bridge_source, write_artifact

ROOT: Path = Path(__file__).resolve().parent.parent
SCRIPTS: tuple[str, ...] = ("js/core.js", "js/vendor/muweave-typography.js", "js/app.js")
RUNTIME_TAG: str = '<script defer src="https://cdn.jsdelivr.net/npm/@mathjax/mathjax-modern-font@4.1.3/tex-mml-svg-mathjax-modern.js"></script>'
CSP: str = (
    "default-src 'none'; connect-src 'none'; object-src 'none'; base-uri 'none'; "
    "form-action 'none'; script-src 'unsafe-inline' 'unsafe-eval'; "
    "style-src 'unsafe-inline'; img-src data: blob:; font-src data:; "
    "frame-src 'none'; worker-src 'none'"
)


def compose_html(*, embedded: bool) -> str:
    """Inline the application while retaining the host-owned runtime boundary.

    Args:
        embedded: Whether to include the exact MuWeb bridge instead of MathJax.
    """
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    manifest = json.loads((ROOT / "muweb/muweave-module.json").read_text())
    version = manifest["version"]
    if f"window.GG_APP_VERSION = '{version}'" not in html:
        raise ValueError("Entry and manifest versions differ")
    for relative in ("js/core.js", "js/app.js"):
        source = (ROOT / relative).read_text(encoding="utf-8")
        if not re.search(rf"const (?:APP_)?VERSION = '{re.escape(version)}'", source):
            raise ValueError(f"Stale application asset: {relative}")
    replacements = {
        f'<link rel="stylesheet" href="css/styles.css?v={version}">':
            f'<style>{(ROOT / "css/styles.css").read_text(encoding="utf-8")}</style>',
        f'<script src="js/mathjax-config.js?v={version}"></script>': "",
        RUNTIME_TAG: "",
        **{f'<script defer src="{path}?v={version}"></script>': "" for path in SCRIPTS},
    }
    for old, new in replacements.items():
        if html.count(old) != 1:
            raise ValueError(f"Expected one asset reference: {old}")
        html = html.replace(old, new, 1)
    if embedded:
        html = html.replace("<head>", f'<head>\n<meta http-equiv="Content-Security-Policy" content="{CSP}">', 1)
    else:
        from pyhtml.mathjax import _mathjax_runtime_markup

        html = html.replace("</head>", _mathjax_runtime_markup() + "\n</head>", 1)
    scripts = [(ROOT / path).read_text(encoding="utf-8") for path in SCRIPTS]
    if embedded:
        scripts.insert(1, module_bridge_source())
    markup = "\n".join(f"<script>{source.replace('</script', '<\\/script')}</script>" for source in scripts)
    before, after = html.rsplit("</body>", 1)
    return before + markup + "\n</body>" + after


def main() -> None:
    """Validate the producer output before writing either deliverable."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--offline-page", type=Path)
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix="function-graphs-build-") as temporary:
        source = Path(temporary)
        (source / "muweave-module.json").write_bytes((ROOT / "muweb/muweave-module.json").read_bytes())
        (source / "embed.html").write_text(compose_html(embedded=True), encoding="utf-8")
        artifact = build_artifact(source)
        write_artifact(artifact, args.output)
    if args.offline_page:
        args.offline_page.parent.mkdir(parents=True, exist_ok=True)
        args.offline_page.write_text(compose_html(embedded=False), encoding="utf-8")
    print(f"Validated {args.output}: {artifact.content_digest}")


if __name__ == "__main__":
    main()
