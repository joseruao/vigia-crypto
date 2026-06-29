# Devil's Advocate — versão desktop local (privada)

App de ambiente de trabalho que corre **tudo na máquina**: a UI, o backend e o modelo
(via **Ollama**). Nenhum documento sai do computador — pensado para sigilo profissional.
Reaproveita o frontend e o backend do projeto; a versão cloud (OpenAI, para o advogado
testar) não é afetada.

> **Fase 1 (este README): modo dev** — prova que o motor local + Ollama funciona dentro
> da app. **Fase 2 (a seguir): instalador `.exe` de 1 clique** (PyInstaller + electron-builder)
> para entregar sem instalar Python/Node.

## Pré-requisitos (uma vez)

1. **Ollama** instalado e um modelo descarregado:
   ```
   ollama pull llama3.2:1b
   ```
   (PC fraco → `1b`. Se aguentar, `llama3.2:3b` dá melhor qualidade.)
2. **Dependências do backend** instaladas (já as tens do projeto):
   ```
   cd backend
   pip install -r requirements.txt
   ```
3. **Dependências do frontend**:
   ```
   cd frontend
   npm install
   ```

## Arrancar (modo dev)

```
cd desktop
npm install      # só a primeira vez (instala o Electron)
npm start
```

Isto arranca o backend (porta 8000), o frontend (porta 3000) e abre a janela em `/devil`.
Na página, o **código de acesso é `local`**. Faz upload de um PDF/DOCX → a análise corre
no Ollama, na tua máquina.

### Mudar de modelo
Define a variável antes do `npm start` (ou edita o default em `main.js`):
```
set DEVILS_ADVOCATE_MODEL=llama3.2:3b   &&  npm start    # Windows (cmd)
```

## Notas honestas
- **Qualidade:** o modelo local é bastante mais fraco que o gpt-5.5 da versão cloud. Esta
  versão resolve **privacidade**, não qualidade.
- **Recursos:** em modo dev correm em simultâneo o Next (compilador), o Electron, o uvicorn
  e o Ollama — pesado para 8 GB de RAM. O `.exe` final (Fase 2) será bem mais leve porque o
  frontend vai pré-compilado (sem o compilador do Next a correr).
- O modelo corre na GPU (NVIDIA) automaticamente se o Ollama detetar CUDA.

## Fase 2 (por fazer)
- Empacotar o backend Python num executável (PyInstaller) lançado como sidecar.
- Build estático do frontend (`next build`/export) servido pela app.
- `electron-builder` → instalador `.exe`.
- Remover a fricção do código de acesso na versão local (é local, 1 utilizador).
