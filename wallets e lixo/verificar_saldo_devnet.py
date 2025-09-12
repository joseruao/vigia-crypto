# verificar_saldo_devnet.py
import requests

def verificar_saldo_devnet():
    public_key = "8WXTo9QFAPj2wygUuZtRAJC2cnQrPXeu3bYc2dwnDTK5"
    
    url = "https://api.devnet.solana.com"
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getBalance",
        "params": [public_key]
    }
    
    response = requests.post(url, json=payload)
    data = response.json()
    
    if 'result' in data:
        saldo_lamports = data['result']['value']
        saldo_sol = saldo_lamports / 1000000000
        print(f"💰 Saldo Devnet: {saldo_sol} SOL (fake)")
    else:
        print("❌ Erro:", data.get('error', 'Unknown'))

verificar_saldo_devnet()