# AI Query Routing & Deterministic Classification

## 1. Architectural Motivation

A major failure mode in agricultural AI applications is delegating factual, quantitative questions (e.g. *"What is today's onion price in Nagpur?"*) to a Large Language Model (LLM), which frequently hallucinates outdated, plausible-sounding, or incorrect numerical values. 

MarketLink eliminates this by implementing a **deterministic query routing architecture**:
- **Factual Spot Market Prices** are routed exclusively to live/cached **Government AGMARKNET data**.
- **Numerical Future Price Forecasts** are routed exclusively to trained **XGBoost ML regressors**.
- **Geospatial Selling Decisions** are routed exclusively to the **MandiRecommender economics engine**.
- **Agronomy, Storage, and Cultivation Questions** are routed to the **Ollama LLaMA 3 LLM**.
- **Multi-Capability Questions** (e.g. future forecast + selling selection) trigger **orchestrated combined analysis**.

```mermaid
graph TD
    Query["Incoming Farmer Query<br/>(Natural Language)"] --> Classifier["AiQueryClassifier<br/>(Deterministic Pattern Matching)"]
    
    Classifier --> Intent{"Classified Intent"}
    
    Intent -->|Both Future & Selling Indicators| COMBINED["COMBINED_ANALYSIS<br/>Confidence: 0.95"]
    Intent -->|Selling / Mandi Selection Indicators| REC["MANDI_RECOMMENDATION<br/>Confidence: 0.92"]
    Intent -->|Future Temporal / Forecast Indicators| PRED["PRICE_PREDICTION<br/>Confidence: 0.90"]
    Intent -->|Current / Spot Price Indicators| SPOT["MARKET_DATA<br/>Confidence: 0.90"]
    Intent -->|Agronomy / Storage / Cultivation| GEN["GENERAL_ADVISORY<br/>Confidence: 0.88"]
    Intent -->|Ambiguous / Conversational Fallback| FALLBACK["GENERAL_ADVISORY<br/>Confidence: 0.65"]

    COMBINED --> Router["AiQueryRouter"]
    REC --> Router
    PRED --> Router
    SPOT --> Router
    GEN --> Router
    FALLBACK --> Router

    Router -->|predictPrice() + getRecommendation()| CombinedWorkflow["Orchestrated Prediction & Ranking"]
    Router -->|getRecommendation()| RecWorkflow["MandiRecommender (POST /recommend)"]
    Router -->|predictPrice()| PredWorkflow["ModelPredictor (POST /predict)"]
    Router -->|getMarketData()| MarketWorkflow["AGMARKNET (GET /market-data)"]
    Router -->|processGeneralQuery()| OllamaWorkflow["Ollama LLM (POST /query)"]
```

---

## 2. Intent Taxonomy & Execution Matrix

| Intent | Detection Triggers (English & Hinglish) | Target Endpoint | LLM Used? | ML Used? | Gov Data? | Location Required? |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`GENERAL_ADVISORY`** | `how to store`, `cultivate`, `fertilizer`, `spoilage`, `disease`, `pest`, `keede`, `khad`, `kheti` | `POST /api/v1/query` | **Yes (Ollama)** | No | No | No |
| **`MARKET_DATA`** | `today's price`, `current price`, `mandi price`, `aaj ka bhav`, `rate kya hai`, `modal price` | `GET /api/v1/market-data` | **No** | No | **Yes (AGMARKNET)** | No |
| **`PRICE_PREDICTION`** | `predict`, `forecast`, `next week`, `tomorrow`, `expected price`, `kya bhav milega`, `aage ka rate` | `POST /api/v1/predict` | **No** | **Yes (XGBoost)** | Cache / Baseline | No (Uses Market) |
| **`MANDI_RECOMMENDATION`** | `where should I sell`, `which mandi`, `best market`, `kahan bechun`, `kaunsi mandi`, `better price` | `POST /api/v1/recommend` | **No** | **Yes (Economics)** | Yes | **Yes (Mandatory)** |
| **`COMBINED_ANALYSIS`** | Both future price indicators AND market selection indicators | Combined `predict` + `recommend` | Optional synthesis | **Yes (Both)** | Yes | **Yes (for distance)** |

---

## 3. Deep-Dive by Intent

### 3.1 `GENERAL_ADVISORY`
- **Example**: *"What is the best way to store onions to prevent rot?"*
- **Execution**: Routed to `ModelAppClient.processGeneralQuery()` $\rightarrow$ `POST /api/v1/query` $\rightarrow$ Model-app `OllamaService`.
- **Response**: Explains curing, humidity control, ventilation, and antifungal measures.
- **Controlled Failure**: If Ollama is offline, returns structured HTTP 503 rather than inventing answers.

### 3.2 `MARKET_DATA`
- **Example**: *"What is today's onion price in Nagpur?"* or *"aaj ka aloo ka rate kya hai Bareilly mein?"*
- **Execution**: Extracts commodity ("Onion") and market ("Nagpur") $\rightarrow$ `ModelAppClient.getMarketData("Onion", ["Nagpur"], null, 20)` $\rightarrow$ `GET /api/v1/market-data`.
- **Response**: Returns latest modal, minimum, and maximum prices recorded on AGMARKNET with observation date.
- **Why Ollama is Excluded**: Eliminates price fabrication.

### 3.3 `PRICE_PREDICTION`
- **Example**: *"What price can I expect for onions next week?"* or *"bhai next week onion ka kya bhav milega?"*
- **Execution**: Routed to `ModelAppClient.predictPrice(...)` $\rightarrow$ `POST /api/v1/predict` $\rightarrow$ XGBoost ModelPredictor.
- **Response**: Returns next-day predicted price, expected change ($\pm$), expected direction (`UP`/`DOWN`), and reliability score.

### 3.4 `MANDI_RECOMMENDATION`
- **Example**: *"Which mandi should I sell my onions in?"* or *"kahan bechun pyaj achha rate paane ke liye?"*
- **Location Requirement**: Validates that `@Embeddable Location(lat, lon)` is present. If missing, immediately halts with `ModelAppValidationException`.
- **Execution**: Routed to `ModelAppClient.getRecommendation(...)` $\rightarrow$ `POST /api/v1/recommend` $\rightarrow$ MandiRecommender.
- **Response**: Ranks regional mandis by calculated net return after haulage transport deductions.

### 3.5 `COMBINED_ANALYSIS`
- **Example**: *"Which mandi should I sell my onions in next week considering expected prices?"*
- **Execution**:
  1. Calls `predictPrice(...)` for next-day price trend.
  2. Calls `getRecommendation(...)` for geospatial net-return ranking.
  3. Synthesizes a unified response:
     > *"Combined Analysis: Selling in Bareilly yields highest estimated net return of ₹18,570. Next-day prices are projected to trend UP to ₹1,920/quintal."*
