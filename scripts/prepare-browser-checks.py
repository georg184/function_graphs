"""Prepare isolated offline, sandboxed bridge and PyHTML integration fixtures."""

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

from muweb import install_artifact, read_artifact
from pyhtml.mathjax import _mathjax_runtime_markup

ROOT: Path = Path(__file__).resolve().parent.parent


def main() -> None:
    """Build independent fixtures without modifying any consumer worksheet."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    directory = args.directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    artifact_path = directory / "function_graphs.muweb"
    subprocess.run([sys.executable, str(ROOT / "scripts/build-muweb.py"), str(artifact_path),
                    "--offline-page", str(directory / "standalone.html")], check=True)
    artifact = read_artifact(artifact_path)
    entry = artifact.entry_bytes.decode("utf-8")
    assert "cdn.jsdelivr.net" not in entry
    install_artifact(artifact, directory / "interactive")
    runtime = _mathjax_runtime_markup()
    data = json.dumps({"entry": entry.replace("</head>", runtime + "</head>", 1),
                       "withoutRuntime": entry, "version": artifact.manifest.version,
                       "stateVersion": artifact.manifest.state_version}).replace("</", "<\\/")
    host = '''<!doctype html><meta charset="utf-8"><title>Function graphs bridge checks</title>
<style>body{margin:0}iframe{width:100%;height:100vh;border:0}</style>
<iframe id="module" sandbox="allow-scripts" title="Function graphs"></iframe>
<script>
const fixtureData = FIXTURE_DATA, frame = document.querySelector('iframe');
let sequence = 0, activeUrl = null, options = {}, saved = null;
window.fixture = {
  messages: [],
  send(kind,payload={}) {
    frame.contentWindow.postMessage({format:'muweave-interactive-bridge',protocolVersion:1,
      instance:'test',channel:'test-channel',sequence:sequence++,kind,payload},'*');
  },
  mount(next={}) {
    if(activeUrl) URL.revokeObjectURL(activeUrl);
    options=next; sequence=0; this.messages=[]; saved=next.state??null;
    activeUrl=URL.createObjectURL(new Blob([next.noRuntime?fixtureData.withoutRuntime:fixtureData.entry],{type:'text/html'}));
    frame.src=activeUrl+'#muweave-instance=test&muweave-channel=test-channel';
  },
  get state() {return saved;}
};
function initialize() {
  fixture.send('init', {
    state:saved, typography:options.typography??{fontSizePt:10,lineHeight:1.35,scaleFactor:1.25},
    module:{id:'function_graphs',version:fixtureData.version,stateVersion:fixtureData.stateVersion,instance:'test',
      activity:options.activity??'power',presentation:options.presentation??'compact',launchParameters:options.launchParameters??{}}
  });
}
function migrate() {
  fixture.send('migrate-state',{requestId:saved.schema,fromVersion:saved.schema,toVersion:saved.schema+1,state:saved});
}
addEventListener('message', event => {
  if(event.source!==frame.contentWindow || event.data?.channel!=='test-channel') return;
  const message=event.data; fixture.messages.push(message);
  if(message.kind==='ready') {
    if(options.migrate) migrate();
    else initialize();
  }
  if(message.kind==='migration-result' && message.payload.ok) {
    saved=message.payload.state;
    if(saved.schema<fixtureData.stateVersion) migrate(); else initialize();
  }
  if(message.kind==='state-changed'||message.kind==='snapshot') saved=message.payload.state;
});
fixture.mount();
</script>'''.replace("FIXTURE_DATA", data)
    (directory / "host.html").write_text(host, encoding="utf-8")
    source = directory / "smoke.muweave"
    source.write_text(
        'µblock.interactive("function_graphs", instance="graphs-inline", activity="power", presentation="compact")\n\n'
        'µblock.interactive("function_graphs", instance="graphs-tab", activity="linear", presentation="full", open="tab")\n\n'
        'µblock.applet[url="https://georg184.github.io/items/440/?type=quadratic", title="Funktionen entdecken"]{\n'
        'µblock.interactive("function_graphs", instance="graphs-applet", activity="quadratic", presentation="full")\n'
        ',,\nWähle den Funktionstyp und verändere die Parameter.\n}\n', encoding="utf-8")
    subprocess.run([sys.executable, "-m", "pyhtml", str(source), "--output", str(directory / "smoke.html"),
                    "--interactive-dir", str(directory / "interactive"), "--math-renderer", "mathjax",
                    "--no-coach", "--no-template"], cwd=directory, check=True)
    html = (directory / "smoke.html").read_text(encoding="utf-8")
    assert html.count('id="muweave-mathjax"') == html.count('id="muweave-mathjax-config"') == 1
    assert html.count('id="muweave-runtime-profiles"') == 1
    spec = importlib.util.spec_from_file_location("producer", ROOT / "scripts/build-muweb.py")
    assert spec is not None and spec.loader is not None
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)
    standalone = producer.compose_html(embedded=False)
    (directory / "no-runtime.html").write_text(standalone.replace(runtime, ""), encoding="utf-8")
    (directory / "mixed-version.html").write_text(
        standalone.replace(f"const VERSION = '{artifact.manifest.version}'", "const VERSION = 'stale'", 1), encoding="utf-8")
    print(f"Browser fixtures: {directory}")


if __name__ == "__main__":
    main()
