# backend/Api/routes/coin_analysis.py
from __future__ import annotations
import sys
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional

# Adiciona backend ao path
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from analisegrafica.coin_analysis import AdvancedCoinAnalyzer
except ImportError:
    AdvancedCoinAnalyzer = None

router = APIRouter(tags=["coin-analysis"])

class AnalyzeRequest(BaseModel):
    coin: str
    period: Optional[str] = "60d"

@router.post("/coin/analyze")
async def analyze_coin(req: AnalyzeRequest):
    """
    Analisa uma moeda com análise gráfica técnica.
    Retorna zonas de compra/venda, RSI, médias móveis, etc.
    """
    if not AdvancedCoinAnalyzer:
        raise HTTPException(
            status_code=503,
            detail="Módulo de análise gráfica não disponível. Verifique se yfinance está instalado."
        )
    
    try:
        import os
        openai_key = os.getenv("OPENAI_API_KEY")
        analyzer = AdvancedCoinAnalyzer(openai_api_key=openai_key)
        
        result = await analyzer.analyze_coin(req.coin.upper(), req.period)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao analisar moeda: {str(e)}")

@router.get("/coin/analyze")
async def analyze_coin_get(coin: str = Query(..., description="Símbolo da moeda (ex: BTC, ETH)"), 
                           period: str = Query("60d", description="Período de análise")):
    """
    Versão GET da análise de moeda.
    """
    req = AnalyzeRequest(coin=coin, period=period)
    return await analyze_coin(req)


