const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '../..');
const script = fs.readFileSync(path.join(root, 'src/spg/web/experience.js'), 'utf8');
const start = script.indexOf('  // A live Turn streams over the existing SSE channel');
const end = script.indexOf('  const collectionInfo =');
const streaming = script.slice(start, end);

function harness({eventSource = true} = {}) {
  const sources = [], timers = [], refreshed = [];
  class FakeEventSource {
    constructor(url) { this.url = url; this.readyState = 1; this.listeners = {}; sources.push(this); }
    addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
    emit(name, data) { for (const fn of this.listeners[name] || []) fn({data: JSON.stringify(data)}); }
    close() { this.readyState = 2; this.closed = true; }
  }
  FakeEventSource.CLOSED = 2;
  const messages = {children: [], html: '', querySelector(sel) {
    if (sel === '[data-streaming-reply]') return this.children.find(c => c.streaming) || null;
    if (sel === '[role="status"]') return null;
    return null;
  }, appendChild(node) { this.children.push(node); }};
  const document = {createElement() {
    const node = {dataset: {}, className: '', set innerHTML(v) { this.text = {textContent: ''}; },
      querySelector() { return this.text; }};
    Object.defineProperty(node.dataset, 'streamingReply', {set() { node.streaming = true; }});
    return node;
  }};
  const context = {
    state: {routeEpoch: 1, timer: null}, document, location: {pathname: '/products/p/workspace'},
    $: sel => sel === '#workspace-messages' ? messages : null,
    setTimeout: (fn, ms) => { timers.push(ms); return timers.length; }, clearTimeout() {},
    encodeURIComponent, JSON,
    renderWorkspace: async () => refreshed.push('workspace'), renderHomeConversation: async () => refreshed.push('home'),
  };
  if (eventSource) context.EventSource = FakeEventSource;
  vm.createContext(context);
  vm.runInContext(streaming, context);
  return {context, sources, timers, refreshed, messages};
}

const live = {turns: [{id: 't1', status: 'PROCESSING'}]};

test('a live Turn opens one SSE stream instead of a 2.6 s poll', () => {
  const h = harness();
  h.context.scheduleConversationPoll('i1', live);
  h.context.scheduleConversationPoll('i1', live);
  assert.equal(h.sources.length, 1);
  assert.equal(h.sources[0].url, '/api/interactions/i1/turns/t1/events');
  assert.deepEqual(h.timers, []);
});

test('response deltas render incrementally and the final text replaces them', () => {
  const h = harness();
  h.context.scheduleConversationPoll('i1', live);
  const source = h.sources[0];
  source.emit('response.delta', {content: '你好'});
  source.emit('response.delta', {content: '，Watt'});
  const reply = h.messages.children.find(c => c.streaming);
  assert.equal(reply.text.textContent, '你好，Watt');
  source.emit('response.final', {content: '你好，Watt。'});
  assert.equal(reply.text.textContent, '你好，Watt。');
});

test('Turn completion closes the stream and re-reads the conversation once', () => {
  const h = harness();
  h.context.scheduleConversationPoll('i1', live);
  h.sources[0].emit('message.completed', {});
  assert.equal(h.sources[0].closed, true);
  assert.deepEqual(h.refreshed, ['workspace']);
});

test('no live Turn opens nothing; a stale route ignores late events', () => {
  const h = harness();
  h.context.scheduleConversationPoll('i1', {turns: [{id: 't1', status: 'COMPLETED'}]});
  assert.equal(h.sources.length, 0);
  h.context.scheduleConversationPoll('i1', live);
  h.context.state.routeEpoch = 2;
  h.sources[0].emit('message.completed', {});
  assert.deepEqual(h.refreshed, []);
});

test('polling remains only as the fallback without EventSource', () => {
  const h = harness({eventSource: false});
  h.context.scheduleConversationPoll('i1', live);
  assert.equal(h.sources.length, 0);
  assert.deepEqual(h.timers, [2600]);
});

const workStart = script.indexOf('  // Committed Work changes are pushed;');
const workEnd = script.indexOf('  async function renderWorkspaceConversation(id) {');
const workStreaming = script.slice(workStart, workEnd);

function workHarness() {
  const sources = [], renders = [];
  class FakeEventSource {
    constructor(url) { this.url = url; this.readyState = 1; this.listeners = {}; sources.push(this); }
    addEventListener(name, fn) { (this.listeners[name] ||= []).push(fn); }
    emit(name) { for (const fn of this.listeners[name] || []) fn({data: '{}'}); }
    close() { this.readyState = 2; this.closed = true; }
  }
  FakeEventSource.CLOSED = 2;
  let release;
  const context = {state: {routeEpoch: 1, timer: 7}, EventSource: FakeEventSource, encodeURIComponent,
    clearTimeout() {}, showNotice() {},
    renderWorkspace: (id) => { renders.push([id, context.state.pushedRender]); return new Promise(r => { release = r; }); }};
  vm.createContext(context);
  vm.runInContext(workStreaming, context);
  return {context, sources, renders, release: () => release()};
}

test('a Work is watched over one push stream that survives re-renders', () => {
  const h = workHarness();
  h.context.watchWork('p1', 'w1');
  h.context.watchWork('p1', 'w1');
  assert.equal(h.sources.length, 1);
  assert.equal(h.sources[0].url, '/api/experience/works/w1/events');
  h.sources[0].emit('work.ready');
  assert.equal(h.context.state.timer, null);
});

test('change bursts coalesce into one in-flight re-render plus one follow-up', async () => {
  const h = workHarness();
  h.context.watchWork('p1', 'w1');
  const source = h.sources[0];
  source.emit('work.changed'); source.emit('work.changed'); source.emit('work.changed');
  assert.equal(h.renders.length, 1);
  assert.equal(h.renders[0][1], true);
  h.release(); await new Promise(r => setImmediate(r));
  assert.equal(h.renders.length, 2);
});

test('a reconnected stream re-reads once to cover changes missed while down', () => {
  const h = workHarness();
  h.context.watchWork('p1', 'w1');
  const source = h.sources[0];
  source.emit('work.ready');
  assert.equal(h.renders.length, 0);
  source.onerror();
  source.emit('work.ready');
  assert.equal(h.renders.length, 1);
});

test('switching Work or leaving closes the previous stream', () => {
  const h = workHarness();
  h.context.watchWork('p1', 'w1');
  h.context.watchWork('p1', 'w2');
  assert.equal(h.sources[0].closed, true);
  h.context.closeWorkStream();
  assert.equal(h.sources[1].closed, true);
  assert.equal(h.context.state.workStream, null);
});

test('real stage progress shows before any reply text and never after it', () => {
  const h = harness();
  const statusLine = {textContent: '', dataset: {}, setAttribute() {}};
  h.messages.querySelector = sel => sel === '[data-turn-status]' ? (h.messages.statusShown ? statusLine : null)
    : sel === '[data-streaming-reply]' ? h.messages.children.find(c => c.streaming) || null : null;
  h.context.document.createElement = () => { h.messages.statusShown = true; return statusLine; };
  h.context.scheduleConversationPoll('i1', live);
  const source = h.sources[0];
  source.emit('turn.accepted', {});
  assert.equal(statusLine.textContent, '已收到，开始处理');
  source.emit('turn.progress', {metadata: {stage: 'UNDERSTANDING'}});
  assert.equal(statusLine.textContent, '正在理解你的需求');
  source.emit('turn.progress', {metadata: {stage: 'NOT_A_STAGE'}});
  assert.equal(statusLine.textContent, '正在理解你的需求');
});

test('stage copy states what Watt is doing, never what the Human meant', () => {
  const copy = vm.runInNewContext(`(${script.slice(script.indexOf('const turnStageCopy = '), script.indexOf('};', script.indexOf('const turnStageCopy = ')) + 2).replace('const turnStageCopy = ', '').replace(/;$/, '')})`);
  assert.deepEqual(Object.keys(copy).sort(), ['COMPOSING_REPLY', 'PREPARING_WORK', 'READING_CONTEXT', 'UNDERSTANDING', 'UNDERSTOOD']);
  for (const text of Object.values(copy)) assert.match(text, /^(正在|已理解)/);
});

test('a failed latest Turn is shown with its reason and a retry, not as the previous reply', () => {
  const start = script.indexOf('  function turnFailure(');
  const fn = script.slice(start, script.indexOf('\n', start));
  const esc = v => String(v).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
  const turnFailure = vm.runInNewContext(`${fn}; turnFailure`, {esc});
  const html = turnFailure('i1', {id: 't9', status: 'FAILED', failure_message: '模型结果未通过校验 <b>'});
  assert.match(html, /这一轮没有处理成功，你的消息已保存/);
  assert.match(html, /data-retry-turn="t9"/);
  assert.match(html, /data-retry-interaction="i1"/);
  assert.match(html, /&lt;b&gt;/);
  assert.match(script, /\/api\/interactions\/\$\{encodeURIComponent\(retry\.dataset\.retryInteraction\)\}\/turns\/\$\{encodeURIComponent\(retry\.dataset\.retryTurn\)\}\/retry/);
});
