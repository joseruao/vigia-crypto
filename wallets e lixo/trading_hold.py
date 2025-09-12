# trading_hold.py - Sistema de HOLD para gems
import time
import random
from datetime import datetime

# ============================
# ESTRATÉGIA DE HOLD
# ============================
ESTRATEGIA = {
    "take_profit_1": 2.0,    # Vender 25% a 2x
    "take_profit_2": 5.0,    # Vender 25% a 5x
    "take_profit_3": 10.0,   # Vender 25% a 10x
    "stop_loss": 0.7,        # Stop loss a -30%
    "hold_remanescente": 0.25, # Manter 25% para moonbag
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
        "vendido_1": False,
        "vendido_2": False, 
        "vendido_3": False,
        "stop_loss_atingido": False,
        "estado": "ativa"
    }
    
    posicoes_ativas[posicao_id] = posicao
    print(f"✅ POSIÇÃO ABERTA: {token_info['token']}")
    print(f"   • Investimento: {amount_sol} SOL")
    print(f"   • Estratégia: TP1(2x) | TP2(5x) | TP3(10x) | Stop(-30%)")
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
# TESTE DO SISTEMA
# ============================
def testar_sistema_hold():
    """Testa o sistema de hold"""
    print("🧪 TESTE SISTEMA HOLD")
    print("=" * 50)
    
    # Cria alerta fake
    alerta_fake = {
        "token": "GEM_TOKEN",
        "mint": "GemToken111111111111111111111111111111111",
        "exchange": "Binance"
    }
    
    # Abre posição
    posicao = abrir_posicao(alerta_fake, 0.1)
    
    print("\n🔍 Simulando 30 dias...")
    for dia in range(30):
        alertas = monitorizar_posicoes()
        if alertas:
            print(f"📅 Dia {dia+1}:")
            for alerta in alertas:
                print(f"   {alerta}")
    
    print("✅ Teste completo!")

if __name__ == "__main__":
    testar_sistema_hold()