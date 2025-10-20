# backend/workers/daily/daily_worker_runner.py
import asyncio
import time
import logging
from datetime import datetime
import sys
import os

# Adicionar o diretório atual ao path
sys.path.append(os.path.dirname(__file__))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('daily_worker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DailyWorker")

class DailyWorkerRunner:
    def __init__(self):
        self.worker_start_time = None
        
    async def run_daily_worker(self):
        """Executa o worker diário com monitorização"""
        try:
            self.worker_start_time = datetime.now()
            logger.info("🚀 INICIANDO WORKER DIÁRIO DE HOLDINGS...")
            
            from daily_holdings_worker import main as holdings_main
            await holdings_main()
            
            execution_time = datetime.now() - self.worker_start_time
            logger.info(f"✅ WORKER DIÁRIO CONCLUÍDO - Tempo: {execution_time}")
            
        except Exception as e:
            logger.error(f"❌ ERRO CRÍTICO NO WORKER DIÁRIO: {e}")
            
    def health_check(self):
        """Verifica se o worker está saudável"""
        return {
            "status": "running" if self.worker_start_time else "stopped",
            "last_start": self.worker_start_time.isoformat() if self.worker_start_time else None,
            "uptime": str(datetime.now() - self.worker_start_time) if self.worker_start_time else None
        }

async def main():
    """Função principal com tratamento de erros robusto"""
    worker = DailyWorkerRunner()
    
    try:
        await worker.run_daily_worker()
    except KeyboardInterrupt:
        logger.info("⏹️ Worker interrompido pelo usuário")
    except Exception as e:
        logger.error(f"💥 Erro fatal: {e}")

if __name__ == "__main__":
    # Configurar event loop para Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main())