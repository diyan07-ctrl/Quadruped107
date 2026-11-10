// Syntax-only diagram validation; npm dependencies live in ignored build/mermaid.
import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { execFileSync } from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const require = createRequire(path.join(root, 'build/mermaid/package.json'));
const { JSDOM } = require('jsdom');
const dom = new JSDOM('<!doctype html><html><body></body></html>');
globalThis.window = dom.window;
globalThis.document = dom.window.document;
const { default: mermaid } = await import(pathToFileURL(require.resolve('mermaid')).href);
mermaid.initialize({ startOnLoad: false, securityLevel: 'strict' });
const names = execFileSync('git', ['ls-files', '--cached', '--others', '--exclude-standard', '-z'],
  {cwd: root, encoding: 'utf8'}).split('\0').filter(name => name.endsWith('.md'));
let count = 0;
for (const name of new Set(names)) {
  const filename = path.join(root, name);
  if (!fs.existsSync(filename)) continue;
  for (const match of fs.readFileSync(filename, 'utf8').matchAll(/```mermaid\r?\n([\s\S]*?)```/g)) {
    try { await mermaid.parse(match[1]); count++; }
    catch (error) { throw new Error(name + ': ' + error.message); }
  }
}
console.log('Mermaid syntax passed for ' + count + ' diagrams; no physical/layout verification implied.');
dom.window.close();
