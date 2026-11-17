// Build first. Requires Node 22+ and a locally installed Chrome; sends no API requests.
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { mkdtemp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join, extname, resolve } from 'node:path';
import { spawn } from 'node:child_process';
import assert from 'node:assert/strict';

const root = resolve('dist');
const config = JSON.parse(await readFile('vercel.json', 'utf8'));
const server = createServer(async (request, response) => {
  try {
    for (const { key, value } of config.headers[0].headers) response.setHeader(key, value);
    const path = new URL(request.url, 'http://localhost').pathname;
    const file = path.startsWith('/assets/') ? join(root, path) : join(root, 'index.html');
    const type = { '.js': 'text/javascript', '.css': 'text/css', '.html': 'text/html' }[extname(file)];
    response.setHeader('Content-Type', type || 'application/octet-stream');
    response.end(await readFile(file));
  } catch { response.writeHead(404); response.end(); }
});
await new Promise(resolve => server.listen(5189, '127.0.0.1', resolve));
const profile = await mkdtemp(join(tmpdir(), 'mahir-security-'));
const chrome = spawn(process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  ['--headless=new', '--disable-gpu', '--remote-debugging-port=9349', `--user-data-dir=${profile}`, 'about:blank'],
  { windowsHide: true, stdio: 'ignore' });
let socket;
try {
  let targets;
  for (let attempt = 0; attempt < 50; attempt++) {
    try { targets = await (await fetch('http://127.0.0.1:9349/json')).json(); break; }
    catch { await new Promise(resolve => setTimeout(resolve, 100)); }
  }
  assert.ok(targets, 'Chrome debugging endpoint did not start');
  socket = new WebSocket(targets.find(target => target.type === 'page').webSocketDebuggerUrl);
  await new Promise(resolve => socket.addEventListener('open', resolve, { once: true }));
  const pending = new Map(), exceptions = [];
  let next = 0, refreshRequests = 0;
  function command(method, params = {}) {
    return new Promise((resolve, reject) => {
      const id = ++next;
      pending.set(id, { resolve, reject }); socket.send(JSON.stringify({ id, method, params }));
    });
  }
  socket.addEventListener('message', async event => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const handler = pending.get(message.id); pending.delete(message.id);
      if (message.error) handler?.reject(message.error); else handler?.resolve(message.result);
    }
    if (message.method === 'Runtime.exceptionThrown') exceptions.push(message.params.exceptionDetails.text);
    if (message.method === 'Fetch.requestPaused') {
      const { requestId, request } = message.params;
      const path = new URL(request.url).pathname;
      if (path.includes('/refresh/')) refreshRequests++;
      const auth = path.includes('/auth/');
      const body = auth ? { detail: 'Invalid credentials.' } : path.includes('/public/') ? { store: {}, content: [], campaigns: [], locales: [], brands: [], reviews: [] } : { count: 0, results: [] };
      await command('Fetch.fulfillRequest', { requestId, responseCode: request.method === 'OPTIONS' ? 204 : auth ? 401 : 200,
        responseHeaders: [{ name: 'Content-Type', value: 'application/json' }, { name: 'Access-Control-Allow-Origin', value: '*' },
          { name: 'Access-Control-Allow-Headers', value: 'content-type,authorization' }, { name: 'Access-Control-Allow-Methods', value: 'GET,POST,OPTIONS' }],
        body: request.method === 'OPTIONS' ? '' : Buffer.from(JSON.stringify(body)).toString('base64') });
    }
  });
  await command('Page.enable'); await command('Runtime.enable');
  await command('Fetch.enable', { patterns: [{ urlPattern: 'https://sales-and-stock-management.onrender.com/*' }] });
  const evaluate = async expression => (await command('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true })).result.value;
  async function visit(path, expected) {
    await command('Page.navigate', { url: `http://127.0.0.1:5189${path}` });
    await new Promise(resolve => setTimeout(resolve, 250));
    for (let attempt = 0; attempt < 80; attempt++) {
      if (await evaluate(`document.body.innerText.includes(${JSON.stringify(expected)})`)) return;
      await new Promise(resolve => setTimeout(resolve, 100));
    }
    throw new Error(`Page ${path} did not render ${expected}`);
  }
  await visit('/login', 'Customer sign in');
  await visit('/signup', 'Create your customer account');
  await visit('/verify-email', 'Verify');
  await visit('/admin/login', 'Admin sign in');
  await visit('/showroom/login', 'Showroom sign in');
  await visit('/admin/products', 'Admin sign in');
  assert.equal(await evaluate('location.pathname'), '/admin/login');
  await visit('/showroom/stock', 'Showroom sign in');
  assert.equal(await evaluate('location.pathname'), '/showroom/login');
  await visit('/products', 'Admin sign in');
  await visit('/admin/login', 'Admin sign in');
  await evaluate(`localStorage.setItem('refresh_token', 'previous-session');
    for (const input of document.querySelectorAll('form input')) {
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, input.type === 'password' ? 'wrong-password' : 'wrong-user');
      input.dispatchEvent(new Event('input', { bubbles: true }));
    }`);
  await evaluate(`document.querySelector('form').requestSubmit()`);
  for (let attempt = 0; attempt < 50; attempt++) {
    if (await evaluate(`document.body.innerText.includes('Invalid credentials.')`)) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.ok(await evaluate(`document.body.innerText.includes('Invalid credentials.')`), await evaluate('document.body.innerText'));
  assert.equal(refreshRequests, 0, 'Failed login must not refresh an existing session');
  assert.deepEqual(exceptions, []);
  console.log('PASS: portal routes, legacy redirects, CSP rendering and failed-login refresh isolation. External API requests were mocked.');
} finally {
  socket?.close(); chrome.kill(); server.close();
  await new Promise(resolve => chrome.once('exit', resolve));
  await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
}
