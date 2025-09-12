# criar_carteira.py - VERSÃO DEFINITIVA
from solders.keypair import Keypair
import json
import os
from datetime import datetime
import base58

def criar_carteira_segura():
    """Cria uma nova carteira e guarda de forma segura"""
    print("🔐 A criar nova carteira segura para o bot...")
    print("=" * 50)
    
    # Gera nova keypair
    keypair = Keypair()
    
    # Informações importantes - MÉTODO CORRETO
    endereco_publico = str(keypair.pubkey())
    
    # Converte a private key para base58 manualmente
    private_key_bytes = bytes(keypair)
    private_key = base58.b58encode(private_key_bytes).decode('utf-8')
    
    # Cria pasta segura se não existir
    if not os.path.exists('config'):
        os.makedirs('config')
    
    # Guarda de forma segura
    with open('config/carteira_bot.json', 'w') as f:
        json.dump({
            "public_key": endereco_publico,
            "private_key": private_key,
            "criada_em": datetime.now().isoformat(),
            "uso": "Carteira dedicada para bot de trading"
        }, f, indent=2)
    
    print("🎉 CARTEIRA CRIADA COM SUCESSO!")
    print("=" * 50)
    print(f"📍 Endereço Público: {endereco_publico}")
    print(f"🔐 Private Key: {private_key}")
    print("=" * 50)
    print("🚨 INSTRUÇÕES DE SEGURANÇA:")
    print("   1. ✅ GUARDA este ficheiro 'config/carteira_bot.json' em segurança")
    print("   2. ✅ TRANSFERE apenas fundos que estás disposto a PERDER")
    print("   3. ❌ NUNCA partilhes a private key com ninguém")
    print("   4. ❌ NUNCA faças commit deste ficheiro para GitHub")
    print("   5. ✅ Usa apenas para o bot de trading")
    print("=" * 50)
    
    return keypair

if __name__ == "__main__":
    criar_carteira_segura()