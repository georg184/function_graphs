/* Pure function models, bounded parameter state and plot geometry. */
(function (global) {
  'use strict';
  const VERSION = '20261027.064032';
  const VIEW_LIMITS = Object.freeze({minSpan: 0.05, maxSpan: 80, maxCenter: 10000});
  const TYPES = Object.freeze(['linear', 'quadratic', 'power']);
  const SETTINGS = Object.freeze({
    linear: Object.freeze({m: {min: -5, max: 5, step: 0.1, initial: 1}, q: {min: -10, max: 10, step: 0.1, initial: 0}}),
    quadratic: Object.freeze({a: {min: -5, max: 5, step: 0.1, initial: 1}, b: {min: -10, max: 10, step: 0.1, initial: 0}, c: {min: -10, max: 10, step: 0.1, initial: 0}}),
    power: Object.freeze({a: {min: -5, max: 5, step: 0.1, initial: 1}, n: {min: 1, max: 12, step: 1, initial: 3}, m: {min: 1, max: 12, step: 1, initial: 2}})
  });
  const DISPLAY = new Intl.NumberFormat('en-US', {useGrouping: false, maximumFractionDigits: 3});

  /** Format displayed values with a decimal point and without negative zero. */
  function number(value) {
    return DISPLAY.format(Math.abs(value) < 0.0005 ? 0 : value).replace('-', '−');
  }

  /** Return an independent, complete state with the requested initial family. */
  function createState(type = 'power') {
    return {schema: 3, comparison: false, type: TYPES.includes(type) ? type : 'power', parameters: Object.fromEntries(TYPES.map(kind => [kind,
      Object.fromEntries(Object.entries(SETTINGS[kind]).map(([key, setting]) => [key, setting.initial]))])), span: 10, center: {x: 0, y: 0}};
  }

  /** Validate every saved family, including controls that are currently hidden. */
  function validateState(value) {
    if (value?.schema === 1 || value?.schema === 2) return validateState(migrateState(value));
    if (!value || value.schema !== 3 || typeof value.comparison !== 'boolean' || !TYPES.includes(value.type) || !value.parameters || !Number.isFinite(value.span) || value.span < VIEW_LIMITS.minSpan || value.span > VIEW_LIMITS.maxSpan) throw new TypeError('Invalid function graph state');
    if (!value.center || !['x', 'y'].every(key => Number.isFinite(value.center[key]) && Math.abs(value.center[key]) <= VIEW_LIMITS.maxCenter)) throw new TypeError('Invalid graph viewport center');
    const state = createState(value.type);
    for (const type of TYPES) {
      for (const [key, setting] of Object.entries(SETTINGS[type])) {
        const actual = value.parameters[type]?.[key];
        if (!Number.isFinite(actual) || actual < setting.min || actual > setting.max || Math.abs(actual / setting.step - Math.round(actual / setting.step)) > 1e-7) throw new TypeError(`Invalid ${type}.${key}`);
        state.parameters[type][key] = actual;
      }
    }
    state.span = value.span;
    state.center = {x: value.center.x, y: value.center.y};
    state.comparison = value.comparison;
    return state;
  }

  /** Validate and upgrade exactly one legacy schema, retaining its original view. */
  function migrateState(value) {
    if (![1, 2].includes(value?.schema) || !Number.isFinite(value.span) || value.span < 2 || value.span > 80) throw new TypeError('Invalid legacy function graph state');
    const legacy = value.schema === 1 ? {...value, comparison: false,
      parameters: {...value.parameters, power: {...value.parameters?.power, m: SETTINGS.power.m.initial}}} : value;
    const current = validateState({...legacy, schema: 3, center: {x: 0, y: 0}});
    if (value.schema === 2) return current;
    const {center, ...intermediate} = current;
    return {...intermediate, schema: 2};
  }

  /** Project a viewport with the same scale on both coordinate axes.
   * Args:
   *   viewport: CSS dimensions, plot padding, vertical span and graph center.
   */
  function plotGeometry({width, height, span, padding, center = {x: 0, y: 0}}) {
    const scale = (height - 2 * padding) / span;
    const halfWidth = (width / 2 - padding) / scale;
    return {
      scale, xmin: center.x - halfWidth, xmax: center.x + halfWidth,
      ymin: center.y - span / 2, ymax: center.y + span / 2,
      x: value => width / 2 + (value - center.x) * scale,
      y: value => height / 2 - (value - center.y) * scale,
      point: (px, py) => ({x: center.x + (px - width / 2) / scale, y: center.y - (py - height / 2) / scale})
    };
  }

  /** Change scale around an invariant graph point, including at zoom limits.
   * Args:
   *   state: Valid current state, including span and center.
   *   factor: Positive multiplier; smaller values magnify the graph.
   *   anchor: Graph point to retain under the pointer, defaulting to the center.
   */
  function zoomViewport(state, factor, anchor = state.center) {
    if (!Number.isFinite(factor) || factor <= 0 || !Number.isFinite(anchor?.x) || !Number.isFinite(anchor?.y)) throw new TypeError('Invalid graph zoom');
    const span = Math.max(VIEW_LIMITS.minSpan, Math.min(VIEW_LIMITS.maxSpan, state.span * factor));
    if (span === state.span) return {span, center: {...state.center}};
    const ratio = span / state.span;
    const center = Object.fromEntries(['x', 'y'].map(key => [key,
      Math.max(-VIEW_LIMITS.maxCenter, Math.min(VIEW_LIMITS.maxCenter, anchor[key] + (state.center[key] - anchor[key]) * ratio))]));
    return {span, center};
  }

  /** Derive displayed curves from one shared coefficient and independent degrees. */
  function curves(state) {
    const parameters = state.parameters[state.type];
    const result = [{name: 'f', type: state.type, parameters}];
    if (state.type === 'power' && state.comparison) {
      result.push({name: 'g', type: 'power', parameters: {a: parameters.a, n: parameters.m}});
    }
    return result;
  }

  /** Clamp and snap a user control while leaving model and display rounding separate. */
  function parameter(type, key, value) {
    const setting = SETTINGS[type][key];
    if (!Number.isFinite(value)) return null;
    const snapped = Math.round(Math.min(setting.max, Math.max(setting.min, value)) / setting.step);
    return setting.step === 1 ? snapped : snapped / 10;
  }

  /** Evaluate the selected real polynomial without parsing or evaluating user code. */
  function evaluate(type, p, x) {
    if (type === 'linear') return p.m * x + p.q;
    if (type === 'quadratic') return (p.a * x + p.b) * x + p.c;
    if (type === 'power') return p.a * x ** p.n;
    throw new TypeError('Unknown function type');
  }

  /** Compose a simplified TeX polynomial; zero terms and unit factors are omitted. */
  function formula(type, p, name = 'f') {
    const terms = type === 'linear' ? [[p.m, 1], [p.q, 0]] : type === 'quadratic' ? [[p.a, 2], [p.b, 1], [p.c, 0]] : [[p.a, p.n]];
    let body = '';
    for (const [coefficient, exponent] of terms) {
      if (coefficient === 0) continue;
      const sign = coefficient < 0 ? '-' : body ? '+' : '';
      const magnitude = Math.abs(coefficient);
      const factor = exponent && magnitude === 1 ? '' : number(magnitude);
      const power = exponent === 0 ? '' : exponent === 1 ? 'x' : `x^{${exponent}}`;
      body += sign + factor + power;
    }
    return `${name}(x)=${body || '0'}`;
  }

  /** Choose readable grid spacing from the usual 1, 2, 5 sequence. */
  function gridStep(span, target = 10) {
    const raw = span / target;
    const power = 10 ** Math.floor(Math.log10(raw));
    const fraction = raw / power;
    return (fraction <= 1 ? 1 : fraction <= 2 ? 2 : fraction <= 5 ? 5 : 10) * power;
  }

  /** Sample a continuous graph densely, keeping off-screen SVG coordinates finite. */
  function graphPath(type, parameters, viewport) {
    const {width} = viewport;
    const geometry = plotGeometry(viewport);
    const samples = Math.min(2400, Math.max(240, Math.ceil(width) * 2));
    const commands = [];
    for (let i = 0; i <= samples; i++) {
      const x = geometry.xmin + (geometry.xmax - geometry.xmin) * i / samples;
      const y = evaluate(type, parameters, x);
      const px = geometry.x(x);
      const py = Math.max(-1e6, Math.min(1e6, geometry.y(y)));
      // These decimals are geometry serialization, never displayed quantities.
      commands.push(`${i ? 'L' : 'M'}${px.toFixed(3)},${py.toFixed(3)}`);
    }
    return commands.join(' ');
  }

  /** Produce one explicit, allowlisted family link, independent of stored state. */
  function familyUrl(base, type) {
    const url = new URL(base);
    url.searchParams.set('type', TYPES.includes(type) ? type : 'power');
    url.hash = '';
    return url.href;
  }

  const api = Object.freeze({VERSION, VIEW_LIMITS, TYPES, SETTINGS, number, createState, validateState, migrateState, plotGeometry, zoomViewport, curves, parameter, evaluate, formula, gridStep, graphPath, familyUrl});
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else global.FunctionGraphsCore = api;
})(typeof window === 'undefined' ? globalThis : window);
