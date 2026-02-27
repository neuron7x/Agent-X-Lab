import { mkdir } from 'node:fs/promises';

try {
  await mkdir('dist', { recursive: true });
} catch (error) {
  console.error('Failed to create dist directory:', error);
  process.exit(1);
}
