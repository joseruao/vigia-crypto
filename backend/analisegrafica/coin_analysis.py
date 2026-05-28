# backend/analisegrafica/coin_analysis_advanced.py
import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import traceback

COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "BNB": "binancecoin",
    "XRP": "ripple",
    "ADA": "cardano",
    "DOGE": "dogecoin",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "MATIC": "matic-network",
    "POL": "polygon-ecosystem-token",
    "DOT": "polkadot",
    "LTC": "litecoin",
    "BCH": "bitcoin-cash",
    "XLM": "stellar",
    "ETC": "ethereum-classic",
    "ATOM": "cosmos",
    "NEAR": "near",
    "APT": "aptos",
    "ARB": "arbitrum",
    "OP": "optimism",
    "SUI": "sui",
    "INJ": "injective-protocol",
    "SEI": "sei-network",
    "TIA": "celestia",
    "WIF": "dogwifcoin",
    "BONK": "bonk",
    "HYPE": "hyperliquid",
}

BINANCE_SYMBOLS = {
    "BTC": "BTCUSDT",
    "ETH": "ETHUSDT",
    "SOL": "SOLUSDT",
    "BNB": "BNBUSDT",
    "XRP": "XRPUSDT",
    "ADA": "ADAUSDT",
    "DOGE": "DOGEUSDT",
    "AVAX": "AVAXUSDT",
    "LINK": "LINKUSDT",
    "DOT": "DOTUSDT",
    "LTC": "LTCUSDT",
    "BCH": "BCHUSDT",
    "NEAR": "NEARUSDT",
    "APT": "APTUSDT",
    "ARB": "ARBUSDT",
    "OP": "OPUSDT",
    "SUI": "SUIUSDT",
}

COINBASE_PRODUCTS = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "XRP": "XRP-USD",
    "ADA": "ADA-USD",
    "DOGE": "DOGE-USD",
    "AVAX": "AVAX-USD",
    "LINK": "LINK-USD",
    "DOT": "DOT-USD",
    "LTC": "LTC-USD",
    "BCH": "BCH-USD",
    "NEAR": "NEAR-USD",
    "APT": "APT-USD",
    "ARB": "ARB-USD",
    "OP": "OP-USD",
    "SUI": "SUI-USD",
}

class AdvancedCoinAnalyzer:
    def __init__(self, openai_api_key: str = None):
        self.supported_indicators = ['RSI', 'Moving_Averages', 'Support_Resistance', 'Volume', 'Fibonacci', 'Trend']
        self.openai_api_key = openai_api_key
    
    async def analyze_coin(self, coin: str, period: str = "60d") -> Dict:
        """Analisa uma moeda com zonas de compra/venda detalhadas"""
        try:
            print(f"Analisando {coin}...")
            
            # 1. Buscar dados históricos (período maior para melhor análise)
            data = await self._fetch_coin_data(coin, period)
            if data is None:
                return {"error": f"Não foi possível obter dados para {coin}"}
            
            # 2. Calcular indicadores técnicos avançados
            analysis = await self._calculate_advanced_indicators(data, coin)
            
            # 3. Definir zonas de trading
            trading_zones = await self._define_trading_zones(analysis, data)
            
            # 4. Gerar análise detalhada
            detailed_analysis = await self._generate_detailed_analysis(analysis, trading_zones, coin)
            
            return {
                "coin": coin,
                "timestamp": datetime.now().isoformat(),
                "current_price": analysis['current_price'],
                "analysis": analysis,
                "trading_zones": trading_zones,
                "recommendations": detailed_analysis,
                "summary": await self._generate_ai_summary(analysis, trading_zones, coin) if self.openai_api_key else None
            }
            
        except Exception as e:
            return {"error": f"Erro na análise: {str(e)}"}
    
    async def _fetch_coin_data(self, coin: str, period: str) -> Optional[pd.DataFrame]:
        """Busca dados históricos da moeda"""
        try:
            return self._fetch_fallback_data(coin, period)
            hist = pd.DataFrame()
            
            if hist.empty:
                print(f"Nenhum dado encontrado para {coin}")
                return self._fetch_fallback_data(coin, period)
                
            print(f"Dados obtidos: {len(hist)} candles para {coin}")
            return hist
        except Exception as e:
            print(f"Erro ao buscar dados para {coin}: {e}")
            return self._fetch_fallback_data(coin, period)

    def _fetch_fallback_data(self, coin: str, period: str) -> Optional[pd.DataFrame]:
        for fetcher in (self._fetch_coinbase_data, self._fetch_gateio_data, self._fetch_binance_data, self._fetch_coingecko_data):
            data = fetcher(coin, period)
            if data is not None:
                return data
        return None

    def _fetch_gateio_data(self, coin: str, period: str) -> Optional[pd.DataFrame]:
        """Fallback sem chave para tokens listados na Gate.io, como HYPE."""
        pair = f"{coin.upper()}_USDT"
        try:
            limit = min(max(self._period_to_days(period), 2), 1000)
            response = requests.get(
                "https://api.gateio.ws/api/v4/spot/candlesticks",
                params={"currency_pair": pair, "interval": "1d", "limit": limit},
                timeout=15,
            )
            response.raise_for_status()
            rows = []
            for item in response.json() or []:
                timestamp, volume, close, high, low, open_price = item[:6]
                rows.append({
                    "Date": datetime.fromtimestamp(int(timestamp)),
                    "Open": float(open_price),
                    "High": float(high),
                    "Low": float(low),
                    "Close": float(close),
                    "Volume": float(volume),
                })

            if len(rows) < 2:
                return None

            hist = pd.DataFrame(rows).sort_values("Date").set_index("Date")
            print(f"Dados obtidos via Gate.io: {len(hist)} candles para {coin}")
            return hist
        except Exception as e:
            print(f"Erro Gate.io para {coin}: {e}")
            return None

    def _fetch_coinbase_data(self, coin: str, period: str) -> Optional[pd.DataFrame]:
        """Fallback sem chave pela Coinbase Exchange public API."""
        product = COINBASE_PRODUCTS.get(coin.upper())
        if not product:
            return None

        try:
            days = min(max(self._period_to_days(period), 2), 300)
            end = datetime.utcnow()
            start = end - timedelta(days=days)
            response = requests.get(
                f"https://api.exchange.coinbase.com/products/{product}/candles",
                params={
                    "granularity": 86400,
                    "start": start.isoformat(),
                    "end": end.isoformat(),
                },
                timeout=15,
            )
            response.raise_for_status()
            rows = []
            for item in response.json() or []:
                timestamp, low, high, open_price, close, volume = item[:6]
                rows.append({
                    "Date": datetime.fromtimestamp(timestamp),
                    "Open": float(open_price),
                    "High": float(high),
                    "Low": float(low),
                    "Close": float(close),
                    "Volume": float(volume),
                })

            if len(rows) < 2:
                return None

            hist = pd.DataFrame(rows).sort_values("Date").set_index("Date")
            print(f"Dados obtidos via Coinbase: {len(hist)} candles para {coin}")
            return hist
        except Exception as e:
            print(f"Erro Coinbase para {coin}: {e}")
            return None

    def _fetch_binance_data(self, coin: str, period: str) -> Optional[pd.DataFrame]:
        """Fallback sem chave para moedas grandes quando Yahoo/CoinGecko limitam."""
        symbol = BINANCE_SYMBOLS.get(coin.upper())
        if not symbol:
            return None

        try:
            limit = min(max(self._period_to_days(period), 2), 1000)
            response = requests.get(
                "https://api.binance.com/api/v3/klines",
                params={"symbol": symbol, "interval": "1d", "limit": limit},
                timeout=15,
            )
            response.raise_for_status()
            rows = []
            for item in response.json() or []:
                open_time, open_price, high, low, close, volume = item[:6]
                rows.append({
                    "Date": datetime.fromtimestamp(open_time / 1000),
                    "Open": float(open_price),
                    "High": float(high),
                    "Low": float(low),
                    "Close": float(close),
                    "Volume": float(volume),
                })

            if len(rows) < 2:
                return None

            hist = pd.DataFrame(rows).set_index("Date")
            print(f"Dados obtidos via Binance: {len(hist)} candles para {coin}")
            return hist
        except Exception as e:
            print(f"Erro Binance para {coin}: {e}")
            return None

    def _fetch_coingecko_data(self, coin: str, period: str) -> Optional[pd.DataFrame]:
        """Fallback gratuito para quando o Yahoo Finance falha no Render."""
        coin_id = COINGECKO_IDS.get(coin.upper())
        if not coin_id:
            print(f"Sem fallback CoinGecko configurado para {coin}")
            return None

        try:
            days = self._period_to_days(period)
            response = requests.get(
                f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart",
                params={"vs_currency": "usd", "days": days, "interval": "daily"},
                timeout=15,
            )
            response.raise_for_status()
            payload = response.json()
            prices = payload.get("prices") or []
            volumes = payload.get("total_volumes") or []

            rows = []
            for index, item in enumerate(prices):
                timestamp_ms, price = item
                volume = volumes[index][1] if index < len(volumes) else 0
                rows.append({
                    "Date": datetime.fromtimestamp(timestamp_ms / 1000),
                    "Open": price,
                    "High": price,
                    "Low": price,
                    "Close": price,
                    "Volume": volume,
                })

            if len(rows) < 2:
                print(f"CoinGecko sem dados suficientes para {coin}")
                return None

            hist = pd.DataFrame(rows).set_index("Date")
            print(f"Dados obtidos via CoinGecko: {len(hist)} candles para {coin}")
            return hist
        except Exception as e:
            print(f"Erro CoinGecko para {coin}: {e}")
            return None

    def _period_to_days(self, period: str) -> int:
        try:
            if period.endswith("d"):
                return max(1, int(period[:-1]))
            if period.endswith("mo"):
                return max(1, int(period[:-2]) * 30)
            if period.endswith("y"):
                return max(1, int(period[:-1]) * 365)
        except Exception:
            pass
        return 60
    
    async def _calculate_advanced_indicators(self, data: pd.DataFrame, coin: str) -> Dict:
        """Calcula indicadores avançados"""
        current_price = float(data['Close'].iloc[-1])
        
        # RSI
        rsi = self._calculate_rsi(data['Close'])
        
        # Médias Móveis
        sma_20 = data['Close'].rolling(window=20, min_periods=1).mean()
        sma_50 = data['Close'].rolling(window=50, min_periods=1).mean()
        sma_200 = data['Close'].rolling(window=200, min_periods=1).mean()
        
        # Tendência
        trend_strength = self._calculate_trend_strength(data)
        
        # Volatilidade
        volatility = self._calculate_volatility(data)
        
        # Fibonacci Levels
        fib_levels = self._calculate_fibonacci_levels(data)
        
        # Volume analysis
        volume_analysis = self._analyze_volume(data)
        
        return {
            'current_price': round(current_price, 2),
            'rsi': round(rsi, 2),
            'moving_averages': {
                'sma_20': round(float(sma_20.iloc[-1]), 2),
                'sma_50': round(float(sma_50.iloc[-1]), 2),
                'sma_200': round(float(sma_200.iloc[-1]), 2) if not pd.isna(sma_200.iloc[-1]) else current_price,
            },
            'trend': trend_strength,
            'volatility': volatility,
            'fibonacci': fib_levels,
            'volume': volume_analysis,
            'support_resistance': await self._find_dynamic_support_resistance(data)
        }
    
    def _calculate_rsi(self, prices, window=14):
        """Calcula RSI manualmente"""
        try:
            if len(prices) < window + 1:
                return 50
                
            deltas = np.diff(prices)
            gains = np.where(deltas > 0, deltas, 0)
            losses = np.where(deltas < 0, -deltas, 0)
            
            avg_gains = pd.Series(gains).rolling(window=window, min_periods=1).mean()
            avg_losses = pd.Series(losses).rolling(window=window, min_periods=1).mean()
            
            rs = avg_gains / np.where(avg_losses == 0, 0.001, avg_losses)
            rsi = 100 - (100 / (1 + rs))
            
            return rsi.iloc[-1] if not pd.isna(rsi.iloc[-1]) else 50
        except:
            return 50
    
    def _calculate_trend_strength(self, data: pd.DataFrame) -> Dict:
        """Calcula força e direção da tendência"""
        prices = data['Close'].tail(50)
        sma_20 = prices.rolling(20).mean()
        sma_50 = prices.rolling(50).mean()
        
        current_sma_20 = sma_20.iloc[-1] if not pd.isna(sma_20.iloc[-1]) else prices.iloc[-1]
        current_sma_50 = sma_50.iloc[-1] if not pd.isna(sma_50.iloc[-1]) else prices.iloc[-1]
        
        if current_sma_20 > current_sma_50:
            direction = "UPTREND"
            strength = min(((current_sma_20 - current_sma_50) / current_sma_50) * 100, 20)
        else:
            direction = "DOWNTREND" 
            strength = min(((current_sma_50 - current_sma_20) / current_sma_20) * 100, 20)
        
        return {"direction": direction, "strength": round(strength, 1)}
    
    def _calculate_volatility(self, data: pd.DataFrame) -> float:
        """Calcula volatilidade (desvio padrão dos retornos)"""
        returns = data['Close'].pct_change().dropna()
        return round(returns.std() * 100, 2)  # Em percentagem
    
    def _calculate_fibonacci_levels(self, data: pd.DataFrame) -> Dict:
        """Calcula níveis de Fibonacci"""
        closes = data['Close'].tail(60)
        high = float(closes.max())
        low = float(closes.min())
        diff = high - low
        
        return {
            'high': round(high, 2),
            'low': round(low, 2),
            'levels': {
                '0.236': round(high - diff * 0.236, 2),
                '0.382': round(high - diff * 0.382, 2),
                '0.5': round(high - diff * 0.5, 2),
                '0.618': round(high - diff * 0.618, 2),
                '0.786': round(high - diff * 0.786, 2)
            }
        }
    
    def _analyze_volume(self, data: pd.DataFrame) -> Dict:
        """Analisa volume"""
        current_volume = int(data['Volume'].iloc[-1])
        avg_volume_20 = data['Volume'].tail(20).mean()
        volume_ratio = current_volume / avg_volume_20 if avg_volume_20 > 0 else 1
        
        return {
            'current': current_volume,
            'ratio_20d': round(volume_ratio, 2),
            'trend': 'HIGH' if volume_ratio > 1.5 else 'LOW' if volume_ratio < 0.7 else 'NORMAL'
        }
    
    async def _find_dynamic_support_resistance(self, data: pd.DataFrame) -> Dict:
        """Encontra suporte e resistência dinâmicos"""
        closes = data['Close'].tail(30)
        
        # Suporte: mínimo recente com buffer
        support = float(closes.min())
        dynamic_support = support * 0.98  # 2% abaixo do mínimo
        
        # Resistência: máximo recente com buffer  
        resistance = float(closes.max())
        dynamic_resistance = resistance * 1.02  # 2% acima do máximo
        
        current = float(closes.iloc[-1])
        position_pct = round(((current - dynamic_support) / (dynamic_resistance - dynamic_support)) * 100, 1) if dynamic_resistance != dynamic_support else 50
        
        return {
            'static_support': round(support, 2),
            'static_resistance': round(resistance, 2),
            'dynamic_support': round(dynamic_support, 2),
            'dynamic_resistance': round(dynamic_resistance, 2),
            'current_position': position_pct
        }
    
    async def _define_trading_zones(self, analysis: Dict, data: pd.DataFrame) -> Dict:
        """Define zonas de compra e venda detalhadas"""
        current_price = analysis['current_price']
        support = analysis['support_resistance']['dynamic_support']
        resistance = analysis['support_resistance']['dynamic_resistance']
        
        # ZONAS DE COMPRA
        buy_zones = {
            "zona_compra_agressiva": {
                "range": f"{support * 0.95:.2f} - {support:.2f}",
                "descricao": "COMPRA FORTE - Preço perto do suporte principal",
                "confianca": "ALTA",
                "alvo_stop_loss": support * 0.92
            },
            "zona_compra_otima": {
                "range": f"{support:.2f} - {support * 1.02:.2f}",
                "descricao": "COMPRA ÓTIMA - Entrada após teste de suporte",
                "confianca": "MUITO ALTA", 
                "alvo_stop_loss": support * 0.95
            },
            "zona_compra_conservadora": {
                "range": f"{support * 1.02:.2f} - {current_price:.2f}",
                "descricao": "COMPRA CONSERVADORA - Esperar confirmação",
                "confianca": "MÉDIA",
                "alvo_stop_loss": support * 0.98
            }
        }
        
        # ZONAS DE VENDA
        sell_zones = {
            "zona_venda_parcial": {
                "range": f"{resistance * 0.98:.2f} - {resistance:.2f}",
                "descricao": "VENDA PARCIAL - Primeiro alvo de lucro",
                "confianca": "ALTA",
                "percentual_vender": "30%"
            },
            "zona_venda_principal": {
                "range": f"{resistance:.2f} - {resistance * 1.05:.2f}",
                "descricao": "VENDA PRINCIPAL - Alvo máximo",
                "confianca": "MUITO ALTA",
                "percentual_vender": "50%"
            },
            "zona_venda_agressiva": {
                "range": f"{resistance * 1.05:.2f} +",
                "descricao": "VENDA AGRESSIVA - Momento FOMO",
                "confianca": "MÉDIA", 
                "percentual_vender": "20%"
            }
        }
        
        # ZONA NEUTRA
        neutral_zone = {
            "range": f"{current_price:.2f} - {resistance * 0.98:.2f}",
            "descricao": "ZONA DE OBSERVAÇÃO - Aguardar confirmação",
            "acao": "AGUARDAR",
            "motivo": "Preço entre suporte e resistência sem clara direção"
        }
        
        return {
            "compra": buy_zones,
            "venda": sell_zones, 
            "neutra": neutral_zone,
            "preco_atual": current_price,
            "posicao_atual": self._get_current_zone(current_price, buy_zones, sell_zones, neutral_zone)
        }
    
    def _get_current_zone(self, current_price, buy_zones, sell_zones, neutral_zone):
        """Determina em que zona está o preço atual"""
        # Extrair ranges
        buy_range = list(buy_zones.values())[-1]['range']  # Última zona de compra
        sell_range = list(sell_zones.values())[0]['range']  # Primeira zona de venda
        
        buy_max = float(buy_range.split(' - ')[1])
        sell_min = float(sell_range.split(' - ')[0])
        
        if current_price <= buy_max:
            return "ZONA_DE_COMPRA"
        elif current_price >= sell_min:
            return "ZONA_DE_VENDA" 
        else:
            return "ZONA_NEUTRA"
    
    async def _generate_detailed_analysis(self, analysis: Dict, trading_zones: Dict, coin: str) -> Dict:
        """Gera análise detalhada com ações específicas"""
        actions = []
        score = 50
        
        # Análise RSI
        rsi = analysis['rsi']
        if rsi < 25:
            actions.append("🎯 RSI EXTREMAMENTE OVERSOLD - OPORTUNIDADE RARA DE COMPRA")
            score += 25
        elif rsi < 30:
            actions.append("✅ RSI OVERSOLD - BOA OPORTUNIDADE DE COMPRA")
            score += 15
        elif rsi > 75:
            actions.append("⚠️ RSI OVERBOUGHT - CONSIDERAR VENDA")
            score -= 20
        elif rsi > 70:
            actions.append("📉 RSI ELEVADO - CUIDADO COM COMPRAS")
            score -= 10
        
        # Análise de Tendência
        if analysis['trend']['direction'] == "UPTREND":
            actions.append("📈 TENDÊNCIA DE ALTA - FAVORÁVEL PARA COMPRAS")
            score += 10
        else:
            actions.append("📉 TENDÊNCIA DE BAIXA - CUIDADO EXTRA")
            score -= 5
        
        # Análise de Posição
        current_zone = trading_zones['posicao_atual']
        current_position = analysis.get('support_resistance', {}).get('current_position', 50)
        if current_zone == "ZONA_DE_COMPRA" and (rsi >= 70 or current_position >= 80):
            actions.append("PRECO ESTICADO DENTRO DO RANGE - MELHOR AGUARDAR PULLBACK")
            strategy = self._generate_trading_strategy(analysis, trading_zones)
            return {
                'acao_principal': "AGUARDAR PULLBACK",
                'confianca': self._get_confidence(score),
                'score': min(max(score, 0), 100),
                'acoes_recomendadas': actions,
                'estrategia_trading': strategy,
                'alerta_risco': self._get_risk_alert(analysis)
            }
        if current_zone == "ZONA_DE_COMPRA":
            actions.append("💰 PREÇO NA ZONA DE COMPRA - MOMENTO ESTRATÉGICO")
            score += 15
        elif current_zone == "ZONA_DE_VENDA":
            actions.append("💸 PREÇO NA ZONA DE VENDA - CONSIDERAR REALIZAR LUCROS")
            score -= 10
        
        # Estratégia de Trading
        strategy = self._generate_trading_strategy(analysis, trading_zones)
        
        return {
            'acao_principal': self._get_main_action(score),
            'confianca': self._get_confidence(score),
            'score': min(max(score, 0), 100),
            'acoes_recomendadas': actions,
            'estrategia_trading': strategy,
            'alerta_risco': self._get_risk_alert(analysis)
        }
    
    def _generate_trading_strategy(self, analysis: Dict, trading_zones: Dict) -> Dict:
        """Gera estratégia de trading específica"""
        current_zone = trading_zones['posicao_atual']
        
        if current_zone == "ZONA_DE_COMPRA":
            return {
                "estrategia": "ACCUMULATION",
                "plano": "Comprar em scale nas zonas definidas",
                "alocacao": "60% na zona ótima, 30% na agressiva, 10% na conservadora",
                "stop_loss": f"{trading_zones['compra']['zona_compra_agressiva']['alvo_stop_loss']:.2f}",
                "targets": [
                    f"{trading_zones['venda']['zona_venda_parcial']['range']} (30%)",
                    f"{trading_zones['venda']['zona_venda_principal']['range']} (50%)", 
                    f"{trading_zones['venda']['zona_venda_agressiva']['range']} (20%)"
                ]
            }
        elif current_zone == "ZONA_DE_VENDA":
            return {
                "estrategia": "PROFIT_TAKING", 
                "plano": "Vender em scale realizando lucros",
                "alocacao": "30% na zona parcial, 50% na principal, 20% na agressiva",
                "recompra": f"Aguardar retorno para {trading_zones['compra']['zona_compra_otima']['range']}",
                "observacao": "Não vender tudo de uma vez - fazer scale"
            }
        else:
            return {
                "estrategia": "WAIT_AND_SEE",
                "plano": "Aguardar confirmação de direção",
                "acao": "Não entrar em novas posições",
                "observacao": "Mercado em consolidação - esperar breakout"
            }
    
    def _get_main_action(self, score: int) -> str:
        if score >= 70: return "COMPRA FORTE"
        if score >= 60: return "COMPRA"
        if score >= 50: return "COMPRA LEVE" 
        if score >= 40: return "AGUARDAR"
        if score >= 30: return "VENDA LEVE"
        return "VENDA FORTE"
    
    def _get_confidence(self, score: int) -> str:
        if score >= 80 or score <= 20: return "MUITO ALTA"
        if score >= 70 or score <= 30: return "ALTA"
        if score >= 60 or score <= 40: return "MÉDIA"
        return "BAIXA"
    
    def _get_risk_alert(self, analysis: Dict) -> str:
        if analysis['volatility'] > 15:
            return "ALTA VOLATILIDADE - POSICIONES PEQUENAS"
        if analysis['rsi'] > 80:
            return "RSI EXTREMO - CUIDADO COM REVERSÃO"
        return "RISCO MODERADO"
    
    async def _generate_ai_summary(self, analysis: Dict, trading_zones: Dict, coin: str) -> str:
        """Gera resumo usando OpenAI"""
        if not self.openai_api_key:
            return "OpenAI API key não configurada"
        
        try:
            # Aqui iria a chamada à API OpenAI
            # Por enquanto retornamos um resumo manual
            return self._generate_manual_summary(analysis, trading_zones, coin)
            
        except:
            return self._generate_manual_summary(analysis, trading_zones, coin)
    
    def _generate_manual_summary(self, analysis: Dict, trading_zones: Dict, coin: str) -> str:
        """Gera resumo manual quando OpenAI não está disponível"""
        current_zone = trading_zones['posicao_atual']
        rsi = analysis['rsi']
        
        if current_zone == "ZONA_DE_COMPRA" and rsi < 30:
            return f"🎯 OPORTUNIDADE DE COMPRA EM {coin}! Preço na zona de acumulação com RSI oversold. Estratégia: Comprar em scale nas zonas definidas. Stop loss: ${trading_zones['compra']['zona_compra_agressiva']['alvo_stop_loss']:.2f}"
        elif current_zone == "ZONA_DE_VENDA":
            return f"💸 MOMENTO DE VENDA EM {coin}. Preço nas zonas de realização de lucro. Estratégia: Vender em scale, não vender tudo de uma vez."
        else:
            return f"⚖️ {coin} EM CONSOLIDAÇÃO. Aguardar confirmação de direção antes de entrar em novas posições."

# Teste
async def main():
    analyzer = AdvancedCoinAnalyzer()
    result = await analyzer.analyze_coin("BTC")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
