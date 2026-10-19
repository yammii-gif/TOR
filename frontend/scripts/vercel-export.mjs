import { cpSync, existsSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { tmpdir } from 'node:os';
import { basename, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

// Export a disposable copy: the regular Next.js proxy and build stay intact.
const root = dirname(dirname(fileURLToPath(import.meta.url)));
const temporary = mkdtempSync(join(tmpdir(), 'renal-vercel-export-'));
const skip = new Set(['node_modules', '.next', 'out', '.browsers', 'test-results', 'playwright-report']);
try {
  cpSync(root, temporary, { recursive: true, filter: path => !skip.has(basename(path)) });
  symlinkSync(join(root, 'node_modules'), join(temporary, 'node_modules'), 'dir');
  rmSync(join(temporary, 'app', 'api'), { recursive: true, force: true });
  writeFileSync(join(temporary, 'next.config.mjs'), "export default { output: 'export' };\n");
  execFileSync(process.execPath, [join(root, 'node_modules/next/dist/bin/next'), 'build', temporary], {
    stdio: 'inherit',
    env: { ...process.env, NEXT_PUBLIC_SERVERLESS_DEMO: 'true', NEXT_TELEMETRY_DISABLED: '1' },
  });
  if (!existsSync(join(temporary, 'out', 'index.html'))) throw Error('Static export missing index.html');
  rmSync(join(root, 'out'), { recursive: true, force: true });
  cpSync(join(temporary, 'out'), join(root, 'out'), { recursive: true });
} finally {
  rmSync(temporary, { recursive: true, force: true });
}
