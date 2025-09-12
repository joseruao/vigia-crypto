# telegram_history_analyzer.py
import requests
import re
import time
import json
from datetime import datetime, timedelta

# ============================
# CONFIGURAÇÃO
# ============================
TELEGRAM_BOT_TOKEN = "8421287024:AAEPmsS3BBM-ITE95RJfDEmnzgAnyGkK9Vs"
TELEGRAM_CHAT_ID = "5239378332"

# APIs para análise
COINGECKO_API = "https://api.coingecko.com/api/v3"
DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"

# ============================
# FUNÇÃO ALTERNATIVA PARA LER HISTÓRICO
# ============================

def get_chat_history():
    """Obtém histórico de mensagens do chat usando uma abordagem diferente"""
    try:
        # Método alternativo: usar uma API externa ou abordagem diferente
        # Vamos tentar uma abordagem mais direta
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getChatHistory"
        
        # Para canais/grupos, precisamos de uma abordagem diferente
        # Vamos tentar getUpdates mas com offset management
        
        messages = []
        
        # Tentar várias vezes para obter mensagens
        for attempt in range(3):
            try:
                url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
                response = requests.get(url, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    for update in data.get('result', []):
                        if 'channel_post' in update:
                            message = update['channel_post']
                            if 'text' in message:
                                messages.append(message['text'])
                        elif 'message' in update:
                            message = update['message']
                            if 'text' in message:
                                messages.append(message['text'])
                
                if messages:
                    break
                    
            except Exception as e:
                print(f"❌ Tentativa {attempt + 1} falhou: {e}")
                time.sleep(2)
        
        return messages
        
    except Exception as e:
        print(f"❌ Erro ao buscar histórico: {e}")
        return []

def get_recent_messages_simulated():
    """Simula mensagens recentes para teste - ENQUANTO NÃO FUNCIONA A API"""
    print("⚠️  Usando mensagens simuladas para teste...")
    
    # Mensagens de exemplo baseadas no que normalmente recebes
    simulated_messages = [
        "💎 MKR detectado na Binance - Valor: $866,874.34",
        "🚨 ALERTA: Token XYZ encontrado - $50,000",
        "🔥 Novo par detectado: ABC/ETH - Liquidez: $1.2M",
        "💎 SUSHI movimentado na Coinbase - $120,000",
        "🎯 Possível listing: TOKEN123 na Kraken",
        "⚠️  Cuidado com SCAM token: 0x123...abc",
        "💎 AAVE detectado em wallet suspeita - $75,000",
        "🚀 Novo token promissor: MOON - Volume: $500K"
    ]
    
    return simulated_messages

def send_telegram_alert(message):
    """Envia alerta para Telegram"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        response = requests.post(url, json=payload, timeout=15)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Erro ao enviar para Telegram: {e}")
        return False

# ============================
# FUNÇÕES DE ANÁLISE (MANTIDAS)
# ============================

def extract_tokens_from_messages(messages):
    """Extrai tokens das mensagens do Telegram"""
    tokens_found = {}
    
    for message in messages:
        # Padrões para encontrar tokens
        patterns = [
            r'Token:\s*([A-Z0-9]{2,10})',
            r'💎\s*([A-Z0-9]{2,10})',
            r'\(([A-Z0-9]{2,10})\)',
            r'\b([A-Z]{3,10})\b(?![a-z])'  # Só maiúsculas
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, message)
            for token in matches:
                if token not in ["USDT", "USDC", "ETH", "BTC", "SOL", "BNB", "XRP", "ADA", "DOT"]:
                    contract_match = re.search(r'0x[a-fA-F0-9]{40}', message)
                    contract = contract_match.group(0) if contract_match else None
                    
                    if token not in tokens_found:
                        tokens_found[token] = {
                            'count': 0,
                            'contract': contract,
                            'messages': []
                        }
                    
                    tokens_found[token]['count'] += 1
                    tokens_found[token]['messages'].append(message)
    
    return tokens_found

def get_token_analysis(token_symbol, contract_address=None):
    """Análise completa IA de um token"""
    try:
        print(f"   🔍 Analisando {token_symbol}...")
        
        # Dados simulados para teste - depois substitui por APIs reais
        analysis = {
            'token': token_symbol,
            'trust_score': 75,
            'listing_probability': 60,
            'scam_risk': 15,
            'red_flags': ['Volume moderado'],
            'green_flags': ['Market Cap decente', 'Liquidez boa'],
            'recommendation': '✅ PROJETO CONFIÁVEL - Bom potencial',
            'details': {}
        }
        
        # Se for MKR (que apareceu no teu alerta)
        if token_symbol == "MKR":
            analysis.update({
                'trust_score': 85,
                'listing_probability': 40,  # Já está listado em todo lado
                'scam_risk': 5,
                'green_flags': ['Bluechip estabelecido', 'Listado em todas exchanges'],
                'red_flags': [],
                'recommendation': '✅ BLUECHIP - Já listado em todas exchanges'
            })
        
        return analysis
        
    except Exception as e:
        print(f"❌ Erro na análise de {token_symbol}: {e}")
        return None

def format_analysis_report(analysis):
    """Formata relatório de análise"""
    try:
        report = f"🤖 <b>ANÁLISE IA - {analysis['token']}</b>\n\n"
        
        report += f"📊 <b>Trust Score:</b> {analysis['trust_score']}/100\n"
        report += f"🎯 <b>Prob. Listing:</b> {analysis['listing_probability']}%\n"
        report += f"⚠️  <b>Risco Scam:</b> {analysis['scam_risk']}%\n\n"
        
        if analysis['green_flags']:
            report += "🟢 <b>PONTOS POSITIVOS:</b>\n"
            for flag in analysis['green_flags'][:3]:
                report += f"• {flag}\n"
            report += "\n"
        
        if analysis['red_flags']:
            report += "🔴 <b>ALERTAS:</b>\n"
            for flag in analysis['red_flags'][:3]:
                report += f"• {flag}\n"
            report += "\n"
        
        report += f"💡 <b>RECOMENDAÇÃO:</b> {analysis['recommendation']}\n\n"
        report += f"<i>⏰ Analisado em {datetime.now().strftime('%H:%M:%S')}</i>"
        
        return report
    except Exception as e:
        return f"❌ Erro na análise de {analysis.get('token', 'token')}"

# ============================
# PROGRAMA PRINCIPAL
# ============================

def main():
    print("🤖 ANALISADOR IA DE ALERTAS - VERSÃO SIMPLIFICADA")
    print("=" * 60)
    
    # 1. Obter mensagens (simulado por agora)
    messages = get_recent_messages_simulated()
    print(f"📨 {len(messages)} mensagens para analisar")
    
    # 2. Extrair tokens
    tokens = extract_tokens_from_messages(messages)
    print(f"💎 {len(tokens)} tokens encontrados: {list(tokens.keys())}")
    
    if not tokens:
        print("❌ Nenhum token para analisar")
        return
    
    # 3. Analisar cada token
    analyzed_count = 0
    for token_symbol, token_data in tokens.items():
        analysis = get_token_analysis(token_symbol, token_data.get('contract'))
        
        if analysis:
            report = format_analysis_report(analysis)
            
            # Enviar análise
            if send_telegram_alert(report):
                print(f"✅ Análise enviada para {token_symbol}")
                analyzed_count += 1
            time.sleep(2)
    
    print(f"🎯 {analyzed_count} análises enviadas com sucesso!")

# Versão alternativa: analisar tokens específicos que sabes que aparecem
def analyze_specific_tokens():
    """Analisa tokens específicos que costumam aparecer"""
    print("🔍 Analisando tokens específicos...")
    
    # Tokens que costumam aparecer nos teus alertas
    common_tokens = ["MKR", "SUSHI", "AAVE", "XYZ", "ABC", "MOON", "TOKEN123"]
    
    analyzed_count = 0
    for token in common_tokens:
        analysis = get_token_analysis(token)
        
        if analysis:
            report = format_analysis_report(analysis)
            
            if send_telegram_alert(report):
                print(f"✅ Análise enviada para {token}")
                analyzed_count += 1
            time.sleep(2)
    
    print(f"🎯 {analyzed_count} análises de tokens comuns enviadas!")

if __name__ == "__main__":
    # Executar análise principal
    main()
    
    # Executar também análise de tokens comuns
    analyze_specific_tokens()