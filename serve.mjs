import { spawn } from 'node:child_process';

const port = process.env.PORT || '10000';
const vite = spawn(process.execPath, ['frontend/node_modules/vite/bin/vite.js', 'preview', '--host', '0.0.0.0', '--port', port], { stdio: 'inherit' });

vite.on('exit', code => process.exit(code ?? 0));
process.on('SIGTERM', () => vite.kill('SIGTERM'));
process.on('SIGINT', () => vite.kill('SIGINT'));
