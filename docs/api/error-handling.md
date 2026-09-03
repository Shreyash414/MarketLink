# Error Handling & Fault Sanitization

## 1. Unified Error Envelope

MarketLink enforces a standardized, predictable error envelope across all public endpoints in the Core Backend:

```json
{
  "success": false,
  "status": 503,
  "message": "AI model service is currently unavailable",
  "timestamp": "2026-09-03T12:00:00Z"
}
```

When validation fails on specific request fields, a structured list of sub-errors is provided:
```json
{
  "success": false,
  "status": 400,
  "message": "Validation failed for request arguments",
  "data": {
    "farmer_latitude": "Latitude must be between -90.0 and 90.0",
    "quantity_quintals": "Quantity must be greater than zero"
  },
  "timestamp": "2026-09-03T12:00:00Z"
}
```

---

## 2. HTTP Status Code Mapping

| Scenario | HTTP Status | Exception Class | Client-Facing Message |
| :--- | :--- | :--- | :--- |
| **Missing or Invalid Request Field** | `400 Bad Request` | `MethodArgumentNotValidException` | `"Validation failed for request arguments"` |
| **Missing JWT or Expired Token** | `401 Unauthorized` | `BadCredentialsException` | `"Full authentication is required to access this resource"` |
| **Forbidden Role Action** | `403 Forbidden` | `AccessDeniedException` | `"Access denied for user role"` |
| **Unknown Lot or Job ID** | `404 Not Found` | `ResourceNotFoundException` / `ModelAppNotFoundException` | `"Resource not found with specified identifier"` |
| **Out-of-Bounds Coordinates** | `422 Unprocessable` | `ModelAppValidationException` | `"Latitude must be between -90.0 and 90.0"` |
| **Missing Location for Mandi Rec** | `422 Unprocessable` | `ModelAppValidationException` | `"Farmer location coordinates (latitude and longitude) are required for mandi recommendations"` |
| **Upstream Ollama LLM Failure** | `502 Bad Gateway` | `ModelAppBadGatewayException` | `"Upstream AI advisory service failed to generate response"` |
| **Model-app Service Unreachable** | `503 Service Unavailable` | `ModelAppUnavailableException` | `"AI model service is currently unavailable"` |
| **Model-app Connection Refused** | `503 Service Unavailable` | `ModelAppUnavailableException` | `"AI model service connection refused"` |
| **Socket Read Timeout** | `504 Gateway Timeout` | `ModelAppTimeoutException` | `"AI service request timed out"` |
| **Uncaught Runtime Exception** | `500 Internal Error` | `Exception` | `"An unexpected error occurred. Please try again later."` |

---

## 3. Strict Sanitization & Security Policies

To safeguard production infrastructure and prevent data leakage, the following sanitization policies are enforced in `GlobalExceptionHandler`:

1. **Stack Trace Suppression**: Full Java stack traces, Python tracebacks, and internal exception class names are strictly suppressed from all client response bodies. Full traces are written only to protected server log files tagged with `X-Correlation-ID`.
2. **Path Masking**: Internal server filesystem paths (e.g. `/home/shreyash/Projects/MarketLink/Model-app/data/...`) are caught and stripped before transmission. Missing file errors are mapped to sanitized codes such as `ARTIFACT_MISSING`.
3. **Secret Masking**: Passwords, JWT secrets, database connection URLs, Redis passwords, RabbitMQ credentials, and `DATA_GOV_API_KEY` are never returned in error details.
4. **Internal Microservice Isolation**: Internal IP addresses (e.g. `127.0.0.1:8000`) are not disclosed to external clients.

---

## 4. Client Guidance for Android & API Consumers

- **400 / 422 Errors**: Inspect the `data` field to highlight the offending input fields in the UI.
- **503 Errors**: Display a non-intrusive offline indicator (e.g. *"AI Advisory is temporarily busy. You can still list your produce and accept buyer bids."*).
- **504 Errors**: The recommendation job may be taking longer due to high regional queue volume; offer the farmer the option to submit the request asynchronously via `/recommend/async`.
