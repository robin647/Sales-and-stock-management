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
  let next = 0, refreshRequests = 0, savedOrder;
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
      const createTest = path.endsWith('/customers/create-test-account/');
      const facebookOrders = path.endsWith('/moderator/facebook-orders/');
      const createOrder = facebookOrders && request.method === 'POST';
      if (createOrder) savedOrder = { ...JSON.parse(request.postData), id: 1, created_at: '2026-11-19T00:00:00Z' };
      let body = { count: 0, results: [] };
      if (createTest) body = { id: 99, email: 'demo@example.test' };
      else if (auth) body = { detail: 'Invalid credentials.' };
      else if (path.endsWith('/accounts/me/')) body = { id: 1, role: 'admin', username: 'test-admin' };
      else if (path.includes('/public/')) body = { store: {}, content: [], campaigns: [], locales: [], brands: [], reviews: [] };
      else if (createOrder) body = savedOrder;
      else if (facebookOrders) body = savedOrder
        ? { count: 1, results: [{ ...savedOrder, delivery_charge: 150 }], summary: { orders: 1, units: savedOrder.quantity, cod: savedOrder.cod_amount, delivery: 150, net_sales: '2844.50' } }
        : { ...body, summary: { orders: 0, units: 0, cod: '0', delivery: 0, net_sales: '0' } };
      await command('Fetch.fulfillRequest', { requestId, responseCode: request.method === 'OPTIONS' ? 204 : auth ? 401 : (createTest || createOrder) ? 201 : 200,
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
  const adminToken = `x.${Buffer.from(JSON.stringify({ user_id: 1, role: 'admin', full_name: 'Test Admin' })).toString('base64url')}.x`;
  await evaluate(`localStorage.setItem('access_token', ${JSON.stringify(adminToken)})`);
  await visit('/admin/customers', 'Create test customer');
  await evaluate(`Array.from(document.querySelectorAll('button')).find(button => button.textContent === 'Create test customer').click()`);
  await evaluate(`for (const [index, input] of Array.from(document.querySelectorAll('[role="dialog"] input')).entries()) {
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(input, ['Demo Buyer', 'demo@example.test', 'Copper#Lake$947'][index]);
    input.dispatchEvent(new Event('input', { bubbles: true }));
  }`);
  await evaluate(`document.querySelector('[role="dialog"] form').requestSubmit()`);
  for (let attempt = 0; attempt < 50; attempt++) {
    if (await evaluate(`document.body.innerText.includes('Test customer demo@example.test created.')`)) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.ok(await evaluate(`document.body.innerText.includes('Test customer demo@example.test created.')`));
  await evaluate(`document.querySelector('[aria-controls="moderator-management-links"]').click();
    document.querySelector('#moderator-management-links a[href$="/facebook-orders"]').click();`);
  for (let attempt = 0; attempt < 50; attempt++) {
    if (await evaluate(`Boolean(document.querySelector('input[type=file]'))`)) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.ok(await evaluate(`Boolean(document.querySelector('input[type=file]'))`), 'Facebook Orders did not open from the sidebar');
  await evaluate(`(async () => {
    const canvas = document.createElement('canvas');
    canvas.width = 1000;
    canvas.height = 900;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = 'black';
    ctx.font = 'bold 36px Arial';
    ctx.fillText('Sample Store', 60, 75);
    ctx.fillText('120000001', 385, 160);
    ctx.fillRect(60, 185, 880, 4);
    ctx.fillRect(60, 420, 880, 4);
    ctx.font = '32px Arial';
    [['Invoice', '8'], ['SF-ID', '120000001'], ['Delivery', 'Home'], ['Weight', '0.5 KG']]
      .forEach(([label, value], i) => {
        ctx.fillText(label, 280, 235 + i * 50);
        ctx.textAlign = 'right';
        ctx.fillText(value, 940, 235 + i * 50);
        ctx.textAlign = 'left';
      });
    [['Name', 'Sample Buyer'], ['Phone', '01000000000'], ['Address', '15 Sample Road, Building 2'],
      ['', 'Near Sample Junction'], ['Area', 'Sylhet']].forEach(([label, value], i) => {
      ctx.fillText(label, 60, 475 + i * 49);
      ctx.fillText(value, 240, 475 + i * 49);
    });
    ctx.fillRect(60, 707, 880, 87);
    ctx.fillStyle = 'white';
    ctx.fillText('Cash on Delivery', 85, 763);
    ctx.fillText('৳ 2,994.50', 745, 763);
    const image = await new Promise(resolve => canvas.toBlob(resolve, 'image/png'));
    const transfer = new DataTransfer();
    transfer.items.add(new File([image], 'test-label.png', { type: 'image/png' }));
    const input = document.querySelector('input[type=file]');
    input.files = transfer.files;
    input.dispatchEvent(new Event('change', { bubbles: true }));
  })()`);
  for (let attempt = 0; attempt < 240; attempt++) {
    if (await evaluate(`!document.querySelector('input[type=file]').disabled`)) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.equal(await evaluate(`document.querySelector('[name="tracking_id"]').value`), '120000001', await evaluate('document.body.innerText'));
  assert.equal(await evaluate(`document.querySelector('[name="cod_amount"]').value`), '2994.50');
  assert.equal(await evaluate(`document.querySelector('[name="quantity"]').value`), '');
  assert.equal(await evaluate(`document.querySelector('[name="delivery_zone"]').value`), 'outside');
  await evaluate(`const quantity = document.querySelector('[name="quantity"]');
    Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(quantity, '2');
    quantity.dispatchEvent(new Event('input', { bubbles: true }));
    quantity.form.requestSubmit();`);
  for (let attempt = 0; attempt < 50 && !savedOrder; attempt++) await new Promise(resolve => setTimeout(resolve, 100));
  assert.equal(savedOrder?.customer_name, 'Sample Buyer');
  assert.equal(savedOrder?.phone, '01000000000');
  assert.match(savedOrder?.address, /15 Sample Road.*Near Sample Junction/);
  assert.equal(savedOrder?.area, 'Sylhet');
  assert.equal(savedOrder?.delivery_zone, 'outside');
  assert.equal(savedOrder?.invoice, '8');
  assert.equal(savedOrder?.quantity, '2');
  for (let attempt = 0; attempt < 50; attempt++) {
    if (await evaluate(`document.querySelector('[aria-label="All Facebook order totals"]').textContent.includes('2,994.50')`)) break;
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  assert.ok(await evaluate(`document.querySelector('[aria-label="All Facebook order totals"]').textContent.includes('2,994.50')`));
  assert.ok(await evaluate(`document.querySelector('[aria-label="All Facebook order totals"]').textContent.includes('2,844.50')`));
  assert.deepEqual(exceptions, []);
  console.log('PASS: portal routes, legacy redirects, CSP rendering, login-refresh isolation and Facebook order image intake. External API requests were mocked.');
} finally {
  socket?.close(); chrome.kill(); server.close();
  await new Promise(resolve => chrome.once('exit', resolve));
  await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
}
