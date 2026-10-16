const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const script = fs.readFileSync(path.resolve(__dirname, '../../src/spg/web/login-prefill.js'), 'utf8');

function harness(fetch) {
  const input = {value: '', isConnected: true};
  const form = {elements: {namedItem: () => input}};
  const window = {};
  vm.runInNewContext(script, {window, fetch});
  return {input, form, prefill: window.WattLogin.prefill};
}

test('prefill fills the input as text without submitting or caching', async () => {
  const token = 'credential-with-"<&-characters';
  const h = harness(async (url, options) => {
    assert.equal(url, '/auth/login-prefill');
    assert.equal(options.cache, 'no-store');
    assert.equal(options.credentials, 'same-origin');
    return {ok: true, json: async () => ({token})};
  });
  await h.prefill(h.form);
  assert.equal(h.input.value, token);
});

test('unavailable or disabled prefill leaves manual entry available', async () => {
  for (const fetch of [async () => ({ok: true, json: async () => ({token: null})}),
    async () => ({ok: false}), async () => { throw new Error('offline'); }]) {
    const h = harness(fetch);
    await h.prefill(h.form);
    assert.equal(h.input.value, '');
  }
});

test('a delayed prefill never replaces typed input or fills a removed form', async () => {
  for (const change of [input => {input.value = 'typed';}, input => {input.isConnected = false;}]) {
    let resolve;
    const h = harness(() => new Promise(r => {resolve = r;}));
    const pending = h.prefill(h.form);
    change(h.input);
    resolve({ok: true, json: async () => ({token: 'configured'})});
    await pending;
    assert.notEqual(h.input.value, 'configured');
  }
});
