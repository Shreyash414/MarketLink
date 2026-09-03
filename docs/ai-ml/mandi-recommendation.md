# Mandi Recommendation & Geospatial Economics Engine

## 1. Overview & Objective

The `MandiRecommender` engine (`Model-app/src/recommendation/mandi_recommender.py`) optimizes farmer market selection by computing the true **Net Return** of selling produce across regional mandis.

A common pitfall in farmer decision-making is traveling to a distant mandi offering a higher quoted modal price, only to discover that excessive haulage transport costs and local mandi market fees completely eliminate the price premium. MarketLink solves this by calculating the net profit after all logistics costs are accounted for.

---

## 2. Geospatial Distance Calculation

The engine calculates the great-circle distance between farmer coordinates $(\text{lat}_1, \text{lon}_1)$ and mandi market coordinates $(\text{lat}_2, \text{lon}_2)$ using the **Haversine formula**:

$$a = \sin^2\left(\frac{\Delta\phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta\lambda}{2}\right)$$
$$c = 2 \cdot \text{atan2}\left(\sqrt{a}, \sqrt{1-a}\right)$$
$$d = R \cdot c$$

Where:
- $\phi$ represents latitude in radians.
- $\lambda$ represents longitude in radians.
- $R = 6,371 \text{ km}$ (Earth's mean radius).

---

## 3. Economic Formulas

For a farmer offering $Q$ quintals of produce at distance $d$ km from a candidate mandi with modal price $P$:

### 3.1 Gross Revenue
$$\text{Gross Revenue} = Q \times P$$

### 3.2 Transport Haulage Cost
$$\text{Transport Cost} = d \times Q \times \text{Base Haulage Rate}$$
*Default Base Haulage Rate: ₹0.30 per quintal per kilometer (calibrated against regional small-commercial-vehicle rates).*

### 3.3 Market Cess & Mandi Fees
$$\text{Market Fee} = \text{Gross Revenue} \times \text{Mandi Cess Rate}$$
*Default APMC Cess Rate: 1.0% (0.01) to 1.5%.*

### 3.4 Net Return & Net Effective Price
$$\text{Total Cost} = \text{Transport Cost} + \text{Market Fee}$$
$$\text{Net Return} = \text{Gross Revenue} - \text{Total Cost}$$
$$\text{Net Price per Quintal} = \frac{\text{Net Return}}{Q}$$

---

## 4. Mandi Ranking Algorithm

1. **Candidate Filtering**: Mandis exceeding `max_distance_km` (default 200 km) are excluded from evaluation to ensure transit time does not cause crop spoilage.
2. **Economic Sorting**: All eligible mandis are sorted in strictly descending order of $\text{Net Return}$.
3. **Recommendation Labeling**:
   - The #1 highest net-return market is tagged as `"RECOMMENDED"`.
   - Remaining markets are tagged as `"CONSIDER"`.
4. **Output Generation**: Produces a ranked list containing distance, gross revenue, breakdown of costs, and net return per quintal.
