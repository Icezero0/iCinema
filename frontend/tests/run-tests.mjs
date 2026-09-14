import { build } from 'esbuild';
import { mkdir } from 'node:fs/promises';
import { spawnSync } from 'node:child_process';
import path from 'node:path';

const output = path.resolve('node_modules/.cache/icinema-tests/review.test.mjs');
await mkdir(path.dirname(output), { recursive: true });
await build({
  entryPoints: ['tests/review.test.ts'], outfile: output,
  bundle: true, platform: 'node', format: 'esm',
  packages: 'external', alias: { '@': path.resolve('src') },
  define: { 'import.meta.env': '{}' },
});
const result = spawnSync(process.execPath, ['--test', output], { stdio: 'inherit' });
process.exitCode = result.status ?? 1;
