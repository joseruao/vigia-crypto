import ccxt
import pandas as pd
import numpy as np
import ta
import time
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

# ========== CONFIGURAÇÃO ==========
TELEGRAM_BOT_TOKEN = "8350004696:AAGVXDH0hRr9S4EPsuQdwDbrG0Pa1m3i_-U"
TELEGRAM_CHAT_ID = "5239378332"

EXCHANGE = 'binance'
TIMEFRAMES = ['5m', '15m', '1h', '4h']
CHECK_INTERVAL = 60  # segundos entre análises

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== CLASSE PRINCIPAL ==========
class CryptoAnalyzerBot:
    def __init__(self):
        self.exchange = getattr(ccxt, EXCHANGE)({
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'}
        })
        self.analyzed_pairs = {}
        self.alert_history = {}
        
    # ========== FUNÇÕES TELEGRAM ==========
    def send_telegram_alert(self, alert_type: str, symbol: str, data: Dict):
        """Envia alerta para Telegram"""
        try:
            message = ""
            if alert_type == "perto_suporte":
                message = self._format_perto_suporte(symbol, data)
            elif alert_type == "perto_resistencia":
                message = self._format_perto_resistencia(symbol, data)
            elif alert_type == "entrada_bom":
                message = self._format_entrada_bom(symbol, data)
            elif alert_type == "entrada_ideal":
                message = self._format_entrada_ideal(symbol, data)
            elif alert_type == "setup_quebrou":
                message = self._format_setup_quebrou(symbol, data)
            else:
                return
            
            # Verificar se já enviou alerta similar recentemente
            alert_key = f"{symbol}_{alert_type}_{data.get('level', '')}"
            if alert_key in self.alert_history:
                last_alert = self.alert_history[alert_key]
                if datetime.now() - last_alert < timedelta(minutes=15):
                    logger.info(f"Alerta {alert_key} enviado recentemente, ignorando")
                    return
            
            # Enviar mensagem
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': TELEGRAM_CHAT_ID,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                self.alert_history[alert_key] = datetime.now()
                logger.info(f"Alerta enviado: {symbol} - {alert_type}")
            else:
                logger.error(f"Erro Telegram: {response.text}")
                
        except Exception as e:
            logger.error(f"Erro enviar alerta: {e}")
    
    def _format_perto_suporte(self, symbol: str, data: Dict) -> str:
        return f"""
🔔 <b>PERTO DE SUPORTE - {symbol}</b>

🎯 <b>Setup:</b> {"LONG se segurar | SHORT se quebrar"}
💰 <b>Preço Atual:</b> ${data['price']:.2f}
📊 <b>Distância:</b> {data['distance_percent']:.2f}%
🛡️ <b>Suporte:</b> ${data['support_level']:.2f}

📈 <b>Volume:</b> {data['volume_ratio']:.1f}x
📉 <b>RSI:</b> {data['rsi']:.1f}
⚡ <b>MACD:</b> {"Bullish" if data['macd_bullish'] else "Bearish"}

🎯 <b>ORDEM PARA COLOCAR:</b>
<b>LONG (se segurar suporte):</b>
• Entrada: ${data['long_entry']:.2f}
• Stop: ${data['long_stop']:.2f} ({data['long_stop_percent']:.1f}%)
• TP1: ${data['long_tp1']:.2f} (+{data['long_tp1_percent']:.1f}%)
• TP2: ${data['long_tp2']:.2f} (+{data['long_tp2_percent']:.1f}%)

<b>SHORT (se quebrar suporte):</b>
• Entrada: ${data['short_entry']:.2f}
• Stop: ${data['short_stop']:.2f} ({data['short_stop_percent']:.1f}%)
• TP1: ${data['short_tp1']:.2f} (-{data['short_tp1_percent']:.1f}%)
• TP2: ${data['short_tp2']:.2f} (-{data['short_tp2_percent']:.1f}%)

⚠️ <b>Monitorar:</b> Reação no suporte
⏰ <b>Timeframe:</b> {data['timeframe']}
📊 <b>Probabilidade LONG:</b> {data['prob_long']}%
        """
    
    def _format_perto_resistencia(self, symbol: str, data: Dict) -> str:
        return f"""
🔔 <b>PERTO DE RESISTÊNCIA - {symbol}</b>

🎯 <b>Setup:</b> {"SHORT se rejeitar | LONG se quebrar"}
💰 <b>Preço Atual:</b> ${data['price']:.2f}
📊 <b>Distância:</b> {data['distance_percent']:.2f}%
⛰️ <b>Resistência:</b> ${data['resistance_level']:.2f}

📈 <b>Volume:</b> {data['volume_ratio']:.1f}x
📉 <b>RSI:</b> {data['rsi']:.1f}
⚡ <b>MACD:</b> {"Bullish" if data['macd_bullish'] else "Bearish"}

🎯 <b>ORDEM PARA COLOCAR:</b>
<b>SHORT (se rejeitar resistência):</b>
• Entrada: ${data['short_entry']:.2f}
• Stop: ${data['short_stop']:.2f} ({data['short_stop_percent']:.1f}%)
• TP1: ${data['short_tp1']:.2f} (-{data['short_tp1_percent']:.1f}%)
• TP2: ${data['short_tp2']:.2f} (-{data['short_tp2_percent']:.1f}%)

<b>LONG (se quebrar resistência):</b>
• Entrada: ${data['long_entry']:.2f}
• Stop: ${data['long_stop']:.2f} ({data['long_stop_percent']:.1f}%)
• TP1: ${data['long_tp1']:.2f} (+{data['long_tp1_percent']:.1f}%)
• TP2: ${data['long_tp2']:.2f} (+{data['long_tp2_percent']:.1f}%)

⚠️ <b>Monitorar:</b> Reação na resistência
⏰ <b>Timeframe:</b> {data['timeframe']}
📊 <b>Probabilidade SHORT:</b> {data['prob_short']}%
        """
    
    def _format_entrada_bom(self, symbol: str, data: Dict) -> str:
        signal_type = "LONG" if data['signal_type'] == 'long' else "SHORT"
        return f"""
🚀 <b>ENTRADA BOA CONFIRMADA - {symbol}</b>

🎯 <b>Tipo:</b> {signal_type}
📊 <b>Score:</b> {data['score']}/100
💰 <b>Preço Atual:</b> ${data['current_price']:.2f}

✅ <b>Confirmações:</b>
{chr(10).join(['✅ ' + conf for conf in data['confirmations']])}

🎯 <b>ORDEM PARA COLOCAR AGORA:</b>
<b>Entrada:</b> ${data['entry_price']:.2f}
<b>Stop Loss:</b> ${data['stop_loss']:.2f} ({data['stop_percent']:.1f}%)
<b>Take Profit 1:</b> ${data['tp1']:.2f} ({data['tp1_percent']:+.1f}%)
<b>Take Profit 2:</b> ${data['tp2']:.2f} ({data['tp2_percent']:+.1f}%)
<b>Take Profit 3:</b> ${data['tp3']:.2f} ({data['tp3_percent']:+.1f}%)

📊 <b>Risk/Reward:</b> 1:{data['risk_reward']:.1f}
⏱️ <b>Válido por:</b> {data['valid_minutes']} minutos
📈 <b>Volume:</b> {data['volume_ratio']:.1f}x
📉 <b>RSI:</b> {data['rsi']:.1f}
        """
    
    def _format_entrada_ideal(self, symbol: str, data: Dict) -> str:
        signal_type = "LONG IDEAL" if data['signal_type'] == 'long' else "SHORT IDEAL"
        return f"""
🎯🎯 <b>OPORTUNIDADE EXCEPCIONAL - {symbol}</b>

🔥 <b>Sinal:</b> {signal_type}
📊 <b>Probabilidade:</b> {data['probability']}%
💰 <b>Preço Atual:</b> ${data['current_price']:.2f}

✅ <b>MÚLTIPLAS CONFIRMAÇÕES:</b>
{chr(10).join(['🎯 ' + conf for conf in data['all_confirmations']])}

💎 <b>ORDEM DE ENTRADA IDEAL:</b>
<b>Zona de Entrada:</b> ${data['entry_zone_low']:.2f} - ${data['entry_zone_high']:.2f}
<b>Entrada Preferida:</b> ${data['entry_preferred']:.2f}
<b>Stop Loss:</b> ${data['stop_loss']:.2f} ({data['stop_percent']:.1f}%)
<b>Take Profit 1 (25%):</b> ${data['tp1']:.2f} ({data['tp1_percent']:+.1f}%)
<b>Take Profit 2 (50%):</b> ${data['tp2']:.2f} ({data['tp2_percent']:+.1f}%)
<b>Take Profit 3 (25%):</b> ${data['tp3']:.2f} ({data['tp3_percent']:+.1f}%)

📊 <b>Risk/Reward:</b> 1:{data['risk_reward']:.1f}
🎯 <b>Gerenciamento:</b> {data['management']}
⏳ <b>Timeframe:</b> {data['main_timeframe']}
⚠️ <b>Nota:</b> {data['note']}
        """
    
    def _format_setup_quebrou(self, symbol: str, data: Dict) -> str:
        direction = "SUPORTE" if data['broken_level'] == 'support' else "RESISTÊNCIA"
        action = "SHORT" if data['broken_level'] == 'support' else "LONG"
        return f"""
⚡ <b>SETUP QUEBROU - {symbol}</b>

🎯 <b>{direction} QUEBRADO → {action} CONFIRMADO</b>
💰 <b>Preço:</b> ${data['price']:.2f}
📊 <b>Nível Quebrado:</b> ${data['level_price']:.2f}

✅ <b>Setup Ativado:</b> {action}
🎯 <b>Entrada Imediata:</b> ${data['entry_price']:.2f}
🛑 <b>Stop:</b> ${data['stop_loss']:.2f}
🎯 <b>Target:</b> ${data['target']:.2f}

📈 <b>Volume Break:</b> {data['volume_ratio']:.1f}x
⏰ <b>Timeframe:</b> {data['timeframe']}
🔍 <b>Confirmação:</b> Candle fechou abaixo/acima do nível
        """
    
    # ========== FUNÇÕES DE ANÁLISE APERFEIÇOADAS ==========
    def get_top_coins(self, limit: int = 50) -> List[str]:
        """Obtém sempre as top 50 moedas por volume"""
        try:
            tickers = self.exchange.fetch_tickers()
            
            # Coletar todos os pares USDT com volume
            all_usdt_pairs = []
            for pair, ticker in tickers.items():
                if '/USDT' in pair and ticker.get('quoteVolume', 0) > 1000000:  # > 1M volume
                    all_usdt_pairs.append((pair, ticker['quoteVolume']))
            
            # Ordenar por volume e pegar top
            sorted_pairs = sorted(all_usdt_pairs, key=lambda x: x[1], reverse=True)[:limit]
            
            # Se não tiver 50 com >1M, completar com menos volume
            if len(sorted_pairs) < limit:
                for pair, ticker in tickers.items():
                    if '/USDT' in pair and pair not in [p[0] for p in sorted_pairs]:
                        sorted_pairs.append((pair, ticker.get('quoteVolume', 0)))
                    if len(sorted_pairs) >= limit:
                        break
            
            return [pair[0] for pair in sorted_pairs]
            
        except Exception as e:
            logger.error(f"Erro ao obter top coins: {e}")
            # Fallback para lista de moedas principais
            return ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'XRP/USDT', 'ADA/USDT', 
                   'AVAX/USDT', 'DOT/USDT', 'DOGE/USDT', 'MATIC/USDT', 'LINK/USDT', 'ATOM/USDT']
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calcula todos os indicadores técnicos com tratamento de erros"""
        if df is None or len(df) < 20:
            return df
        
        try:
            # Indicadores básicos
            df['rsi'] = ta.momentum.RSIIndicator(df['close'], window=14).rsi()
            
            # EMAs para tendência
            df['ema_9'] = ta.trend.EMAIndicator(df['close'], window=9).ema_indicator()
            df['ema_21'] = ta.trend.EMAIndicator(df['close'], window=21).ema_indicator()
            df['ema_50'] = ta.trend.EMAIndicator(df['close'], window=50).ema_indicator()
            
            # MACD
            macd = ta.trend.MACD(df['close'], window_slow=26, window_fast=12, window_sign=9)
            df['macd'] = macd.macd()
            df['macd_signal'] = macd.macd_signal()
            
            # Volume
            df['volume_sma'] = df['volume'].rolling(20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_sma'].replace(0, 1)
            
            # Suporte e Resistência dinâmicos
            df['support'] = df['low'].rolling(20).min()
            df['resistance'] = df['high'].rolling(20).max()
            
            # ATR para stops
            df['atr'] = ta.volatility.AverageTrueRange(
                df['high'], df['low'], df['close'], window=14
            ).average_true_range()
            
            return df
        except Exception as e:
            logger.error(f"Erro calcular indicadores: {e}")
            return df
    
    def detect_key_levels(self, df: pd.DataFrame, current_price: float) -> Dict:
        """Detecta níveis chave de suporte e resistência"""
        if len(df) < 50:
            return {'nearest_support': 0, 'nearest_resistance': 0}
        
        try:
            # Encontrar suportes recentes (mínimos locais)
            df['low_rolling_min'] = df['low'].rolling(10, center=True).min()
            supports = df[df['low'] == df['low_rolling_min']]['low'].unique()
            supports = [s for s in supports if s < current_price]
            
            # Encontrar resistências recentes (máximos locais)
            df['high_rolling_max'] = df['high'].rolling(10, center=True).max()
            resistances = df[df['high'] == df['high_rolling_max']]['high'].unique()
            resistances = [r for r in resistances if r > current_price]
            
            # Encontrar mais próximo
            nearest_support = max(supports) if supports else 0
            nearest_resistance = min(resistances) if resistances else 0
            
            # Calcular distâncias percentuais
            dist_to_support = ((current_price - nearest_support) / current_price * 100) if nearest_support > 0 else 999
            dist_to_resistance = ((nearest_resistance - current_price) / current_price * 100) if nearest_resistance > 0 else 999
            
            return {
                'nearest_support': nearest_support,
                'nearest_resistance': nearest_resistance,
                'dist_to_support': dist_to_support,
                'dist_to_resistance': dist_to_resistance,
                'closer_to': 'support' if dist_to_support < dist_to_resistance else 'resistance'
            }
        except:
            return {'nearest_support': 0, 'nearest_resistance': 0}
    
    def analyze_pair(self, symbol: str) -> Optional[Dict]:
        """Analisa um par com detecção inteligente de níveis"""
        try:
            # Obter dados do timeframe principal (5m)
            df_5m = self.get_ohlcv_data(symbol, '5m', 100)
            if df_5m is None or len(df_5m) < 50:
                return None
            
            # Calcular indicadores
            df_5m = self.calculate_indicators(df_5m)
            
            # Dados atuais
            current = df_5m.iloc[-1]
            current_price = current['close']
            
            # Detectar níveis chave
            levels = self.detect_key_levels(df_5m, current_price)
            
            # Determinar o setup mais provável
            setup_type = self.determine_setup_type(df_5m, levels, current_price)
            
            if setup_type == 'none':
                return None
            
            # Preparar análise
            analysis = {
                'symbol': symbol,
                'price': current_price,
                'levels': levels,
                'setup_type': setup_type,
                'rsi': current['rsi'] if not pd.isna(current['rsi']) else 50,
                'volume_ratio': current['volume_ratio'] if not pd.isna(current['volume_ratio']) else 1,
                'macd_bullish': current['macd'] > current['macd_signal'] if not pd.isna(current['macd']) else False,
                'timestamp': datetime.now()
            }
            
            # Adicionar sinais específicos
            analysis['signals'] = self.generate_signals(analysis, df_5m)
            
            return analysis
            
        except Exception as e:
            logger.error(f"Erro analisar {symbol}: {e}")
            return None
    
    def determine_setup_type(self, df: pd.DataFrame, levels: Dict, current_price: float) -> str:
        """Determina o tipo de setup mais provável"""
        if levels['nearest_support'] == 0 and levels['nearest_resistance'] == 0:
            return 'none'
        
        current = df.iloc[-1]
        rsi = current['rsi'] if not pd.isna(current['rsi']) else 50
        volume_ratio = current['volume_ratio'] if not pd.isna(current['volume_ratio']) else 1
        
        # Verificar proximidade a níveis (2-5% é "perto")
        near_support = 2 <= levels['dist_to_support'] <= 5
        near_resistance = 2 <= levels['dist_to_resistance'] <= 5
        
        # Se está perto de ambos, decidir baseado em outros fatores
        if near_support and near_resistance:
            # Decidir baseado em RSI e tendência
            if rsi < 50:
                return 'near_support'  # Mais provável bounce no suporte
            else:
                return 'near_resistance'  # Mais provável rejeição na resistência
        
        elif near_support:
            return 'near_support'
        elif near_resistance:
            return 'near_resistance'
        else:
            return 'none'
    
    def generate_signals(self, analysis: Dict, df: pd.DataFrame) -> List[Dict]:
        """Gera sinais baseados na análise"""
        signals = []
        symbol = analysis['symbol']
        current_price = analysis['price']
        levels = analysis['levels']
        setup_type = analysis['setup_type']
        
        # SINAL 1: PERTO DE SUPORTE/RESISTÊNCIA
        if setup_type == 'near_support':
            signal_data = self.create_support_signal(analysis, df)
            if signal_data:
                signals.append({'type': 'perto_suporte', 'data': signal_data})
        
        elif setup_type == 'near_resistance':
            signal_data = self.create_resistance_signal(analysis, df)
            if signal_data:
                signals.append({'type': 'perto_resistencia', 'data': signal_data})
        
        # SINAL 2: ENTRADA BOA (setup confirmado)
        entry_good = self.check_confirmed_entry(analysis, df)
        if entry_good:
            signals.append({'type': 'entrada_bom', 'data': entry_good})
        
        # SINAL 3: ENTRADA IDEAL (múltiplas confirmações)
        entry_ideal = self.check_ideal_entry(analysis, df)
        if entry_ideal:
            signals.append({'type': 'entrada_ideal', 'data': entry_ideal})
        
        return signals
    
    def create_support_signal(self, analysis: Dict, df: pd.DataFrame) -> Optional[Dict]:
        """Cria sinal de perto de suporte"""
        try:
            current_price = analysis['price']
            support_level = analysis['levels']['nearest_support']
            distance = analysis['levels']['dist_to_support']
            
            if support_level == 0:
                return None
            
            # Calcular níveis de entrada
            atr = df.iloc[-1]['atr'] if not pd.isna(df.iloc[-1]['atr']) else current_price * 0.01
            
            # LONG setup (se segurar suporte)
            long_entry = support_level * 1.001  # Entrada logo acima do suporte
            long_stop = support_level * 0.995   # Stop abaixo do suporte
            long_tp1 = current_price * 1.01     # TP1: 1%
            long_tp2 = current_price * 1.02     # TP2: 2%
            
            # SHORT setup (se quebrar suporte)
            short_entry = support_level * 0.999  # Entrada logo abaixo do suporte
            short_stop = support_level * 1.005   # Stop acima do suporte
            short_tp1 = support_level * 0.99     # TP1: -1%
            short_tp2 = support_level * 0.98     # TP2: -2%
            
            # Calcular probabilidade baseada em RSI e volume
            prob_long = 60 if analysis['rsi'] < 40 else 50
            if analysis['volume_ratio'] > 1.5:
                prob_long += 10
            
            return {
                'price': current_price,
                'support_level': support_level,
                'distance_percent': distance,
                'volume_ratio': analysis['volume_ratio'],
                'rsi': analysis['rsi'],
                'macd_bullish': analysis['macd_bullish'],
                'timeframe': '5m',
                'prob_long': min(prob_long, 80),
                
                # Ordem LONG
                'long_entry': long_entry,
                'long_stop': long_stop,
                'long_stop_percent': ((long_entry - long_stop) / long_entry * 100),
                'long_tp1': long_tp1,
                'long_tp1_percent': ((long_tp1 - long_entry) / long_entry * 100),
                'long_tp2': long_tp2,
                'long_tp2_percent': ((long_tp2 - long_entry) / long_entry * 100),
                
                # Ordem SHORT
                'short_entry': short_entry,
                'short_stop': short_stop,
                'short_stop_percent': ((short_stop - short_entry) / short_entry * 100),
                'short_tp1': short_tp1,
                'short_tp1_percent': ((short_entry - short_tp1) / short_entry * 100),
                'short_tp2': short_tp2,
                'short_tp2_percent': ((short_entry - short_tp2) / short_entry * 100)
            }
        except Exception as e:
            logger.error(f"Erro create_support_signal: {e}")
            return None
    
    def create_resistance_signal(self, analysis: Dict, df: pd.DataFrame) -> Optional[Dict]:
        """Cria sinal de perto de resistência"""
        try:
            current_price = analysis['price']
            resistance_level = analysis['levels']['nearest_resistance']
            distance = analysis['levels']['dist_to_resistance']
            
            if resistance_level == 0:
                return None
            
            # Calcular níveis de entrada
            atr = df.iloc[-1]['atr'] if not pd.isna(df.iloc[-1]['atr']) else current_price * 0.01
            
            # SHORT setup (se rejeitar resistência)
            short_entry = resistance_level * 0.999  # Entrada logo abaixo da resistência
            short_stop = resistance_level * 1.005   # Stop acima da resistência
            short_tp1 = resistance_level * 0.99     # TP1: -1%
            short_tp2 = resistance_level * 0.98     # TP2: -2%
            
            # LONG setup (se quebrar resistência)
            long_entry = resistance_level * 1.001   # Entrada logo acima da resistência
            long_stop = resistance_level * 0.995    # Stop abaixo da resistência
            long_tp1 = resistance_level * 1.01      # TP1: +1%
            long_tp2 = resistance_level * 1.02      # TP2: +2%
            
            # Calcular probabilidade
            prob_short = 60 if analysis['rsi'] > 60 else 50
            if analysis['volume_ratio'] > 1.5:
                prob_short += 10
            
            return {
                'price': current_price,
                'resistance_level': resistance_level,
                'distance_percent': distance,
                'volume_ratio': analysis['volume_ratio'],
                'rsi': analysis['rsi'],
                'macd_bullish': analysis['macd_bullish'],
                'timeframe': '5m',
                'prob_short': min(prob_short, 80),
                
                # Ordem SHORT
                'short_entry': short_entry,
                'short_stop': short_stop,
                'short_stop_percent': ((short_stop - short_entry) / short_entry * 100),
                'short_tp1': short_tp1,
                'short_tp1_percent': ((short_entry - short_tp1) / short_entry * 100),
                'short_tp2': short_tp2,
                'short_tp2_percent': ((short_entry - short_tp2) / short_entry * 100),
                
                # Ordem LONG
                'long_entry': long_entry,
                'long_stop': long_stop,
                'long_stop_percent': ((long_entry - long_stop) / long_entry * 100),
                'long_tp1': long_tp1,
                'long_tp1_percent': ((long_tp1 - long_entry) / long_entry * 100),
                'long_tp2': long_tp2,
                'long_tp2_percent': ((long_tp2 - long_entry) / long_entry * 100)
            }
        except Exception as e:
            logger.error(f"Erro create_resistance_signal: {e}")
            return None
    
    def check_confirmed_entry(self, analysis: Dict, df: pd.DataFrame) -> Optional[Dict]:
        """Verifica entrada boa confirmada"""
        try:
            current = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else current
            
            confirmations = []
            score = 0
            
            # Verificar se o setup se confirmou
            if analysis['setup_type'] == 'near_support':
                # Confirmação de bounce no suporte
                if current['close'] > analysis['levels']['nearest_support'] * 1.002:  # Fechou 0.2% acima
                    confirmations.append("Bounce no Suporte Confirmado")
                    score += 30
                    
                    # Adicionar mais confirmações
                    if current['rsi'] < 45 and current['rsi'] > prev['rsi']:
                        confirmations.append("RSI Reversão Bullish")
                        score += 20
                    
                    if current['volume_ratio'] > 1.8:
                        confirmations.append(f"Volume Alto {current['volume_ratio']:.1f}x")
                        score += 15
            
            elif analysis['setup_type'] == 'near_resistance':
                # Confirmação de rejeição na resistência
                if current['close'] < analysis['levels']['nearest_resistance'] * 0.998:  # Fechou 0.2% abaixo
                    confirmations.append("Rejeição na Resistência Confirmada")
                    score += 30
                    
                    if current['rsi'] > 55 and current['rsi'] < prev['rsi']:
                        confirmations.append("RSI Reversão Bearish")
                        score += 20
                    
                    if current['volume_ratio'] > 1.8:
                        confirmations.append(f"Volume Alto {current['volume_ratio']:.1f}x")
                        score += 15
            
            if score >= 50 and len(confirmations) >= 2:
                # Criar sinal de entrada
                signal_type = 'long' if analysis['setup_type'] == 'near_support' else 'short'
                current_price = analysis['price']
                atr = current['atr'] if not pd.isna(current['atr']) else current_price * 0.01
                
                if signal_type == 'long':
                    entry_price = current_price
                    stop_loss = analysis['levels']['nearest_support'] * 0.995
                    tp1 = current_price + (atr * 1)
                    tp2 = current_price + (atr * 2)
                    tp3 = current_price + (atr * 3)
                else:
                    entry_price = current_price
                    stop_loss = analysis['levels']['nearest_resistance'] * 1.005
                    tp1 = current_price - (atr * 1)
                    tp2 = current_price - (atr * 2)
                    tp3 = current_price - (atr * 3)
                
                return {
                    'signal_type': signal_type,
                    'score': score,
                    'confirmations': confirmations,
                    'current_price': current_price,
                    'entry_price': entry_price,
                    'stop_loss': stop_loss,
                    'stop_percent': abs((entry_price - stop_loss) / entry_price * 100),
                    'tp1': tp1,
                    'tp1_percent': ((tp1 - entry_price) / entry_price * 100) if signal_type == 'long' else ((entry_price - tp1) / entry_price * 100),
                    'tp2': tp2,
                    'tp2_percent': ((tp2 - entry_price) / entry_price * 100) if signal_type == 'long' else ((entry_price - tp2) / entry_price * 100),
                    'tp3': tp3,
                    'tp3_percent': ((tp3 - entry_price) / entry_price * 100) if signal_type == 'long' else ((entry_price - tp3) / entry_price * 100),
                    'volume_ratio': current['volume_ratio'],
                    'rsi': current['rsi'],
                    'valid_minutes': 15,
                    'risk_reward': abs((tp1 - entry_price) / (entry_price - stop_loss)) if entry_price != stop_loss else 1
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Erro check_confirmed_entry: {e}")
            return None
    
    def check_ideal_entry(self, analysis: Dict, df: pd.DataFrame) -> Optional[Dict]:
        """Verifica entrada ideal com múltiplas confirmações"""
        try:
            # Primeiro verificar entrada boa
            good_entry = self.check_confirmed_entry(analysis, df)
            if not good_entry or good_entry['score'] < 70:
                return None
            
            current = df.iloc[-1]
            
            # Verificar condições extras para ser IDEAL
            extra_confirmations = []
            
            # Volume muito alto
            if current['volume_ratio'] > 3:
                extra_confirmations.append(f"Volume Excepcional {current['volume_ratio']:.1f}x")
            
            # Alinhamento de EMAs
            if not pd.isna(current['ema_9']) and not pd.isna(current['ema_21']) and not pd.isna(current['ema_50']):
                if good_entry['signal_type'] == 'long':
                    if current['ema_9'] > current['ema_21'] > current['ema_50']:
                        extra_confirmations.append("EMAs Alinhadas Bullish")
                else:
                    if current['ema_9'] < current['ema_21'] < current['ema_50']:
                        extra_confirmations.append("EMAs Alinhadas Bearish")
            
            # RSI extremo
            if good_entry['signal_type'] == 'long' and current['rsi'] < 35:
                extra_confirmations.append("RSI Extremamente Oversold")
            elif good_entry['signal_type'] == 'short' and current['rsi'] > 65:
                extra_confirmations.append("RSI Extremamente Overbought")
            
            # Se tiver pelo menos 2 confirmações extras
            if len(extra_confirmations) >= 2:
                all_confirmations = good_entry['confirmations'] + extra_confirmations
                
                # Calcular zona de entrada ideal
                entry_zone_low = good_entry['entry_price'] * 0.995
                entry_zone_high = good_entry['entry_price'] * 1.005
                entry_preferred = good_entry['entry_price']
                
                return {
                    'signal_type': good_entry['signal_type'],
                    'probability': min(85 + (len(extra_confirmations) * 3), 95),
                    'current_price': current['close'],
                    'all_confirmations': all_confirmations,
                    'entry_zone_low': entry_zone_low,
                    'entry_zone_high': entry_zone_high,
                    'entry_preferred': entry_preferred,
                    'stop_loss': good_entry['stop_loss'],
                    'stop_percent': good_entry['stop_percent'],
                    'tp1': good_entry['tp1'],
                    'tp1_percent': good_entry['tp1_percent'],
                    'tp2': good_entry['tp2'],
                    'tp2_percent': good_entry['tp2_percent'],
                    'tp3': good_entry['tp3'],
                    'tp3_percent': good_entry['tp3_percent'],
                    'risk_reward': good_entry['risk_reward'],
                    'management': "TP1: 25% | TP2: 50% | TP3: 25%",
                    'main_timeframe': '5m + 1h confirmação',
                    'note': "Setup com múltiplas confirmações e alto volume"
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Erro check_ideal_entry: {e}")
            return None
    
    def get_ohlcv_data(self, symbol: str, timeframe: str = '5m', limit: int = 100) -> Optional[pd.DataFrame]:
        """Obtém dados OHLCV"""
        try:
            ohlcv = self.exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except Exception as e:
            logger.warning(f"Erro dados {symbol} {timeframe}: {e}")
            return None
    
    # ========== LOOP PRINCIPAL ==========
    def run(self):
        """Loop principal do bot"""
        logger.info("🚀 Crypto Analyzer Bot Iniciado")
        logger.info(f"📊 Monitorando Top 50 moedas")
        logger.info(f"🎯 Detecção Inteligente de Suporte/Resistência")
        
        self.alert_history = {}
        
        while True:
            try:
                start_time = time.time()
                
                # Obter top coins
                top_coins = self.get_top_coins(50)
                logger.info(f"📈 Analisando {len(top_coins)} moedas...")
                
                signals_count = 0
                
                # Analisar cada moeda
                for i, symbol in enumerate(top_coins):
                    try:
                        analysis = self.analyze_pair(symbol)
                        
                        if analysis and 'signals' in analysis and analysis['signals']:
                            for signal in analysis['signals']:
                                self.send_telegram_alert(signal['type'], symbol, signal['data'])
                                signals_count += 1
                        
                        # Pausa para não sobrecarregar API
                        if i % 10 == 0:
                            time.sleep(0.3)
                            
                    except Exception as e:
                        logger.debug(f"Erro {symbol}: {e}")
                        continue
                
                elapsed = time.time() - start_time
                sleep_time = max(1, CHECK_INTERVAL - elapsed)
                
                logger.info(f"✅ Análise: {len(top_coins)} moedas | {signals_count} sinais | Próxima em {sleep_time:.0f}s")
                time.sleep(sleep_time)
                
            except KeyboardInterrupt:
                logger.info("👋 Bot interrompido")
                break
            except Exception as e:
                logger.error(f"Erro loop principal: {e}")
                time.sleep(30)

# ========== EXECUÇÃO ==========
if __name__ == "__main__":
    # Testar Telegram
    try:
        test_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(test_url)
        if response.status_code == 200:
            logger.info("✅ Conexão Telegram OK")
        else:
            logger.error("❌ Erro Telegram. Verifique tokens.")
            exit(1)
    except Exception as e:
        logger.error(f"❌ Erro testar Telegram: {e}")
        exit(1)
    
    bot = CryptoAnalyzerBot()
    bot.run()