#!/usr/bin/env node
// Verify that the same HTML a browser will render actually builds its timeline.
// Playwright is optional for the standalone skill; snap.py also checks pixels.
import { createRequire } from 'node:module';
import { dirname, extname, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import { constants, existsSync, lstatSync, writeFileSync } from 'node:fs';
import { lstat, open, realpath } from 'node:fs/promises';
import { createServer } from 'node:http';

const here = dirname(fileURLToPath(import.meta.url));
const project = process.argv[2];
const report = process.argv[3];
if (!project) { console.error('usage: browser_preflight.mjs <project> [report.json]'); process.exit(1); }

const require = createRequire(import.meta.url);
let chromium;
for (const name of ['playwright']) {
  try { chromium = require(name).chromium; break; } catch { /* try the next installed package */ }
}
if (!chromium) {
  console.error('PLAYWRIGHT_UNAVAILABLE: install Playwright Chromium for browser preflight; snapshot pixel checks still run');
  process.exit(2);
}

let browser, server;
try {
  const hf = resolve(project, 'hf');
  const index = resolve(hf, 'index.html');
  if (!existsSync(index)) throw new Error(`missing ${index}`);
  if (lstatSync(hf).isSymbolicLink()) throw new Error('hf directory must not be a symbolic link');
  const hfReal = await realpath(hf);
  const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.woff2': 'font/woff2',
    '.ttf': 'font/ttf', '.mp4': 'video/mp4', '.webm': 'video/webm', '.png': 'image/png',
    '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml' };
  server = createServer(async (request, response) => {
    let name;
    try { name = resolve(hf, '.' + decodeURIComponent(new URL(request.url, 'http://localhost').pathname)); }
    catch { response.writeHead(400).end(); return; }
    if (name === hf || !name.startsWith(hf + sep)) { response.writeHead(403).end(); return; }
    try {
      // Reject every symlink component, including a link that still resolves
      // inside hf. The realpath check is a second boundary against escapes.
      let component = hf;
      for (const part of relative(hf, name).split(sep)) {
        component = resolve(component, part);
        if ((await lstat(component)).isSymbolicLink()) { response.writeHead(403).end(); return; }
      }
      const actual = await realpath(name);
      if (!actual.startsWith(hfReal + sep)) { response.writeHead(403).end(); return; }
      const handle = await open(name, constants.O_RDONLY | constants.O_NOFOLLOW);
      let data;
      try {
        if (!(await handle.stat()).isFile()) { response.writeHead(403).end(); return; }
        data = await handle.readFile();
      } finally { await handle.close(); }
      // Check again after reading, before sending bytes to the browser.
      if ((await realpath(name)) !== actual) { response.writeHead(403).end(); return; }
      response.writeHead(200, { 'Content-Type': mime[extname(name)] || 'application/octet-stream' }).end(data);
    } catch (error) {
      response.writeHead(error?.code === 'ENOENT' ? 404 : 403).end();
    }
  });
  await new Promise((ok, fail) => server.listen(0, '127.0.0.1', ok).once('error', fail));
  const origin = `http://127.0.0.1:${server.address().port}`;
  browser = await chromium.launch({ headless: true, args: ['--disable-background-networking', '--disable-component-update'] });
  const context = await browser.newContext({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1, serviceWorkers: 'block' });
  const blocked = new Set();
  const networkOrigin = (url) => { try { return new URL(url).origin; } catch { return '<invalid>'; } };
  await context.route('**/*', (route) => {
    const url = route.request().url();
    if (networkOrigin(url) === origin) return route.continue();
    blocked.add(networkOrigin(url));
    return route.abort('blockedbyclient');
  });
  await context.routeWebSocket('**/*', (route) => {
    blocked.add(networkOrigin(route.url()));
    route.close();
  });
  const page = await context.newPage();
  await page.addInitScript(() => { window.__timelines = window.__timelines || {}; });
  const errors = [], forbidden = [];
  page.on('pageerror', (error) => errors.push(error.message.replace(/https?:\/\/[^\s"'<>]+/g, '[url redacted]')));
  page.on('response', (response) => {
    if (response.status() === 403 && networkOrigin(response.url()) === origin) forbidden.push(new URL(response.url()).pathname);
  });
  await page.goto(`${origin}/index.html`, { waitUntil: 'load', timeout: 15000 });
  await page.evaluate(() => document.fonts.ready);
  let ready = false;
  for (let attempt = 0; attempt < 100; attempt++) {
    if (errors.length || forbidden.length || blocked.size) break;
    ready = await page.evaluate(() => Boolean(window.__timelines?.main));
    if (ready) break;
    await page.waitForTimeout(100);
  }
  if (forbidden.length) throw new Error(`hf asset denied (symlink or path escape): ${forbidden.join(', ')}`);
  if (blocked.size) throw new Error(`external browser network request blocked: ${[...blocked].join(', ')}`);
  if (errors.length) throw new Error(`browser pageerror before timeline: ${errors.join(' | ')}`);
  if (!ready) throw new Error('browser timeline main was not created within 10 s; inspect the composition JavaScript');
  const result = await page.evaluate(() => ({
    timeline_ready: Boolean(window.__timelines?.main),
    captions: [...document.querySelectorAll('.cap')].map((cap) => {
      const content = cap.querySelector('.cap-in');
      const nodes = [content, ...content.querySelectorAll('.serif,.sans,.ln')];
      const rect = content.getBoundingClientRect();
      return {
        id: cap.id,
        dom_text_box_px: [rect.left, rect.top, rect.right, rect.bottom].map((v) => Math.round(v)),
        dom_min_font_px: Math.round(Math.min(...nodes.map((node) => parseFloat(getComputedStyle(node).fontSize))) * 10) / 10,
      };
    }),
  }));
  if (report) writeFileSync(report, JSON.stringify(result, null, 2));
  console.log(`browser preflight: timeline ready, ${result.captions.length} caption layouts measured`);
} catch (error) {
  const message = String(error?.message ?? error);
  if (/Executable doesn't exist|browserType\.launch:.*not found/.test(message)) {
    console.error(`PLAYWRIGHT_UNAVAILABLE: ${message}`);
    process.exitCode = 2;
  } else {
    console.error(`browser preflight failed: ${message}`);
    process.exitCode = 1;
  }
} finally {
  if (browser) await browser.close();
  if (server) await new Promise((ok) => server.close(ok));
}
