/* Accessible explorer UI, SVG graph and MuWeb learner-state integration. */
(function () {
  'use strict';
  const APP_VERSION = '20261020.201612';
  const PUBLIC_URL = 'https://georg184.github.io/function_graphs/';
  const core = window.FunctionGraphsCore;
  const bridge = window.MuWeaveModuleBridge || null;
  const storageKey = 'function-graphs-state-v1';
  const root = document.getElementById('app');
  const notice = document.getElementById('notice');
  const plot = document.getElementById('plot');
  const titles = {linear: 'Lineare Funktion', quadratic: 'Quadratische Funktion', power: 'Potenzfunktion'};
  const roles = {m: 'Steigung', q: 'Achsenabschnitt', a: 'Vorfaktor', b: 'Linearer Koeffizient', c: 'Achsenabschnitt', n: 'Grad'};
  let state = core?.createState(), ready = false, locked = false;
  let mathQueue = Promise.resolve(), formulaRevision = 0, lastHeight = 0;
  let lastInsight = '', drawingFrame = 0;

  /** Keep infrastructure failures visible and preserve any existing saved work. */
  function fail(message) {
    locked = true;
    notice.textContent = message;
    document.querySelectorAll('button, input').forEach(control => { control.disabled = true; });
  }

  if (!core || core.VERSION !== APP_VERSION || window.GG_APP_VERSION !== APP_VERSION || window.GGTypography?.VERSION !== '1.1.0') {
    fail('Die App-Dateien gehören zu verschiedenen Versionen. Bitte die Seite vollständig neu laden.');
    return;
  }

  /** Report content height without creating an iframe resize feedback loop. */
  function reportHeight() {
    // One extra CSS pixel covers fractional rounding in the host's scaled frame.
    // A subpixel inner scrollbar would otherwise consume the first wheel event.
    const height = Math.ceil(document.body.getBoundingClientRect().height) + 1;
    if (bridge?.isInitialized() && height > 0 && height !== lastHeight) {
      bridge.reportPreferredHeight(height);
      lastHeight = height;
    }
  }

  /** Serialize MathJax work and expose missing offline dependencies explicitly. */
  function withMath(action) {
    mathQueue = mathQueue.then(async () => {
      if (!window.MathJax?.startup?.promise) throw new Error('MathJax unavailable');
      await MathJax.startup.promise;
      if (!MathJax.tex2svgPromise || !MathJax.typesetPromise) throw new Error('MathJax unavailable');
      await action();
      if (root.querySelector('[data-mjx-error], mjx-merror')) throw new Error('Invalid mathematical expression');
      reportHeight();
    }).catch(() => fail('Die Formeldarstellung konnte nicht geladen werden. Bitte die Seite neu laden.'));
    return mathQueue;
  }

  /** Return the complete schema, including values of inactive function types. */
  function snapshot() {
    return ready ? core.validateState(state) : bridge?.getState() ?? null;
  }

  /** Save through the host when embedded; otherwise use ordinary local storage. */
  function publish() {
    if (!ready || locked) return;
    if (bridge) {
      if (!bridge.isEnabled()) { fail('Der Host hat Änderungen gesperrt. Der bisherige Stand bleibt erhalten.'); return; }
      bridge.updateState(snapshot());
    } else {
      try { localStorage.setItem(storageKey, JSON.stringify(snapshot())); }
      catch { notice.textContent = 'Dieser Browser kann den Stand nicht dauerhaft speichern. Das Applet bleibt auf dieser Seite nutzbar.'; }
    }
  }

  /** Update the live equation without letting rapid slider events display old values. */
  function renderFormula() {
    const revision = ++formulaRevision;
    const tex = core.formula(state.type, state.parameters[state.type]);
    const target = document.getElementById('formula');
    withMath(async () => {
      if (revision !== formulaRevision) return;
      const expression = await MathJax.tex2svgPromise(tex, {display: false});
      if (revision !== formulaRevision) return;
      target.replaceChildren(expression);
      target.dataset.tex = tex;
      root.dataset.ready = 'true';
    });
  }

  /** Explain geometric behavior and explicitly identify degree-degenerate cases. */
  function renderInsight() {
    const p = state.parameters[state.type];
    let content, special = false;
    if (state.type === 'power') {
      if (p.a === 0) {
        special = true;
        content = 'Bei \\(a=0\\) entsteht die Nullfunktion. Sie ist nach unserer Definition keine Potenzfunktion mit eindeutigem Grad.';
      } else {
        content = p.n % 2 === 0 ? 'Gerader Grad: Der Graph ist achsensymmetrisch zur \\(y\\)-Achse.' : 'Ungerader Grad: Der Graph ist punktsymmetrisch zum Ursprung.';
        content += ' Für Potenzfunktionen gilt \\(a\\ne 0\\).';
      }
    } else if (state.type === 'quadratic') {
      if (p.a === 0) {
        special = true;
        content = 'Bei \\(a=0\\) entfällt der quadratische Term. Es entsteht eine lineare Funktion, keine quadratische Funktion.';
      } else content = p.a > 0 ? 'Die Parabel ist nach oben geöffnet. Ein grösserer Betrag von \\(a\\) macht sie schmaler.' : 'Die Parabel ist nach unten geöffnet. Ein grösserer Betrag von \\(a\\) macht sie schmaler.';
    } else {
      content = p.m === 0 ? 'Bei \\(m=0\\) ist die Gerade waagrecht. \\(q\\) bestimmt ihren Abstand von der \\(x\\)-Achse.' : '\\(m\\) bestimmt die Steigung der Geraden, \\(q\\) ihren Schnittpunkt mit der \\(y\\)-Achse.';
    }
    if (content === lastInsight) return;
    lastInsight = content;
    const target = document.getElementById('insight');
    withMath(async () => {
      if (content !== lastInsight) return;
      MathJax.typesetClear([target]);
      target.textContent = content;
      target.dataset.special = String(special);
      await MathJax.typesetPromise([target]);
    });
  }

  /** Draw a crisp, uniformly scaled coordinate system and the selected graph. */
  function draw() {
    drawingFrame = 0;
    if (!ready) return;
    const width = plot.clientWidth, height = plot.clientHeight;
    if (width <= 0 || height <= 0) return;
    const padding = Math.min(45, width * 0.12);
    const scale = (height - 2 * padding) / state.span;
    const xLimit = (width / 2 - padding) / scale, yLimit = state.span / 2;
    const step = core.gridStep(state.span, Math.max(4, (height - 2 * padding) / 55));
    const x = value => width / 2 + value * scale;
    const y = value => height / 2 - value * scale;
    const lines = [], labels = [];
    const line = (x1, y1, x2, y2, stroke, thickness = 1) => `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${stroke}" stroke-width="${thickness}"/>`;
    for (let i = Math.ceil(-xLimit / (step / 2)); i <= Math.floor(xLimit / (step / 2)); i++) {
      const value = i * step / 2;
      if (i) lines.push(line(x(value), padding, x(value), height - padding, i % 2 ? '#eff3f6' : '#dce6eb'));
      if (i && i % 2 === 0) labels.push(`<text x="${x(value)}" y="${y(0) + 23}" text-anchor="middle">${core.number(value)}</text>`);
    }
    for (let i = Math.ceil(-yLimit / (step / 2)); i <= Math.floor(yLimit / (step / 2)); i++) {
      const value = i * step / 2;
      if (i) lines.push(line(padding, y(value), width - padding, y(value), i % 2 ? '#eff3f6' : '#dce6eb'));
      if (i && i % 2 === 0) labels.push(`<text x="${x(0) - 9}" y="${y(value) + 5}" text-anchor="end">${core.number(value)}</text>`);
    }
    const graph = core.graphPath(state.type, state.parameters[state.type], {width, height, span: state.span, padding});
    plot.setAttribute('viewBox', `0 0 ${width} ${height}`);
    plot.setAttribute('aria-label', `${titles[state.type]}. ${Object.entries(state.parameters[state.type]).map(([key, value]) => `${key} = ${core.number(value)}`).join('; ')}.`);
    plot.innerHTML = `<title>${titles[state.type]}</title><defs><clipPath id="graph-clip"><rect x="${padding}" y="${padding}" width="${width - 2 * padding}" height="${height - 2 * padding}"/></clipPath><marker id="axis-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3" orient="auto"><path d="M0 0 L6 3 L0 6" fill="none" stroke="#516a7a" stroke-width="1.1"/></marker></defs>
      ${lines.join('')}
      <path d="M${padding - 7} ${y(0)} H${width - padding + 9}" stroke="#516a7a" stroke-width="1.4" fill="none" marker-end="url(#axis-arrow)"/>
      <path d="M${x(0)} ${height - padding + 7} V${padding - 9}" stroke="#516a7a" stroke-width="1.4" fill="none" marker-end="url(#axis-arrow)"/>
      ${labels.join('')}<text x="${x(0) - 9}" y="${y(0) + 23}" text-anchor="end">0</text>
      <text class="axis-label" x="${width - padding + 13}" y="${y(0) - 9}">x</text><text class="axis-label" x="${x(0) + 12}" y="${padding - 10}">y</text>
      <path id="function-curve" d="${graph}" fill="none" stroke="#0a7b80" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" clip-path="url(#graph-clip)"/>`;
    document.getElementById('zoom-in').disabled = locked || state.span <= 2;
    document.getElementById('zoom-out').disabled = locked || state.span >= 80;
  }

  /** Coalesce geometry updates at browser-frame boundaries. */
  function requestDraw() {
    if (!drawingFrame) drawingFrame = requestAnimationFrame(draw);
  }

  /** Synchronize paired controls without replacing the active slider DOM. */
  function updateParameters() {
    for (const [key, value] of Object.entries(state.parameters[state.type])) {
      document.getElementById(`slider-${key}`).value = String(value);
      document.getElementById(`number-${key}`).value = String(value);
      document.getElementById(`slider-${key}`).setAttribute('aria-valuetext', `${key} = ${core.number(value)}`);
    }
    renderFormula();
    renderInsight();
    requestDraw();
  }

  /** Rebuild only the controls whose identities change with a different family. */
  function renderFamily() {
    root.dataset.type = state.type;
    document.querySelectorAll('[name="function-type"]').forEach(input => { input.checked = input.value === state.type; });
    document.getElementById('graph-heading').textContent = titles[state.type];
    const parameters = document.getElementById('parameters');
    MathJax.typesetClear?.([parameters]);
    parameters.innerHTML = Object.entries(core.SETTINGS[state.type]).map(([key, setting]) => `<div class="parameter">
      <div class="parameter-top"><label class="parameter-symbol" for="slider-${key}">\\(${key}\\)</label><input class="parameter-number" id="number-${key}" data-parameter="${key}" type="number" lang="en" min="${setting.min}" max="${setting.max}" step="${setting.step}" aria-label="${roles[key]} ${key}, Zahlenwert"></div>
      <input id="slider-${key}" data-parameter="${key}" type="range" min="${setting.min}" max="${setting.max}" step="${setting.step}" aria-label="${roles[key]} ${key}">
      <div class="parameter-bounds"><span>${core.number(setting.min)}</span><span>${core.number(setting.max)}</span></div></div>`).join('');
    withMath(async () => { await MathJax.typesetPromise([parameters]); });
    updateParameters();
    if (locked) parameters.querySelectorAll('input').forEach(input => { input.disabled = true; });
  }

  root.addEventListener('change', event => {
    if (!ready || locked) return;
    if (event.target.name === 'function-type') {
      state.type = event.target.value;
      renderFamily();
      if (!bridge) {
        try { history.replaceState(null, '', core.familyUrl(location.href, state.type)); } catch { /* File viewers may forbid history updates. */ }
      }
      document.getElementById('status').textContent = `${titles[state.type]} ausgewählt.`;
      document.getElementById('link-fallback').hidden = true;
      publish();
    }
    if (event.target.type === 'number' && event.target.dataset.parameter) {
      const key = event.target.dataset.parameter;
      const value = core.parameter(state.type, key, event.target.valueAsNumber);
      if (value !== null) state.parameters[state.type][key] = value;
      updateParameters();
      publish();
    }
  });

  root.addEventListener('input', event => {
    if (!ready || locked || event.target.type !== 'range') return;
    const key = event.target.dataset.parameter;
    state.parameters[state.type][key] = core.parameter(state.type, key, event.target.valueAsNumber);
    updateParameters();
    publish();
  });

  // Number inputs must leave wheel input to the surrounding page.
  root.addEventListener('wheel', event => { if (event.target.type === 'number') event.target.blur(); }, {passive: true});

  document.getElementById('reset-parameters').addEventListener('click', () => {
    if (!ready || locked) return;
    state.parameters[state.type] = core.createState(state.type).parameters[state.type];
    updateParameters(); publish();
  });
  for (const [id, transform] of [['zoom-in', value => Math.max(2, value / 1.5)], ['zoom-out', value => Math.min(80, value * 1.5)], ['reset-view', () => 10]]) {
    document.getElementById(id).addEventListener('click', () => {
      if (!ready || locked) return;
      state.span = transform(state.span);
      requestDraw(); publish();
    });
  }
  document.getElementById('copy-link').addEventListener('click', async () => {
    if (!ready || locked) return;
    const url = core.familyUrl(PUBLIC_URL, state.type);
    try {
      await navigator.clipboard.writeText(url);
      document.getElementById('status').textContent = 'Link kopiert.';
    } catch {
      document.getElementById('link-fallback').hidden = false;
      const field = document.getElementById('share-url');
      field.value = url; field.focus(); field.select();
      reportHeight();
    }
  });

  /** Apply a saved state, then an explicit standalone URL or fresh host activity. */
  async function initialize(restored) {
    if (ready || locked) return;
    try {
      const activity = bridge?.getModuleContext()?.activity;
      state = restored == null ? core.createState(activity) : core.validateState(restored);
      if (!bridge) {
        const requested = new URL(location.href).searchParams.get('type');
        if (core.TYPES.includes(requested)) state.type = requested;
      }
    } catch {
      fail('Der gespeicherte Stand ist ungültig. Er wurde nicht überschrieben.');
      return;
    }
    window.GGTypography.apply({'--size-small': -1, '--size-title': 2, '--size-formula': 1}, bridge);
    document.documentElement.dataset.presentation = bridge?.getModuleContext()?.presentation || 'full';
    document.documentElement.dataset.embedded = String(Boolean(bridge));
    await withMath(async () => { await MathJax.typesetPromise([root]); });
    if (locked) return;
    ready = true;
    notice.textContent = '';
    renderFamily();
  }

  if (bridge) {
    bridge.setSnapshotProvider(snapshot);
    bridge.subscribeState(initialize);
    if (bridge.isInitialized()) initialize(bridge.getState());
    window.addEventListener('message', () => {
      if (ready && !bridge.isEnabled()) fail('Der Host hat Änderungen gesperrt. Der bisherige Stand bleibt erhalten.');
    });
  } else {
    let restored = null;
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved) restored = JSON.parse(saved);
    } catch (error) {
      if (error instanceof SyntaxError) { fail('Der gespeicherte Stand ist ungültig. Er wurde nicht überschrieben.'); return; }
    }
    initialize(restored);
  }
  new ResizeObserver(() => { requestDraw(); reportHeight(); }).observe(document.body);
  new ResizeObserver(requestDraw).observe(plot);
})();
