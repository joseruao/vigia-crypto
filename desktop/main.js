// Devil's Advocate — desktop (Fase 1, modo dev).
// Arranca o backend Python (FastAPI) e o frontend (Next.js) existentes, aponta o
// backend para o Ollama local, e abre a UI numa janela. Reaproveita 100% do código
// do projeto — nada é reescrito. A versão cloud (advogado) fica intocada.

const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const http = require('http');
const path = require('path');

const ROOT = path.join(__dirname, '..');
const BACKEND_DIR = path.join(ROOT, 'backend');
const FRONTEND_DIR = path.join(ROOT, 'frontend');

const BACKEND_PORT = 8000; // o frontend (api.ts) aponta para localhost:8000 quando corre local
const FRONTEND_PORT = 3000;

const isWin = process.platform === 'win32';
const npmCmd = isWin ? 'npm.cmd' : 'npm';
const pyCmd = process.env.PYTHON || (isWin ? 'python' : 'python3');

// Config local: backend usa o Ollama na própria máquina, sem chamar a OpenAI.
const LOCAL_ENV = {
  ...process.env,
  DEVILS_ADVOCATE_BASE_URL: 'http://localhost:11434/v1',
  DEVILS_ADVOCATE_MODEL: process.env.DEVILS_ADVOCATE_MODEL || 'llama3.2:1b',
  // Local app = private, single user, no OpenAI cost — no access code needed.
  DEVILS_ADVOCATE_REQUIRE_ACCESS_CODE: 'false',
};

let backendProc = null;
let frontendProc = null;

function startBackend() {
  console.log('[desktop] a arrancar backend (uvicorn) na porta', BACKEND_PORT);
  backendProc = spawn(
    pyCmd,
    ['-m', 'uvicorn', 'Api.main:app', '--host', '127.0.0.1', '--port', String(BACKEND_PORT)],
    { cwd: BACKEND_DIR, env: LOCAL_ENV, stdio: 'inherit', shell: isWin }
  );
  backendProc.on('exit', (code) => console.log('[desktop] backend terminou:', code));
}

function startFrontend() {
  console.log('[desktop] a arrancar frontend (next dev) na porta', FRONTEND_PORT);
  frontendProc = spawn(npmCmd, ['run', 'dev'], {
    cwd: FRONTEND_DIR,
    env: process.env,
    stdio: 'inherit',
    shell: isWin,
  });
  frontendProc.on('exit', (code) => console.log('[desktop] frontend terminou:', code));
}

function waitForPort(port, onReady, triesLeft = 180) {
  const req = http.get({ host: '127.0.0.1', port, path: '/', timeout: 2000 }, (res) => {
    res.resume();
    onReady();
  });
  req.on('error', () => retry());
  req.on('timeout', () => {
    req.destroy();
    retry();
  });
  function retry() {
    if (triesLeft <= 0) {
      console.error('[desktop] timeout à espera da porta', port);
      return;
    }
    setTimeout(() => waitForPort(port, onReady, triesLeft - 1), 1000);
  }
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 900,
    title: "Devil's Advocate (local)",
    webPreferences: { contextIsolation: true },
  });
  // IMPORTANTE: carregar via "localhost" (não 127.0.0.1) — o api.ts só aponta
  // para o backend local quando o hostname é exatamente "localhost".
  win.loadURL(`http://localhost:${FRONTEND_PORT}/devil`);
}

app.whenReady().then(() => {
  startBackend();
  startFrontend();
  // O Next.js dev demora a compilar na primeira vez — esperamos pela porta antes de abrir.
  waitForPort(FRONTEND_PORT, createWindow);

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

function killChildren() {
  if (backendProc) try { backendProc.kill(); } catch (_) {}
  if (frontendProc) try { frontendProc.kill(); } catch (_) {}
}

app.on('window-all-closed', () => {
  killChildren();
  if (process.platform !== 'darwin') app.quit();
});
app.on('before-quit', killChildren);
process.on('exit', killChildren);
