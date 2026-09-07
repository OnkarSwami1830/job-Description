import { cp, rm } from 'node:fs/promises';
import { execSync } from 'node:child_process';

execSync('npm install --prefix frontend', { stdio: 'inherit' });
execSync('npm run build --prefix frontend', { stdio: 'inherit' });
await rm('dist', { recursive: true, force: true });
await cp('frontend/dist', 'dist', { recursive: true });
