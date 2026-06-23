import { spawn, ChildProcess } from 'child_process';
import fs from 'fs';
import path from 'path';
import http from 'http';

export interface PythonManagerOptions {
  appRoot: string;
  isPackaged: boolean;
}

function decodeOutput(data: Buffer): string {
  return data.toString('utf8');
}

export class PythonManager {
  private process: ChildProcess | null = null;
  private port: number | null = null;
  private readonly appRoot: string;
  private readonly isPackaged: boolean;

  constructor(options: PythonManagerOptions) {
    this.appRoot = options.appRoot;
    this.isPackaged = options.isPackaged;
  }

  get baseUrl(): string {
    if (!this.port) throw new Error('Python engine not started');
    return `http://127.0.0.1:${this.port}`;
  }

  private resolveEngineDir(): string {
    if (this.isPackaged) {
      return path.join(process.resourcesPath, 'engine');
    }
    return path.join(this.appRoot, 'engine');
  }

  private resolvePythonCommand(): string {
    const venvPython = path.join(this.appRoot, '.venv', 'Scripts', 'python.exe');
    if (fs.existsSync(venvPython)) return venvPython;
    return 'python';
  }

  private async pingHealth(): Promise<boolean> {
    if (!this.port) return false;
    try {
      const res = await fetch(`http://127.0.0.1:${this.port}/health`, {
        signal: AbortSignal.timeout(3000),
      });
      return res.ok;
    } catch {
      return false;
    }
  }

  async start(): Promise<number> {
    if (this.process && this.port && (await this.pingHealth())) {
      return this.port;
    }

    await this.stop();

    const engineDir = this.resolveEngineDir();
    const mainPy = path.join(engineDir, 'main.py');
    if (!fs.existsSync(mainPy)) {
      throw new Error(`Python engine not found: ${mainPy}`);
    }

    const port = await this.findFreePort();
    const python = this.resolvePythonCommand();
    const dataDir = path.join(this.appRoot, 'data');

    this.process = spawn(
      python,
      ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', String(port), '--timeout-keep-alive', '300'],
      {
        cwd: engineDir,
        env: {
          ...process.env,
          CHRONOS_DATA_DIR: dataDir,
          PYTHONUNBUFFERED: '1',
          PYTHONUTF8: '1',
          PYTHONIOENCODING: 'utf-8',
        },
        stdio: ['ignore', 'pipe', 'pipe'],
        windowsHide: true,
      }
    );

    this.port = port;

    this.process.stdout?.on('data', (data: Buffer) => {
      const text = decodeOutput(data).trim();
      if (text) console.log('[python]', text);
    });

    this.process.stderr?.on('data', (data: Buffer) => {
      const text = decodeOutput(data).trim();
      if (text) console.error('[python]', text);
    });

    this.process.on('exit', (code, signal) => {
      console.log('[python] exited', signal ? `signal ${signal}` : `code ${code}`);
      this.process = null;
      this.port = null;
    });

    await this.waitForHealth(30000);
    return port;
  }

  async ensureReady(): Promise<void> {
    await this.start();
  }

  async stop(): Promise<void> {
    if (this.process) {
      this.process.kill();
      this.process = null;
      this.port = null;
    }
  }

  private findFreePort(): Promise<number> {
    return new Promise((resolve, reject) => {
      const server = http.createServer();
      server.listen(0, '127.0.0.1', () => {
        const addr = server.address();
        if (!addr || typeof addr === 'string') {
          reject(new Error('Failed to get port'));
          return;
        }
        const port = addr.port;
        server.close(() => resolve(port));
      });
      server.on('error', reject);
    });
  }

  private waitForHealth(timeoutMs: number): Promise<void> {
    const start = Date.now();
    return new Promise((resolve, reject) => {
      const check = () => {
        if (!this.port) {
          reject(new Error('Engine stopped'));
          return;
        }
        http
          .get(`http://127.0.0.1:${this.port}/health`, (res) => {
            if (res.statusCode === 200) {
              resolve();
            } else if (Date.now() - start > timeoutMs) {
              reject(new Error('Python engine health check timeout'));
            } else {
              setTimeout(check, 300);
            }
          })
          .on('error', () => {
            if (Date.now() - start > timeoutMs) {
              reject(new Error('Python engine health check timeout'));
            } else {
              setTimeout(check, 300);
            }
          });
      };
      setTimeout(check, 500);
    });
  }

  async getHealth(): Promise<{ python: boolean; ollama: boolean; ollamaModel?: string; error?: string }> {
    try {
      await this.ensureReady();
      const res = await fetch(`${this.baseUrl}/health`);
      return (await res.json()) as { python: boolean; ollama: boolean; ollamaModel?: string; error?: string };
    } catch (err) {
      return { python: false, ollama: false, error: String(err) };
    }
  }
}
