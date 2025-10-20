# backend/analisegrafica/coin_analysis_advanced.py
import requests
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import yfinance as yf
from typing import Dict, List, Optional
import traceback

class AdvancedCoinAnalyzer:
    def __init__(self, openai_api_key: str = None):
        self.supported_indicators = ['RSI', 'Moving_Averages', 'Support_Resistance', 'Volume', 'Fibonacci', 'Trend']
        self.openai_api_key = openai_api_key
    
    async def analyze_coin(self, coin: str, period: str = "60d") -> Dict:
        """Analisa uma moeda com zonas de compra/venda detalhadas"""
        try:
            print(f"🔍 Analisando {coin}...")
            
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
    
    async def _generate_ai_summary(self, analysis: Dict, trading_zones: Dict, coin: str) -> str:
        """Gera resumo usando OpenAI"""
        if not self.openai_api_key:
            return "OpenAI API key não configurada"
        
        try:
            prompt = f"""
            Analise técnica do {coin}:
            
            PREÇO ATUAL: ${analysis['current_price']}
            RSI: {analysis['rsi']}
            ZONA ATUAL: {trading_zones['posicao_atual']}
            
            ZONAS DE COMPRA:
            {json.dumps(trading_zones['compra'], indent=2)}
            
            ZONAS DE VENDA:
            {json.dumps(trading_zones['venda'], indent=2)}
            
            Gere um resumo conciso em português com:
            1. Situação atual em 1 frase
            2. Melhor estratégia 
            3. Principais riscos
            4. Conclusão final
            
            Seja direto e prático.
            """
            
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
    
    # ... (outros métodos auxiliares do código anterior - _calculate_rsi, _fetch_coin_data, etc.)
    
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

# Teste
async def main():
    analyzer = AdvancedCoinAnalyzer()
    result = await analyzer.analyze_coin("BTC")
    print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())