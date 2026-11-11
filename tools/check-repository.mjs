// Hardware-free repository integrity checks. Run from any working directory.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { execFileSync } from 'node:child_process';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const git = (...args) => execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trimEnd();
const baseline = 'fb5bacc011ee3c99ed0cc3078a8081b49bfce029';
const files = [...new Set(git('ls-files', '--cached', '--others', '--exclude-standard', '-z').split('\0'))]
  .filter(name => name && fs.existsSync(path.join(root, name)));
const errors = [];
const fail = message => errors.push(message);
const read = name => fs.readFileSync(path.join(root, name), 'utf8');

for (const name of files) {
  if (/(^|\/)(node_modules|__pycache__|\.venv|\.cache|build|dist)\//.test(name) || /\.(pyc|tmp|bak)$/.test(name))
    fail(`Generated file tracked: ${name}`);
  if (!/\.(md|py|ino|h|yml|yaml|toml|js|mjs|html|css|service|txt)$/.test(name)) continue;
  const text = read(name);
  // Report paths only: never print a possible credential value.
  if (/(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)/.test(text))
    fail(`Possible credential in ${name}`);
  if (!name.startsWith('archive/') && name !== 'docs/AUDIT.md' && name !== 'tools/check-repository.mjs' &&
      /Dev\/Quadruped107-connect|Design\/|docs\/(architecture|validation)\.md/.test(text))
    fail(`Obsolete active path in ${name}`);
  if (!name.endsWith('.md')) continue;
  for (const match of text.matchAll(/!?\[[^\]]*\]\((<[^>]+>|[^\n)]+)\)/g)) {
    let target = match[1].replace(/^<|>$/g, '').replace(/\s+"[^"]*"$/, '');
    if (/^(https?:|mailto:|#)/.test(target)) continue;
    target = decodeURIComponent(target.split('#')[0]);
    const resolved = path.resolve(root, path.dirname(name), target);
    if (!fs.existsSync(resolved)) fail(`Broken link in ${name}: ${target}`);
  }
}

const oldEntries = git('ls-tree', '-r', baseline).split('\n');
let preserved = 0;
for (const line of oldEntries) {
  const match = line.match(/^\d+ blob ([a-f0-9]+)\t(.+)$/);
  if (!match) continue;
  const [, sha, oldName] = match;
  let newName;
  if (oldName.startsWith('Design/STL/')) newName = oldName.replace('Design/STL/', 'hardware/stl/');
  else if (oldName === 'Design/STL_Final.zip') newName = 'hardware/stl/STL_Final.zip';
  else if (oldName.startsWith('Design/')) newName = oldName.replace('Design/', 'hardware/cad/');
  else if (oldName.startsWith('Dev/Tools/') && oldName.endsWith('.xlsx')) newName = oldName.replace('Dev/Tools/', 'hardware/calibration/');
  else if (oldName.startsWith('docs/images/') || oldName.endsWith('.mp4') || oldName === 'LICENSE') newName = oldName;
  // Active command firmware evolves; retain strict byte preservation for gait data.
  // The historical sketch remains available at baseline in Git history.
  else if (oldName.startsWith('Dev/Quadruped107-connect/sketch/') && oldName.endsWith('/motion.h')) newName = oldName.replace('Dev/Quadruped107-connect/sketch/', 'firmware/uno/sketch/');
  else if (oldName.startsWith('Dev/Quadruped107-connect/assets/poses/')) newName = oldName.replace('Dev/Quadruped107-connect/assets/', 'software/pi/quadruped/web/');
  if (!newName) continue;
  if (!fs.existsSync(path.join(root, newName))) fail(`Missing preserved asset: ${newName}`);
  else if (git('hash-object', '--no-filters', '--', newName) !== sha) fail(`Changed preserved asset: ${newName}`);
  else preserved++;
}

const web = 'software/pi/quadruped/web';
for (const match of read(`${web}/index.html`).matchAll(/(?:src|href)="\/(?!api\/)([^"?#]+)"/g)) {
  if (!fs.existsSync(path.join(root, web, match[1]))) fail(`Missing web asset: ${match[1]}`);
}
for (const doc of ['PROJECT', 'ARCHITECTURE', 'HARDWARE', 'WIRING', 'SOFTWARE', 'PROTOCOL', 'SAFETY', 'ROADMAP', 'VALIDATION'])
  if (!files.includes(`docs/${doc}.md`)) fail(`Missing document: ${doc}`);
if (!read('deploy/quadruped107.service').includes('/.venv/bin/python -m quadruped.main')) fail('Deployment entry point mismatch');
const workflow = read('.github/workflows/validate.yml');
for (const target of ['software/pi/requirements-dev.txt', 'software/pi/quadruped/web/app.js', 'firmware/uno/sketch', 'tools/check-repository.mjs'])
  if (!workflow.includes(target)) fail(`CI missing expected target: ${target}`);

const duplicateGroups = new Map();
for (const name of files.filter(name => name.startsWith('hardware/stl/') && name.endsWith('.stl'))) {
  const hash = git('hash-object', '--no-filters', '--', name);
  duplicateGroups.set(hash, [...(duplicateGroups.get(hash) || []), name]);
}
const namedDuplicates = [...duplicateGroups.values()].filter(group => group.length > 1).length;
if (errors.length) {
  for (const error of errors) console.error(error);
  process.exitCode = 1;
} else console.log(`Repository checks passed: ${files.length} files, ${preserved} preserved blobs; ${namedDuplicates} intentional identical STL groups.`);
