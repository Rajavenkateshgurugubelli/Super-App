import logging
import time
from app.models import Currency

logger = logging.getLogger("RoutingEngine")

# Mock Liquidity Pools & Baseline Conversion Rates (USD Base)
# In production, these would be fetched dynamically from DeFi pools or internal treasury systems
FX_RATES_USD_BASE = {
    Currency.USD: 1.0,
    Currency.INR: 83.12,
    Currency.EUR: 0.918
}

# Transaction processing fee matrix by path (bps). E.g., 50 = 0.5%
FEE_BPS = {
    (Currency.USD, Currency.USD): 0,
    (Currency.USD, Currency.INR): 50,
    (Currency.INR, Currency.USD): 60,
    (Currency.USD, Currency.EUR): 30,
    (Currency.EUR, Currency.USD): 40,
    (Currency.EUR, Currency.INR): 80,
    (Currency.INR, Currency.EUR): 80
}

def calculate_optimal_route(amount: float, from_currency: Currency, to_currency: Currency) -> dict:
    """
    Calculates the best fee and final amount for cross-border transaction routing.
    In phase 4, we evaluate direct routing vs synthetic triangular arbitrage (e.g. INR -> USD -> EUR)
    """
    logger.info(f"Calculating routing path for {amount} {from_currency.name} -> {to_currency.name}")
    
    if from_currency == to_currency:
        return {
            "path": [from_currency.name],
            "fee_amount": 0.0,
            "estimated_time_ms": 100,
            "final_amount": amount,
            "rate": 1.0
        }

    # Calculate direct exchange rate (ignoring liquidity spread for simplicity)
    base_rate = FX_RATES_USD_BASE.get(to_currency, 1.0) / FX_RATES_USD_BASE.get(from_currency, 1.0)
    
    # 1. Direct path
    direct_bps = FEE_BPS.get((from_currency, to_currency), 100) # Default 1% if undefined
    direct_fee = amount * (direct_bps / 10000.0)
    direct_final = (amount - direct_fee) * base_rate
    
    # 2. Triangular path (Routing via USD as the reserve anchor)
    triangle_final = -1.0
    triangle_fee = 0.0
    
    if from_currency != Currency.USD and to_currency != Currency.USD:
        leg1_bps = FEE_BPS.get((from_currency, Currency.USD), 100)
        leg2_bps = FEE_BPS.get((Currency.USD, to_currency), 100)
        
        fee1 = amount * (leg1_bps / 10000.0)
        usd_amount = (amount - fee1) * (1.0 / FX_RATES_USD_BASE.get(from_currency, 1.0))
        
        fee2 = usd_amount * (leg2_bps / 10000.0)
        triangle_final = (usd_amount - fee2) * FX_RATES_USD_BASE.get(to_currency, 1.0)
        triangle_fee = fee1 + (fee2 * FX_RATES_USD_BASE.get(from_currency, 1.0)) # Rough back-calculation to source currency
        
    # Decide best route
    if triangle_final > direct_final:
        return {
            "path": [from_currency.name, Currency.USD.name, to_currency.name],
            "fee_amount": round(triangle_fee, 4),
            "estimated_time_ms": 800,
            "final_amount": round(triangle_final, 4),
            "rate": round(triangle_final / amount, 6)
        }
    else:
        return {
            "path": [from_currency.name, to_currency.name],
            "fee_amount": round(direct_fee, 4),
            "estimated_time_ms": 400,
            "final_amount": round(direct_final, 4),
            "rate": round(base_rate, 6)
        }
