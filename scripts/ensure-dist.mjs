import { mkdir } from 'node:fs/promises';

await mkdir('dist', { recursive: true });
