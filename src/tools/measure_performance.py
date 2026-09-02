"""
Performance benchmark script measuring pipeline inference execution latency.
"""
import time
from src.recommendation.mandi_recommender import recommend_canonical

COMMODITIES_TO_TEST = [
    ("Potato", 27.1767, 78.0081),
    ("Tomato", 13.1367, 78.1292),
    ("Wheat", 22.7196, 75.8577),
    ("Onion", 28.6139, 77.2090),
    ("Rice", 23.2324, 87.8615),
]

def main():
    print("=" * 80)
    print(f"{'COMMODITY':<12} | {'RUN 1 (ms)':<12} | {'RUN 2 (WARM) (ms)':<18} | {'TOP MANDI':<12} | {'STATUS'}")
    print("=" * 80)

    for comm, lat, lon in COMMODITIES_TO_TEST:
        # Run 1 (Cold / First fetch)
        t0 = time.perf_counter()
        res1 = recommend_canonical(farmer_latitude=lat, farmer_longitude=lon, quantity_quintals=10.0, commodity=comm, farmer_facing=True)
        t1 = time.perf_counter()
        ms1 = (t1 - t0) * 1000.0

        # Run 2 (Warm / In-memory cache)
        t2 = time.perf_counter()
        res2 = recommend_canonical(farmer_latitude=lat, farmer_longitude=lon, quantity_quintals=10.0, commodity=comm, farmer_facing=True)
        t3 = time.perf_counter()
        ms2 = (t3 - t2) * 1000.0

        top_mandi = res1.recommended_mandi
        status = "ALLOWED" if top_mandi != "NONE" else "BLOCKED"

        print(f"{comm:<12} | {ms1:<12.2f} | {ms2:<18.2f} | {top_mandi:<12} | {status}")

    print("=" * 80)

if __name__ == "__main__":
    main()
