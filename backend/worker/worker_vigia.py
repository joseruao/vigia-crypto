# worker_vigia.py
import os
import time
import signal
import sys
import logging
from threading import Event

# Configurar logging detalhado para Debug
logging.basicConfig(
    level=logging.DEBUG,  # Mudado para DEBUG para ver tudo
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("VigiaWorker")

logger.info("🎯 WORKER INICIADO - DEBUG MODE")
logger.debug(f"Python path: {sys.path}")
logger.debug(f"Diretório atual: {os.getcwd()}")
logger.debug(f"Conteúdo do diretório: {os.listdir('.')}")

# Debug: tentar importar com mais informação
try:
    logger.info("🔍 Tentando importar vigia_solana_pro_supabase...")
    
    # Verificar se o ficheiro existe
    if os.path.exists("vigia_solana_pro_supabase.py"):
        logger.info("✅ Ficheiro vigia_solana_pro_supabase.py ENCONTRADO")
    else:
        logger.error("❌ Ficheiro vigia_solana_pro_supabase.py NÃO ENCONTRADO")
        logger.error(f"Ficheiros disponíveis: {os.listdir('.')}")
    
    from vigia_solana_pro_supabase import main as vigia_main
    logger.info("✅ Import do vigia_solana_pro_supabase BEM SUCEDIDO!")
    
except ImportError as e:
    logger.error(f"❌ ERRO DE IMPORT: {e}")
    logger.error("Tentando import alternativo...")
    
    # Tentativa alternativa
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("vigia_solana", "vigia_solana_pro_supabase.py")
        vigia_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(vigia_module)
        vigia_main = vigia_module.main
        logger.info("✅ Import alternativo BEM SUCEDIDO!")
    except Exception as e2:
        logger.error(f"❌ Import alternativo também falhou: {e2}")
        sys.exit(1)
        
except Exception as e:
    logger.error(f"❌ ERRO INESPERADO no import: {e}")
    sys.exit(1)

# Debug: verificar environment variables
logger.info("🔍 Verificando environment variables...")
required_vars = ["HELIUS_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY"]
for var in required_vars:
    value = os.getenv(var)
    if value:
        logger.info(f"✅ {var}: CONFIGURADA (primeiros 10 chars: {value[:10]}...)")
    else:
        logger.error(f"❌ {var}: NÃO CONFIGURADA")

class Worker:
    def __init__(self):
        self.shutdown_event = Event()
        self.interval = int(os.getenv("WORKER_INTERVAL", "900"))  # 15min default
        logger.info(f"🔄 Worker configurado com intervalo: {self.interval}s")
    
    def handle_signal(self, signum, frame):
        logger.info(f"📩 Recebido sinal {signum}, a encerrar graciosamente...")
        self.shutdown_event.set()
    
    def run_cycle(self):
        """Executa um ciclo de monitorização"""
        try:
            logger.info("🔍 Iniciando ciclo de monitorização...")
            logger.debug("Chamando vigia_main()...")
            
            # Executar o teu código principal
            vigia_main()
            
            logger.info("✅ Ciclo completado com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"❌ Erro no ciclo: {e}", exc_info=True)
            return False
    
    def run(self):
        """Loop principal do worker"""
        logger.info(f"👷 Worker INICIADO (intervalo: {self.interval}s)")
        
        # Configurar sinais para shutdown gracioso
        signal.signal(signal.SIGINT, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)
        
        cycle_count = 0
        
        while not self.shutdown_event.is_set():
            try:
                cycle_count += 1
                logger.info(f"🔄 Ciclo #{cycle_count} iniciando...")
                
                success = self.run_cycle()
                
                if success:
                    logger.info(f"✅ Ciclo #{cycle_count} completado com sucesso")
                else:
                    logger.warning(f"⚠️ Ciclo #{cycle_count} completado com erros")
                
                # Aguardar próximo ciclo ou shutdown
                logger.info(f"💤 Aguardando {self.interval}s para próximo ciclo...")
                waited = 0
                while waited < self.interval and not self.shutdown_event.is_set():
                    time.sleep(10)  # Verificar a cada 10s se precisa parar
                    waited += 10
                    if waited % 60 == 0:  # Log a cada minuto
                        logger.debug(f"⏰ Aguardando... {waited}/{self.interval}s")
                
            except Exception as e:
                logger.error(f"💥 Erro crítico no worker: {e}", exc_info=True)
                logger.info("😴 Aguardando 60s antes de continuar...")
                time.sleep(60)
        
        logger.info("🛑 Worker parado graciosamente")

if __name__ == "__main__":
    try:
        logger.info("🎬 Iniciando aplicação worker_vigia.py")
        worker = Worker()
        worker.run()
    except KeyboardInterrupt:
        logger.info("🛑 Worker interrompido pelo utilizador")
    except Exception as e:
        logger.error(f"💥 ERRO FATAL: {e}", exc_info=True)
        sys.exit(1)