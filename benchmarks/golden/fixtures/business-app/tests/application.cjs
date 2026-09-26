const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
test('database-backed customer create, read and update', async (t) => {
  const database = '.test-site.sqlite';
  fs.rmSync(database, { force: true });
  const process = spawn('python', ['server.py'], {
    env: { ...global.process.env, SITE_PORT: '18080', SITE_DATABASE_PATH: database },
    stdio: ['ignore', 'ignore', 'pipe']
  });
  let errors = '';
  process.stderr.on('data', value => { errors += value; });
  t.after(async () => {
    if (process.exitCode === null) { const closed = once(process, 'exit'); process.kill(); await closed; }
    fs.rmSync(database, { force: true });
  });
  const origin = 'http://127.0.0.1:18080';
  let ready = false;
  for (let i = 0; i < 100; i++) {
    try { ready = (await fetch(origin + '/health')).ok; } catch {}
    if (ready || process.exitCode !== null) break;
    await new Promise(resolve => setTimeout(resolve, 50));
  }
  assert.ok(ready, errors);
  const create = await fetch(origin + '/api/customers', { method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: 'Round trip', email: 'roundtrip@example.invalid' }) });
  assert.equal(create.status, 201);
  const customer = await create.json();
  assert.equal((await (await fetch(origin + '/api/customers/' + customer.id)).json()).name, 'Round trip');
  const update = await fetch(origin + '/api/customers/' + customer.id, { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: 'Updated' }) });
  assert.equal(update.status, 200);
  assert.equal((await (await fetch(origin + '/api/customers/' + customer.id)).json()).name, 'Updated');
});
