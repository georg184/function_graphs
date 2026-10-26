'use strict';
const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const core = require('../js/core.js');

test('all three families evaluate independently, including degree-degenerate cases', () => {
  for (const x of [-5, -2, -1, 0, 0.5, 1, 3]) {
    assert.equal(core.evaluate('linear', {m: -2, q: 3}, x), 3 - 2 * x);
    assert.equal(core.evaluate('quadratic', {a: 2, b: -3, c: 1}, x), 2 * x * x - 3 * x + 1);
    assert.equal(core.evaluate('quadratic', {a: 0, b: 2, c: -1}, x), 2 * x - 1);
    assert.equal(core.evaluate('power', {a: 0, n: 12}, x) + 0, 0);
  }
});

test('all selectable degrees preserve their parity symmetry', () => {
  for (let n = 1; n <= 12; n++) for (const a of [-5, -0.1, 0.1, 5]) for (const x of [0.25, 1, 2]) {
    const right = core.evaluate('power', {a, n}, x);
    assert.equal(core.evaluate('power', {a, n}, -x), (n % 2 ? -1 : 1) * right);
  }
});

test('formulas omit zero terms and unit coefficients without losing signs or degree one', () => {
  assert.equal(core.formula('linear', {m: -1, q: 0}), 'f(x)=-x');
  assert.equal(core.formula('quadratic', {a: -1, b: 0.5, c: -2}), 'f(x)=-x^{2}+0.5x-2');
  assert.equal(core.formula('quadratic', {a: 0, b: 0, c: 0}), 'f(x)=0');
  assert.equal(core.formula('power', {a: 1, n: 1}), 'f(x)=x');
  assert.equal(core.formula('power', {a: -0.1, n: 12}), 'f(x)=-0.1x^{12}');
  assert.equal(core.number(-0.0000001), '0');
  assert.equal(core.number(1234.5), '1234.5');
});

test('state validation retains hidden family settings and rejects invalid degrees or coefficients', () => {
  const state = core.createState();
  state.parameters.linear.q = -7.3;
  state.parameters.power.n = 12;
  const restored = core.validateState(JSON.parse(JSON.stringify(state)));
  assert.deepEqual(restored, state);
  restored.parameters.linear.q = 0;
  assert.equal(state.parameters.linear.q, -7.3);
  for (const n of [0, 1.1, 13, NaN, Infinity, '2']) {
    const invalid = core.createState(); invalid.parameters.power.n = n;
    assert.throws(() => core.validateState(invalid));
  }
  const invalid = core.createState(); invalid.parameters.quadratic.a = 5.1;
  assert.throws(() => core.validateState(invalid));
  invalid.parameters.quadratic.a = 1;
  invalid.schema = 99;
  assert.throws(() => core.validateState(invalid));
});

test('comparison curves share a coefficient, retain independent degrees and reverse order with its sign', () => {
  const state = core.createState();
  assert.equal(core.curves(state).length, 1);
  state.comparison = true;
  for (const a of [-2, 0, 0.5]) {
    state.parameters.power.a = a;
    const [f, g] = core.curves(state);
    assert.equal(f.name, 'f');
    assert.equal(g.name, 'g');
    assert.equal(g.parameters.a, a);
    assert.equal(g.parameters.n, 2);
    assert.equal(f.parameters.n, 3);
    assert.equal(core.formula(g.type, g.parameters, g.name), a === 0 ? 'g(x)=0' : `g(x)=${a}x^{2}`);
    for (const x of [0, 0.5, 1, 2]) {
      const difference = core.evaluate(g.type, g.parameters, x) - core.evaluate(f.type, f.parameters, x);
      assert.equal(difference + 0, a * x ** 2 * (1 - x) + 0);
    }
  }
  state.parameters.power.m = state.parameters.power.n;
  const [f, g] = core.curves(state);
  const viewport = {width: 600, height: 400, span: 10, padding: 40};
  assert.equal(core.graphPath(f.type, f.parameters, viewport), core.graphPath(g.type, g.parameters, viewport));
  state.type = 'linear';
  assert.equal(core.curves(state).length, 1);
  assert.equal(state.parameters.linear.m, 1);
});

test('comparison state round-trips and rejects invalid hidden degrees and toggle values', () => {
  const state = core.createState('quadratic');
  state.comparison = true;
  state.parameters.power.m = 12;
  assert.deepEqual(core.validateState(JSON.parse(JSON.stringify(state))), state);
  for (const m of [0, 1.5, 13, '2', NaN]) {
    state.parameters.power.m = m;
    assert.throws(() => core.validateState(state));
  }
  state.parameters.power.m = 2;
  for (const comparison of [null, undefined, 1, 'true']) {
    state.comparison = comparison;
    assert.throws(() => core.validateState(state));
  }
});

test('schema one migrates without changing saved controls or accepting malformed old data', () => {
  const old = {schema: 1, type: 'power', span: 4,
    parameters: {linear: {m: -1.5, q: 3}, quadratic: {a: 2, b: -3, c: 1}, power: {a: -0.5, n: 11}}};
  const original = structuredClone(old);
  const migrated = core.migrateState(old);
  assert.equal(migrated.schema, 2);
  assert.equal(migrated.comparison, false);
  assert.deepEqual(migrated.parameters.power, {a: -0.5, n: 11, m: 2});
  assert.deepEqual(migrated.parameters.linear, old.parameters.linear);
  assert.deepEqual(migrated.parameters.quadratic, old.parameters.quadratic);
  assert.equal(migrated.span, 4);
  assert.deepEqual(core.validateState(old), migrated);
  assert.deepEqual(old, original);
  assert.throws(() => core.migrateState(migrated));
  delete old.parameters.power.n;
  assert.throws(() => core.migrateState(old));
});

test('control normalization keeps natural degrees and finite bounded decimal coefficients', () => {
  assert.equal(core.parameter('power', 'n', 3.5), 4);
  assert.equal(core.parameter('power', 'n', 0), 1);
  assert.equal(core.parameter('power', 'n', 100), 12);
  assert.equal(core.parameter('quadratic', 'b', -1.26), -1.3);
  assert.equal(core.parameter('power', 'a', NaN), null);
});

test('high degrees and maximum zoom spans generate finite clipped geometry', () => {
  for (const n of [1, 2, 11, 12]) for (const span of [2, 10, 80]) {
    const curve = core.graphPath('power', {a: -5, n}, {width: 900, height: 600, span, padding: 45});
    assert.ok(!/NaN|Infinity/.test(curve));
    assert.ok(curve.startsWith('M45.000,'));
    assert.ok(curve.includes('L450.000,300.000'));
  }
});

test('explicit links encode exactly the requested initial family', () => {
  for (const type of core.TYPES) {
    const url = new URL(core.familyUrl('https://example.org/app/?keep=yes#old', type));
    assert.equal(url.searchParams.get('type'), type);
    assert.equal(url.searchParams.get('keep'), 'yes');
    assert.equal(url.hash, '');
  }
  assert.equal(new URL(core.familyUrl('https://example.org/', 'invalid')).searchParams.get('type'), 'power');
});

test('every local entry asset carries the producer version and no service worker is registered', () => {
  const root = path.join(__dirname, '..');
  const html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
  const manifest = JSON.parse(fs.readFileSync(path.join(root, 'muweb/muweave-module.json')));
  assert.equal(manifest.version, core.VERSION);
  assert.ok(html.includes(`window.GG_APP_VERSION = '${core.VERSION}'`));
  for (const match of html.matchAll(/(?:href|src)="((?:css|js)\/[^\"]+)"/g)) assert.ok(match[1].endsWith(`?v=${core.VERSION}`), match[1]);
  assert.ok(!/serviceWorker/.test(fs.readFileSync(path.join(root, 'js/app.js'), 'utf8')));
});
