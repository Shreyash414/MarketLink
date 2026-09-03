# AI Query API Specification (`/api/v1/ai/query`)

## 1. Overview

The `POST /api/v1/ai/query` endpoint is MarketLink's primary intelligent interface for farmer natural-language inquiries. It accepts conversational questions in English or Hinglish alongside optional farmer domain context, classifies the intent deterministically, and dispatches the query to the proper analytical engine.

- **URL**: `/api/v1/ai/query`
- **Method**: `POST`
- **Authentication**: `Bearer <JWT_TOKEN>`
- **Content-Type**: `application/json`
- **Response Wrapper**: Standard `ApiResponse<AiQueryResponse>`

---

## 2. Universal Request Contract: `AiNaturalLanguageQueryRequest`

```typescript
interface AiNaturalLanguageQueryRequest {
  query: string;               // Required. Natural language question
  language?: string;           // Optional. "en" (default), "hi"
  crop?: string;               // Optional. Commodity name ("Onion", "Potato", etc.)
  market?: string;             // Optional. Target mandi name ("Bareilly", "Nagpur")
  location?: {                 // Optional. Required for MANDI_RECOMMENDATION
    latitude: number;          // Range: [-90.0, 90.0]
    longitude: number;         // Range: [-180.0, 180.0]
  };
  quantity_quintals?: number;  // Optional. Produce volume in quintals (default 10.0)
  max_distance_km?: number;    // Optional. Search radius in km (default 200.0)
  current_price?: number;      // Optional. Farmer observed price for comparison
}
```

---

## 3. Universal Response Contract: `AiQueryResponse`

```typescript
interface AiQueryResponse {
  type: AiQueryIntent;         // "GENERAL_ADVISORY" | "MARKET_DATA" | "PRICE_PREDICTION" | "MANDI_RECOMMENDATION" | "COMBINED_ANALYSIS"
  confidence: number;          // Classification certainty (0.0 to 1.0)
  answer: string;              // Human-readable summary / advisory text
  prediction?: ModelAppPredictionResponse;
  recommendation?: ModelAppRecommendationResponse;
  market_data?: ModelAppMarketDataResponse;
  general_advisory?: ModelAppQueryResponse;
  explanation?: string;        // Optional contextual synthesis
  timestamp: string;           // ISO-8601 UTC timestamp
}
```

---

## 4. Intent Execution Examples

### Example 1: `GENERAL_ADVISORY`
**Request**:
```json
{
  "query": "How to prevent onion rotting in storage during rainy season?",
  "crop": "Onion"
}
```
**Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Query processed successfully",
  "data": {
    "type": "GENERAL_ADVISORY",
    "confidence": 0.88,
    "answer": "Ensure harvested onions are properly cured for 2 weeks in dry shade. Maintain ambient humidity below 65% with adequate cross-ventilation to prevent black mold and neck rot.",
    "general_advisory": {
      "query": "How to prevent onion rotting in storage during rainy season?",
      "intent": "GENERAL_ADVISORY",
      "source": "OLLAMA_LLM",
      "model": "llama3"
    },
    "timestamp": "2026-09-03T12:00:00Z"
  }
}
```

---

### Example 2: `MARKET_DATA`
**Request**:
```json
{
  "query": "What is today's onion price in Nagpur mandi?",
  "crop": "Onion",
  "market": "Nagpur"
}
```
**Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Query processed successfully",
  "data": {
    "type": "MARKET_DATA",
    "confidence": 0.90,
    "answer": "Current modal price for Onion in Nagpur (Maharashtra) is ₹1950.0/quintal (Date: 2026-09-03, Source: LIVE).",
    "market_data": {
      "commodity": "Onion",
      "data_source": "LIVE",
      "is_live": true,
      "record_count": 1,
      "records": [
        {
          "state": "Maharashtra",
          "district": "Nagpur",
          "market": "Nagpur",
          "commodity": "Onion",
          "modal_price": 1950.0,
          "min_price": 1800.0,
          "max_price": 2100.0,
          "date": "2026-09-03"
        }
      ]
    },
    "timestamp": "2026-09-03T12:00:00Z"
  }
}
```

---

### Example 3: `PRICE_PREDICTION`
**Request**:
```json
{
  "query": "bhai next week onion ka kya bhav milega Bareilly mein?",
  "crop": "Onion",
  "market": "Bareilly",
  "current_price": 1850.0
}
```
**Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Query processed successfully",
  "data": {
    "type": "PRICE_PREDICTION",
    "confidence": 0.90,
    "answer": "Next-day forecasted price for Onion in Bareilly is ₹1920.0/quintal (Expected change: +₹70.0, UP). Model reliability: STRONG (Score: 92.0%).",
    "prediction": {
      "market": "Bareilly",
      "commodity": "Onion",
      "current_price": 1850.0,
      "predicted_price": 1920.0,
      "expected_change": 70.0,
      "expected_change_pct": 3.78,
      "expected_direction": "UP",
      "usage_status": "PRODUCTION_READY",
      "reliability_score": 92.0,
      "quality_class": "STRONG"
    },
    "timestamp": "2026-09-03T12:00:00Z"
  }
}
```

---

### Example 4: `MANDI_RECOMMENDATION`
**Request**:
```json
{
  "query": "Which mandi should I sell my onions in for better price?",
  "crop": "Onion",
  "location": {
    "latitude": 28.6139,
    "longitude": 77.2090
  },
  "quantity_quintals": 10.0
}
```
**Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Query processed successfully",
  "data": {
    "type": "MANDI_RECOMMENDATION",
    "confidence": 0.92,
    "answer": "Recommended mandi: Bareilly (Uttar Pradesh, 15.2 km away) with estimated net return of ₹18570.0 for 10.0 quintals of Onion.",
    "recommendation": {
      "commodity": "Onion",
      "recommended_mandi": "Bareilly",
      "total_mandis_evaluated": 1,
      "recommendations": [
        {
          "rank": 1,
          "mandi": "Bareilly",
          "distance_km": 15.2,
          "current_price": 1850.0,
          "predicted_price": 1920.0,
          "transport_cost": 45.0,
          "market_fee": 18.0,
          "gross_revenue": 19200.0,
          "total_cost": 630.0,
          "net_return": 18570.0,
          "net_price_per_quintal": 1857.0,
          "recommendation_label": "RECOMMENDED"
        }
      ]
    },
    "timestamp": "2026-09-03T12:00:00Z"
  }
}
```

---

### Example 5: `COMBINED_ANALYSIS`
**Request**:
```json
{
  "query": "Which mandi should I sell my onions in next week considering expected prices?",
  "crop": "Onion",
  "location": {
    "latitude": 28.6139,
    "longitude": 77.2090
  },
  "quantity_quintals": 10.0
}
```
**Response (`200 OK`)**:
```json
{
  "success": true,
  "message": "Query processed successfully",
  "data": {
    "type": "COMBINED_ANALYSIS",
    "confidence": 0.95,
    "answer": "Combined Analysis: Selling in Bareilly yields highest estimated net return of ₹18570.0. Next-day prices are projected to trend UP to ₹1920.0/quintal.",
    "prediction": {
      "market": "Bareilly",
      "commodity": "Onion",
      "predicted_price": 1920.0,
      "expected_direction": "UP"
    },
    "recommendation": {
      "recommended_mandi": "Bareilly",
      "recommendations": [
        {
          "rank": 1,
          "mandi": "Bareilly",
          "net_return": 18570.0
        }
      ]
    },
    "explanation": "Analytical synthesis combining ML price forecasting in Bareilly with geospatial mandi ranking for Onion.",
    "timestamp": "2026-09-03T12:00:00Z"
  }
}
```

---

## 5. Error Responses

### Missing Location for Mandi Recommendation (`422 Unprocessable Entity`)
```json
{
  "success": false,
  "status": 422,
  "message": "Farmer location coordinates (latitude and longitude) are required for mandi recommendations",
  "timestamp": "2026-09-03T12:00:00Z"
}
```

### Model-app Offline (`503 Service Unavailable`)
```json
{
  "success": false,
  "status": 503,
  "message": "AI model service is currently unavailable",
  "timestamp": "2026-09-03T12:00:00Z"
}
```
