# AGMARKNET Market Data Ingestion & Caching

## 1. Overview & Data Provenance

MarketLink ingests real-time agricultural market data from the **Open Government Data (OGD) Platform India (data.gov.in)**, specifically the AGMARKNET daily modal price and arrival feed.

- **Upstream Source**: Ministry of Agriculture & Farmers Welfare / AGMARKNET
- **API Endpoint Resource**: `https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070`
- **Authentication**: Provided via `api-key` query parameter bound to `DATA_GOV_API_KEY`
- **Internal Service**: `Model-app/src/data/ingestion/current_data_fetcher.py` and `market_data_service.py`

---

## 2. Ingestion Pipeline Architecture

```mermaid
graph TD
    Client[Core Backend Request] --> Svc[MarketDataService]
    
    Svc --> CheckCache{Cache Valid & Fresh?}
    CheckCache -->|Yes| ReturnCache[Return Cached Records<br/>data_source: CACHE]
    
    CheckCache -->|No / Miss| LiveFetch[CurrentDataFetcher.fetch_live()]
    LiveFetch --> CallGov[data.gov.in API Call<br/>Timeout: 5s, Max Retries: 2]
    
    CallGov -->|Success| SaveCache[Store in Local JSON Cache<br/>Update Timestamp]
    SaveCache --> ReturnLive[Return Live Records<br/>data_source: LIVE]
    
    CallGov -->|Timeout / Network Error| FallbackCache[Load Last Known Good Cache<br/>data_source: CACHE]
    FallbackCache --> ReturnFallback[Return Cache with Warning]
    
    FallbackCache -->|No Cache Exists| Error[Return 502 Bad Gateway<br/>data_source: ERROR]
```

---

## 3. Resilience & Timeout Handling

### 3.1 Network Timeout Policy
External government endpoints are prone to rate limiting and latency variance during peak morning market hours. The `CurrentDataFetcher` enforces:
- **Connection Timeout**: 5 seconds.
- **Read Timeout**: 5 seconds.
- **Retry Attempts**: 2 attempts with a 1-second backoff.
- **Fast Fail**: If the API fails consecutively, the service immediately falls back to cache without stalling caller threads.

### 3.2 Cache Architecture
- Observations are indexed by commodity and market name.
- Records retain historical metadata (`date`, `modal_price`, `min_price`, `max_price`, `arrivals_tonnes`).
- Returned payloads explicitly declare the data source:
  - `"LIVE"`: Freshly fetched from government server.
  - `"CACHE"`: Retrieved from local cache due to offline state or rate limits.
  - `"ERROR"`: No data available in either live API or cache.

---

## 4. Configuration & Security

The government API key must be injected via environment variables:
```bash
# .env file
DATA_GOV_API_KEY=your_registered_datagov_api_key_here
```

> [!CAUTION]
> **Zero API Key Leakage**:
> The `DATA_GOV_API_KEY` is loaded privately inside Python using `pydantic-settings`. It is **never** transmitted to Core Backend, never passed to Android, and never logged in debug outputs.
