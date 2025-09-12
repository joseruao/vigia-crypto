# vigia_solana_realtime_corrigido.py - VERSÃO COMPLETAMENTE CORRIGIDA
import requests
import time
from datetime import datetime

# ============================
# CONFIGURAÇÃO SOLANA
# ============================
TELEGRAM_BOT_TOKEN_SOL = "8350004696:AAGVXDH0hRr9S4EPsuQdwDbrG0Pa1m3i_-U"
TELEGRAM_CHAT_ID_SOL = "5239378332"
HELIUS_API_KEY = "0fd1b496-c250-459e-ba21-fa5a33caf055"
HELIUS_URL = f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"

# Wallets de exchanges Solana
EXCHANGE_WALLETS_SOL = {
    "Binance 1": "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
    "Binance 2": "5tzFkiKscXHK5ZXCGbXZxdw7gTjjD1mBwuoFbhUvuAi9",
    "Binance 3": "8kPLJg9eKSwCoDJjK3CixgB3Mf7i5p2hWQqRgt7F5XkR",
    "Coinbase 1": "9obNtb5GyUegcs3a1CbBkLuc5hEWynWfJC6gjz5uWQkE",
    "Coinbase Hot": "FpwQQhQQoEaVu3WU2qZMfF1hx48YyfwsLoRgXG83E99Q",
    "Bybit": "AC5RDfQFmDS1deWZos921JfqscXdByf8BKHs5ACWjtW2",
    "Gate.io": "u6PJ8DtQuPFnfmwHbGFULQ4u4EgjDiyYKjVEsynXq2w",
    "Bitget": "A77HErqtfN1hLLpvZ9pCtu66FEtM8BveoaKbbMoZ4RiR",
    "Kraken Cold 1": "9cNE6KBg2Xmf34FPMMvzDF8yUHMrgLRzBV3vD7b1JnUS",
    "Kraken Cold 2": "F7RkX6Y1qTfBqoX5oHoZEgrG1Dpy55UZ3GfWwPbM58nQ",
    "OKX": "HWpGJNxbQRW5HiwHfL2QwF45vweKD2tSfRo8FwY3SgKp",
    "FTX": "2npR8J6kKgrY2T6VioeS5pbgjRtx6eXG3wJ8kYF8tX9L",
    "MEXC": "H7gyjxzXm7fQ6pfx9WkQqJk4DfjRk7Vc1nG5VcJqJ5qj",
}

THRESHOLD_USD = 50000
CHECK_INTERVAL = 60
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"

# ============================
# FUNÇÃO ANALYZE COMPLETAMENTE CORRIGIDA
# ============================
def analyze_transaction_details(transaction_data, wallet_address, exchange_name):
    """Análise de transações Solana com DexScreener - COMPLETAMENTE CORRIGIDA"""
    try:
        # Verificação profunda da estrutura dos dados
        if not transaction_data or not isinstance(transaction_data, dict):
            return None
            
        result = transaction_data.get('result', {})
        if not result:
            return None
            
        meta = result.get('meta', {})
        if not meta:
            return None
        
        # Verificar se há erro na transação
        if meta.get('err'):
            return None
        
        post_token_balances = meta.get('postTokenBalances', [])
        pre_token_balances = meta.get('preTokenBalances', [])
        
        # Verificar se são listas
        if not isinstance(post_token_balances, list) or not isinstance(pre_token_balances, list):
            return None
        
        for balance in post_token_balances:
            if not isinstance(balance, dict):
                continue
                
            # Verificação segura de todos os campos
            owner = balance.get('owner')
            ui_token_amount = balance.get('uiTokenAmount', {})
            current_amount = ui_token_amount.get('uiAmount', 0) if isinstance(ui_token_amount, dict) else 0
            mint_address = balance.get('mint')
            
            # Converter para float e garantir que é número
            try:
                current_amount = float(current_amount) if current_amount is not None else 0
            except (ValueError, TypeError):
                current_amount = 0
            
            if (owner == wallet_address and current_amount > 0 and mint_address):
                previous_amount = 0
                
                # Buscar saldo anterior
                for pre_balance in pre_token_balances:
                    if not isinstance(pre_balance, dict):
                        continue
                        
                    pre_owner = pre_balance.get('owner')
                    pre_mint = pre_balance.get('mint')
                    pre_ui_token_amount = pre_balance.get('uiTokenAmount', {})
                    pre_amount = pre_ui_token_amount.get('uiAmount', 0) if isinstance(pre_ui_token_amount, dict) else 0
                    
                    try:
                        pre_amount = float(pre_amount) if pre_amount is not None else 0
                    except (ValueError, TypeError):
                        pre_amount = 0
                    
                    if pre_owner == wallet_address and pre_mint == mint_address:
                        previous_amount = pre_amount
                        break
                
                amount_received = current_amount - previous_amount
                
                if amount_received > 0:
                    token_symbol = get_token_symbol(mint_address)
                    
                    # Ignorar tokens principais
                    tokens_que_nao_quero = ["SOL", "BTC", "ETH", "USDC", "USDT"]
                    
                    if token_symbol not in tokens_que_nao_quero:
                        # Buscar dados do DexScreener
                        dex_data = get_dexscreener_data_solana(mint_address)
                        
                        if dex_data and dex_data.get('price', 0) > 0:
                            # Garantir que todos os valores são números
                            price = float(dex_data.get('price', 0)) or 0
                            liquidity = float(dex_data.get('liquidity', 0)) or 0
                            fdv = float(dex_data.get('fdv', 0)) or 0
                            volume_24h = float(dex_data.get('volume_24h', 0)) or 0
                            
                            value_usd = amount_received * price
                            
                            # Critérios para gems (com verificações extras)
                            if (value_usd >= THRESHOLD_USD and
                                liquidity > 10000 and
                                fdv < 100000000 and
                                volume_24h > 5000):
                                
                                return {
                                    "exchange": exchange_name,
                                    "token": token_symbol,
                                    "token_address": mint_address,
                                    "amount": amount_received,
                                    "value_usd": value_usd,
                                    "price": price,
                                    "liquidity": liquidity,
                                    "fdv": fdv,
                                    "volume_24h": volume_24h,
                                    "price_change_24h": float(dex_data.get('price_change_24h', 0)) or 0,
                                    "dex": dex_data.get('dex', 'Unknown'),
                                    "pair_url": dex_data.get('pair_url', ''),
                                    "signature": result.get('transaction', {}).get('signatures', [''])[0],
                                    "timestamp": result.get('blockTime', int(time.time()))
                                }
        return None
        
    except Exception as e:
        print(f"❌ Erro CRÍTICO na análise: {e}")
        import traceback
        traceback.print_exc()
        return None

# ============================
# FUNÇÕES AUXILIARES (mantidas como estavam)
# ============================
def send_telegram_alert_sol(message):
    """Envia alerta para o Telegram Solana"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN_SOL}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID_SOL,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200:
            print(f"✅ Alerta enviado para Telegram Solana")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Erro ao enviar para Telegram Solana: {e}")
        return False

def get_transaction_details(signature):
    """Obtém detalhes de uma transação Solana"""
    try:
        payload = {
            "jsonrpc": "2.0",
            "id": "vigia-details",
            "method": "getTransaction",
            "params": [signature, {"encoding": "json", "maxSupportedTransactionVersion": 0}]
        }
        response = requests.post(HELIUS_URL, json=payload, timeout=10)
        return response.json() if response.status_code == 200 else None
    except:
        return None

def get_dexscreener_data_solana(token_address):
    """Obtém dados do DexScreener para tokens Solana"""
    try:
        url = f"{DEXSCREENER_API}{token_address}"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('pairs') and len(data['pairs']) > 0:
                pair = data['pairs'][0]
                return {
                    'price': float(pair.get('priceUsd', 0)) or 0,
                    'liquidity': float(pair.get('liquidity', {}).get('usd', 0)) or 0,
                    'fdv': float(pair.get('fdv', 0)) or 0,
                    'volume_24h': float(pair.get('volume', {}).get('h24', 0)) or 0,
                    'price_change_24h': float(pair.get('priceChange', {}).get('h24', 0)) or 0,
                    'dex': pair.get('dexId', 'Unknown'),
                    'pair_url': pair.get('url', ''),
                    'base_token': pair.get('baseToken', {}).get('name', 'Unknown')
                }
        return None
    except Exception as e:
        print(f"❌ Erro ao buscar DexScreener: {e}")
        return None

def get_token_symbol(mint_address):
    """Obtém símbolo do token Solana"""
    known_tokens = {
        "So11111111111111111111111111111111111111112": "SOL",
        "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v": "USDC",
        "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB": "USDT",
        "2FPyTwcZLUg1MDrwsyoP4D6s1tM7hAkHYRjkNb5w6Pxk": "ETH",
        "9n4nbM75f5Ui33ZbPYXn59EwSgE8CGsHtAeTH5YFeJ9E": "BTC",
    }
    return known_tokens.get(mint_address, f"UNKNOWN ({mint_address[:6]}...)")

def format_solana_alert(alert_info):
    """Formata alerta bonito para Telegram"""
    emoji = "💎" if alert_info.get('fdv', 0) < 50000000 else "🔥"
    trend_emoji = "📈" if alert_info.get('price_change_24h', 0) > 0 else "📉"
    
    message = f"{emoji} <b>ALERTA SOLANA GEM</b> {emoji}\n\n"
    message += f"🏦 <b>Exchange:</b> {alert_info.get('exchange', 'Unknown')}\n"
    message += f"💎 <b>Token:</b> {alert_info.get('token', 'Unknown')}\n"
    message += f"💰 <b>Valor Recebido:</b> ${alert_info.get('value_usd', 0):,.0f}\n"
    message += f"📦 <b>Quantidade:</b> {alert_info.get('amount', 0):,.0f}\n"
    message += f"📊 <b>Preço:</b> ${alert_info.get('price', 0):.8f}\n"
    message += f"💧 <b>Liquidez:</b> ${alert_info.get('liquidity', 0):,.0f}\n"
    message += f"🏢 <b>FDV:</b> ${alert_info.get('fdv', 0):,.0f}\n"
    message += f"📈 <b>Volume 24h:</b> ${alert_info.get('volume_24h', 0):,.0f}\n"
    message += f"{trend_emoji} <b>Variação 24h:</b> {alert_info.get('price_change_24h', 0):+.1f}%\n"
    message += f"🦄 <b>DEX:</b> {alert_info.get('dex', 'Unknown')}\n"
    message += f"⏰ <b>Hora:</b> {datetime.fromtimestamp(alert_info.get('timestamp', time.time())).strftime('%H:%M:%S')}\n\n"
    
    message += f"🔗 <a href='{alert_info.get('pair_url', '')}'>Ver no DexScreener</a>\n"
    message += f"🔍 <a href='https://solscan.io/token/{alert_info.get('token_address', '')}'>Solscan</a>\n"
    message += f"📝 <a href='https://solscan.io/tx/{alert_info.get('signature', '')}'>Ver Transação</a>\n\n"
    
    message += f"<i>⚠️ Não é aconselhamento financeiro</i>"
    
    return message

def monitor_solana_realtime():
    """Monitorização em tempo real das wallets Solana"""
    print("🤖 VIGILANTE SOLANA - MODO TEMPO REAL (ULTRA-CORRIGIDO)")
    print("💎 Procurando gems potenciais em exchanges")
    print("📊 Usando DexScreener para análise")
    print("=" * 60)
    
    # Enviar mensagem inicial
    start_message = "🔔 <b>VIGIA SOLANA INICIADO</b>\n✅ Monitorizando exchanges em tempo real\n⏰ Hora: " + datetime.now().strftime("%H:%M:%S")
    send_telegram_alert_sol(start_message)
    
    last_signatures = {}
    
    while True:
        try:
            print(f"\n🔍 Verificando transações... {datetime.now().strftime('%H:%M:%S')}")
            
            for exchange_name, wallet_address in EXCHANGE_WALLETS_SOL.items():
                try:
                    # Buscar assinaturas recentes
                    payload = {
                        "jsonrpc": "2.0",
                        "id": "vigia-signatures",
                        "method": "getSignaturesForAddress",
                        "params": [wallet_address, {"limit": 3}]  # Reduzido para 3 para testes
                    }
                    
                    response = requests.post(HELIUS_URL, json=payload, timeout=10)
                    if response.status_code != 200:
                        print(f"   ❌ HTTP Error para {exchange_name}")
                        continue

                    data = response.json()
                    if "error" in data:
                        print(f"   ❌ API Error para {exchange_name}: {data['error']}")
                        continue
                        
                    if not data.get('result'):
                        print(f"   ℹ️  Sem transações para {exchange_name}")
                        continue

                    for tx in data['result']:
                        signature = tx['signature']
                        
                        if signature != last_signatures.get(wallet_address):
                            print(f"   🔍 Analisando transação: {signature[:10]}...")
                            tx_details = get_transaction_details(signature)
                            
                            if not tx_details:
                                print(f"   ❌ Sem detalhes para transação")
                                continue

                            alert_info = analyze_transaction_details(tx_details, wallet_address, exchange_name)
                            
                            if alert_info:
                                message = format_solana_alert(alert_info)
                                send_telegram_alert_sol(message)
                                
                                print(f"   ✅ ALERTA: {exchange_name} recebeu ${alert_info.get('value_usd', 0):,.0f} em {alert_info.get('token', 'Unknown')}")
                                time.sleep(2)
                            else:
                                print(f"   ℹ️  Transação não relevante")
                            
                            last_signatures[wallet_address] = signature

                    time.sleep(0.5)

                except Exception as e:
                    print(f"❌ Erro a verificar {exchange_name}: {e}")
                    continue
            
            print(f"♻️ Ciclo completo. Próxima verificação em {CHECK_INTERVAL} segundos...")
            time.sleep(CHECK_INTERVAL)
            
        except Exception as e:
            print(f"❌ Erro no ciclo principal: {e}")
            time.sleep(30)

# ============================
# EXECUÇÃO PRINCIPAL
# ============================
if __name__ == "__main__":
    print(f"🤖 Bot Token: {'✅' if TELEGRAM_BOT_TOKEN_SOL else '❌'}")
    print(f"💬 Chat ID: {'✅' if TELEGRAM_CHAT_ID_SOL else '❌'}")
    print(f"🔍 Monitorizando {len(EXCHANGE_WALLETS_SOL)} wallets Solana")
    print("=" * 60)
    
    monitor_solana_realtime()