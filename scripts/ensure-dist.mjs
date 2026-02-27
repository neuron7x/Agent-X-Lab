import { mkdir } from 'node:fs/promises';

try {
  await mkdir('dist', { recursive: true });
} catch (err) {
  console.error('ensure-dist failed:', err);
  process.exit(1);
}
