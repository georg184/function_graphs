# Funktionen entdecken

Ein interaktives Applet für lineare Funktionen, quadratische Funktionen und
Potenzfunktionen mit positivem ganzzahligem Grad. Eine ständig sichtbare
Radiobutton-Gruppe wählt den Funktionstyp. Die zugehörigen Regler verändern
den Graphen und seine Funktionsgleichung sofort. Alle Achsen verwenden
denselben Massstab; Vergrössern, Verkleinern und Standardansicht ändern nur
den Diagrammausschnitt. Über dem Diagramm zoomt das Mausrad zum Mauszeiger:
Der betrachtete Punkt bleibt an derselben Bildschirmposition. Der vertikale
Ausschnitt kann bis auf 0.05 Einheiten vergrössert werden, um Schnittpunkte
genauer zu untersuchen. «Standardansicht» stellt den ursprünglichen Ausschnitt
um den Ursprung wieder her. Ausserhalb des Diagramms scrollt das Mausrad die
Seite; Strg/Cmd mit Mausrad bleibt dem Browser vorbehalten.

Bei Potenzfunktionen lässt sich ein zweiter Graph `g(x)=a*x^m` zuschalten.
Beide Graphen teilen den Vorfaktor `a`; die Grade `n` und `m` sind unabhängig
einstellbar. Der Graph von `f` ist durchgezogen und türkis, der von `g`
gestrichelt und orange. Die entsprechend gefärbten Gleichungen zeigen die
aktuellen Funktionen. Beim Wechsel des Funktionstyps bleibt die
Vergleichseinstellung gespeichert und wird nur bei Potenzfunktionen angezeigt.

Die Oberfläche ist deutsch. Die Parameterwerte lassen sich auch direkt
eingeben. Die Regler verwenden Schritte von 0.1, der Grad Schritte von 1.
Der Gradbereich reicht von 1 bis 12. Bei `a=0` erklärt das Applet ausdrücklich
den Übergang zur linearen Funktion beziehungsweise zur Nullfunktion, die
nicht zur hier definierten Familie der Potenzfunktionen gehört.

## Öffnen und verlinken

`index.html` öffnet die eigenständige Anwendung; sie lädt die festgelegte
MathJax-Version. Der unten beschriebene Build erzeugt daneben eine vollständig
offline nutzbare HTML-Datei aus derselben Implementierung.

Der URL-Parameter `type` legt die Vorauswahl fest:

| Parameter | Vorauswahl |
| --- | --- |
| `?type=linear` | Lineare Funktionen, Regler `m`, `q` |
| `?type=quadratic` | Quadratische Funktionen, Regler `a`, `b`, `c` |
| `?type=power` | Potenzfunktionen, Regler `a`, `n` |

Ohne gültige URL-Vorauswahl wird ein gespeicherter Stand wiederhergestellt;
ohne gespeicherten Stand beginnt das Applet mit Potenzfunktionen. Eine gültige
explizite Vorauswahl hat Vorrang vor dem gespeicherten Funktionstyp. Die
gespeicherten Parameter jeder Familie bleiben erhalten. Der Link-Button
kopiert die Vorauswahl, nicht die aktuellen Parameterwerte.

Öffentliche Anwendung: [Funktionen entdecken](https://georg184.github.io/items/440/).
[Potenzfunktionen vorauswählen](https://georg184.github.io/items/440/?type=power).

## MuWeave

Die Modul-ID ist `function_graphs`, die Standardaktivität `power`. Die weiteren
Aktivitäten `linear` und `quadratic` stellen lediglich den anfänglichen
Funktionstyp ein; jede Aktivität erlaubt weiterhin den Wechsel zwischen allen
drei Familien. Eine explizite Vorauswahl der öffentlichen Itemseite wird nach
der kompatiblen Host-Speicherung angewandt; die Parameterwerte bleiben dabei
erhalten. Ohne URL-Vorauswahl gilt der gespeicherte Stand.

```text
µblock.interactive("function_graphs", instance="funktionen-entdecken", activity="power")
```

`presentation="compact"` blendet die allgemeine Kopfzeile aus;
`presentation="full"` zeigt die vollständige App. Die Host-Typografie stammt
aus der unveränderten MuWeb-Bridge und dem generierten gemeinsamen
`js/vendor/muweave-typography.js`. Diese Datei nicht von Hand ändern;
`../shared/sync-muweave-typography.py` erzeugt die registrierten Kopien.

Das deklarierte Profil `muweave-mathjax-4-svg-v1` setzt im konsumierenden
Dokument den MathJax-Renderer voraus. Die App bündelt keine zweite
Formellaufzeit. Der vollständige PyHTML-Export funktioniert offline.

Das kanonische Item 440 (`ggpackages/muweave_library/items/440.muweave`)
enthält die Applet-Einbindung mit der Vorauswahl `power` und eine Beschreibung
für das PDF. Im Kapitel wird es mit `µblock.applet(item=440)` eingefügt.

## Zustand

Schema 3 enthält `schema`, `type`, `parameters` mit sämtlichen Werten aller
drei Familien sowie `span` für den vertikalen Diagrammausschnitt und
`center: {x, y}` für dessen Mittelpunkt. `comparison`
speichert, ob der Vergleichsgraph eingeschaltet ist; `parameters.power.m`
speichert seinen Grad. Der Vorfaktor wird gemeinsam aus `parameters.power.a`
gelesen. Die Migration von Schema 1 ergänzt `comparison=false` und `m=2`,
ohne vorhandene Parameter zu verändern. Die Migration 2 → 3 ergänzt den
bisherigen Mittelpunkt `{x: 0, y: 0}`. Beide benachbarten Migrationen sind bei
der MuWeb-Bridge registriert und gelten auch für eigenständige Seiten.
Der Ausschnitt bleibt nach dem Neuladen und beim Wiederherstellen einer
gespeicherten MuWeave-Arbeit erhalten. `span` liegt zwischen 0.05 und 80,
die Mittelpunktskoordinaten zwischen −10000 und 10000. Alle Zahlen werden auf
endliche Werte, Grenzen und bei Parametern auf die Schrittweite geprüft.
Typografie, Fenstergrösse und compact/full gehören nicht zum Lernzustand.

Eigenständige Seiten behalten den Speicherschlüssel `function-graphs-state-v1` im lokalen
Browser-Speicher. Eingebettet ist ausschliesslich die MuWeb-Bridge zuständig.
Ungültige Daten bleiben erhalten und sperren die Bearbeitung mit einer
sichtbaren Meldung. Eine Host-Speichersperre deaktiviert Änderungen.

## Bauen und prüfen

Audience: application maintainers

Die Befehle laufen im App-Verzeichnis. `python` ist die vorhandene
Workspace-Debug-Umgebung mit MuWeb und PyHTML; die Browserprüfung benötigt
zusätzlich Playwright und Chrome. Es gibt keinen npm-Build.

```bash
node tests/core.test.cjs
node --check js/app.js
python scripts/prepare-browser-checks.py /tmp/function-graphs-check
python -m muweb validate /tmp/function-graphs-check/function_graphs.muweb
python scripts/verify-browser.py /tmp/function-graphs-check
```

Die Vorbereitung erzeugt eine Offline-Seite, einen echten sandboxierten
Bridge-Host und eine unabhängige PyHTML-Datei mit mehreren Einbindungen.
Die Browserprüfung sperrt Netzwerkzugriffe und prüft Auswahl, alle Regler,
Link-Vorauswahl, Zustandswiederherstellung und Migration, Vergleichsgraph mit
gemeinsamem Vorfaktor, Mausradzoom mit festem Bezugspunkt, Ausschnittspeicherung,
Rücksetzen, Seitenscrollen ausserhalb des Diagramms, Typografie, Sonderfälle,
Tastaturbedienung, schmale Ansichten und sichtbare Infrastrukturfehler.
`--only standalone|host|pyhtml|failures` erlaubt gezielte Wiederholungen.

Den deterministischen Build separat erzeugen:

```bash
python scripts/build-muweb.py /tmp/function-graphs-check/function_graphs.muweb \
  --offline-page build/function_graphs.html
```

Erst nach erfolgreicher Prüfung die identischen Bytes installieren:

```bash
python -m muweb install /tmp/function-graphs-check/function_graphs.muweb \
  --interactive-dir /mnt/data/sync/software/Python/ggpackages/muweave_library/interactive
```

Die Versionskennung in Manifest, Einstiegspunkt, Kernmodul, UI und allen
lokalen Asset-URLs muss identisch sein. Fehlende Mathematik-Laufzeit oder
gemischte Dateien stoppen die Anwendung mit einer sichtbaren Meldung.

## Veröffentlichung

Audience: application maintainers

Das Quellrepository ist [georg184/function_graphs](https://github.com/georg184/function_graphs),
Branch `main`. GitHub Pages verwendet den Actions-Workflow
`.github/workflows/deploy-pages.yml`. Er prüft die JavaScript-Dateien und die
Kerntests und veröffentlicht ausschliesslich `index.html`, `.nojekyll`,
`css/` und `js/`.

Die öffentliche Lernadresse ist `https://georg184.github.io/items/440/`.
Das eigenständige Quellprojekt bleibt separat; auch seine Link-Buttons zeigen
auf die Itemadresse. Die zusätzliche Projektseite unter `/function_graphs/`
verwendet dieselbe Implementierung.

Nach App-Änderungen das geprüfte MuWeb-Artefakt installieren und den Wrapper
`../items/440.muweave` mit `../items/scripts/export.py 440` neu exportieren.
Die selbstständige Itemseite entsteht ausschliesslich durch diesen regulären
PyHTML-Export. Der [Item-Veröffentlichungsablauf](../items/DEVELOPMENT.md)
beschreibt Prüfung und Lieferung des separaten Repositories. Die zugehörigen
MuWeave-Dokumente ebenfalls neu bauen.

Ein freigegebener `git push origin main` in diesem Quellprojekt aktualisiert
die zusätzliche Projektseite.
Den Workflow bis zum Abschluss verfolgen und anschliessend den öffentlichen
Versionsstand, die ausgelieferten Dateien sowie alle drei `?type=...`-Links
in einem frischen Browserprofil prüfen.
