"""
Economics & Transport Cost Engine.
Calculates transport costs, market fees, gross revenues, and net farmer returns.
"""
from dataclasses import dataclass

from src.config.config import (
    DEFAULT_MARKET_FEE_PER_QUINTAL,
    DEFAULT_TRANSPORT_COST_PER_QUINTAL_KM,
)


@dataclass
class EconomicsOutput:
    distance_km: float
    transport_cost: float
    market_fee: float
    gross_revenue: float
    total_cost: float
    net_return: float
    net_price_per_quintal: float


def calculate_transport_cost(
    distance_km: float,
    quantity_quintals: float,
    rate_per_quintal_km: float = DEFAULT_TRANSPORT_COST_PER_QUINTAL_KM
) -> float:
    """
    Calculate transportation cost in Rupees.

    Parameters
    ----------
    distance_km : float
        Distance to mandi in kilometers.
    quantity_quintals : float
        Quantity of produce in quintals.
    rate_per_quintal_km : float
        Transport cost tariff rate in ₹ / quintal / km.
    """
    if distance_km < 0 or quantity_quintals <= 0 or rate_per_quintal_km < 0:
        raise ValueError("Invalid parameters for transport cost calculation.")
    return float(distance_km * rate_per_quintal_km * quantity_quintals)


def calculate_market_fee(
    quantity_quintals: float,
    fee_per_quintal: float = DEFAULT_MARKET_FEE_PER_QUINTAL
) -> float:
    """
    Calculate market fee in Rupees.
    """
    if quantity_quintals <= 0 or fee_per_quintal < 0:
        raise ValueError("Invalid parameters for market fee calculation.")
    return float(quantity_quintals * fee_per_quintal)


def calculate_economics(
    distance_km: float,
    quantity_quintals: float,
    predicted_price: float,
    transport_rate: float = DEFAULT_TRANSPORT_COST_PER_QUINTAL_KM,
    market_fee_rate: float = DEFAULT_MARKET_FEE_PER_QUINTAL
) -> EconomicsOutput:
    """
    Calculate complete financial breakdown for selling at a specific mandi.
    """
    transport_cost = calculate_transport_cost(
        distance_km=distance_km,
        quantity_quintals=quantity_quintals,
        rate_per_quintal_km=transport_rate
    )
    market_fee = calculate_market_fee(
        quantity_quintals=quantity_quintals,
        fee_per_quintal=market_fee_rate
    )
    gross_revenue = float(predicted_price * quantity_quintals)
    total_cost = transport_cost + market_fee
    net_return = gross_revenue - total_cost
    net_price_per_quintal = net_return / quantity_quintals if quantity_quintals > 0 else 0.0

    return EconomicsOutput(
        distance_km=round(distance_km, 2),
        transport_cost=round(transport_cost, 2),
        market_fee=round(market_fee, 2),
        gross_revenue=round(gross_revenue, 2),
        total_cost=round(total_cost, 2),
        net_return=round(net_return, 2),
        net_price_per_quintal=round(net_price_per_quintal, 2)
    )
