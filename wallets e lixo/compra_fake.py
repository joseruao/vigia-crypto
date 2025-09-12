# trading_hold.py - Sistema de hold com take profits parciais
import time
import random
from datetime import datetime, timedelta

# ============================
# ESTRATÉGIA DE HOLD
# ============================
ESTRATEGIA = {
    "take_profit_1": 2.0,    # Vender 25% a 2x
    "take_profit_2": 5.0,    # Vender 25% a 5x
    "take_profit_3": 10.0,   # Vender 25% a 10x
    "stop_loss": 0.7,        # Stop loss a -30%
    "hold_remanescente": 0.25, # Manter 25% para moonbag
    "monitorizar_sem_vender": True  # Só alertar, não vender auto
}

# ============================
# GESTÃO DE POSIÇÕES
# ============================
posicoes_ativas = {}

def abrir_posicao(token_info, amount_sol):
    """Abre uma posição para hold a longo prazo"""
    posicao_id = f"hold_{int(time.time())}_{token_info['token']}"
    
    posicao = {
        "id": posicao_id,
        "token": token_info['token'],
        "mint": token_info['mint'],
        "investimento_total": amount_sol,
        "quantidade_total": amount_sol / random.uniform(0.001, 0.01),
        "preco_entrada": random.uniform(0.001, 0.01),
        "timestamp_entrada": datetime.now(),
        "exchange": token_info['exchange'],
        "vendido_1": False,  # Take profit 1
        "vendido_2": False,  # Take profit 2  
        "vendido_3": False,  # Take profit 3
        "stop_loss_atingido": False,
        "estado": "ativa"
    }
    
    posicoes_ativas[posicao_id] = posicao
    return posicao

def monitorizar_posicoes():
    """Monitoriza posições e alerta para take profits"""
    alertas = []
    
    for posicao_id, posicao in list(posicoes_ativas.items()):
        # Simular preço atual (entre 0.1x e 20x)
        preco_atual = posicao['preco_entrada'] * random.uniform(0.1, 20.0)
        multiplicador = preco_atual / posicao['preco_entrada']
        
        # Verificar take profits
        if multiplicador >= ESTRATEGIA["take_profit_3"] and not posicao['vendido_3']:
            alertas.append(f"🎯 TAKE PROFIT 3 (10x) - {posicao['token']}")
            posicao['vendido_3'] = True
            
        elif multiplicador >= ESTRATEGIA["take_profit_2"] and not posicao['vendido_2']:
            alertas.append(f"🎯 TAKE PROFIT 2 (5x) - {posicao['token']}")  
            posicao['vendido_2'] = True
            
        elif multiplicador >= ESTRATEGIA["take_profit_1"] and not posicao['vendido_1']:
            alertas.append(f"🎯 TAKE PROFIT 1 (2x) - {posicao['token']}")
            posicao['vendido_1'] = True
            
        # Verificar stop loss
        elif multiplicador <= ESTRATEGIA["stop_loss"] and not posicao['stop_loss_atingido']:
            alertas.append(f"🚨 STOP LOSS (-30%) - {posicao['token']}")
            posicao['stop_loss_atingido'] = True
            posicao['estado'] = "stop_loss"
    
    return alertas

# ============================
# SIMULAÇÃO COMPLETA
# ============================
def simular_hold_long_term():
    """Simulação de hold a longo prazo"""
    print("🤖 SISTEMA DE HOLD A LONGO PRAZO")
    print("💎 Estratégia: Take profits parciais + Moonbag")
    print("=" * 60)
    
    # Abrir posição fake
    token_fake = {
        "token": "GEM_TOKEN",
        "mint": "GemToken111111111111111111111111111111111",
        "exchange": "Binance"
    }
    
    posicao = abrir_posicao(token_fake, 0.1)  # 0.1 SOL
    print(f"✅ Posição aberta: {posicao['token']}")
    print(f"   • Investimento: {posicao['investimento_total']} SOL")
    print(f"   • Preço entrada: {posicao['preco_entrada']:.6f}")
    print(f"   • Hold: TP1(2x) | TP2(5x) | TP3(10x) | Stop(-30%)")
    print("\n🔍 Iniciando monitorização...")
    print("-" * 50)
    
    # Simular 30 dias de monitorização
    for dia in range(30):
        alertas = monitorizar_posicoes()
        
        if alertas:
            print(f"📅 Dia {dia+1}:")
            for alerta in alertas:
                print(f"   {alerta}")
            print()
        
        time.sleep(0.1)
    
    print("✅ Simulação completa!")
    return True

if __name__ == "__main__":
    simular_hold_long_term()