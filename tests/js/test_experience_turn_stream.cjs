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
