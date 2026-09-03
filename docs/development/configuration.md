# Configuration & Environment Variables Reference

## 1. Overview

MarketLink adheres to 12-Factor App principles. All environment-specific secrets, ports, endpoints, and credentials are configured via environment variables and bound into type-safe configuration classes.

---

## 2. Environment Variables Reference

| Variable Name | Component | Required? | Default Value | Example Placeholder | Sensitivity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `SERVER_PORT` | Core Backend | Optional | `8080` | `8080` | Low |
| `SPRING_PROFILES_ACTIVE` | Core Backend | Optional | `dev` | `prod` | Low |
| `MODEL_APP_BASE_URL` | Core Backend | Optional | `http://localhost:8000` | `http://ai-service.internal:8000` | Medium |
| `MODEL_APP_CONNECT_TIMEOUT_MS`| Core Backend | Optional | `5000` | `5000` | Low |
| `MODEL_APP_READ_TIMEOUT_MS` | Core Backend | Optional | `15000` | `15000` | Low |
| `MODEL_APP_QUERY_TIMEOUT_MS`| Core Backend | Optional | `30000` | `30000` | Low |
| `JWT_SECRET` | Core Backend | **Required** | None (Template provided) | `dGhpcy1pcy1hLXNhbXBsZS1iYXNlNjQtc2VjcmV0` | **High (Secret)** |
| `JWT_EXPIRATION_MS` | Core Backend | Optional | `86400000` (24h) | `86400000` | Medium |
| `SPRING_DATASOURCE_URL` | Core Backend | Optional | `jdbc:postgresql://...` | `jdbc:postgresql://localhost:5432/marketlink` | Medium |
| `SPRING_DATASOURCE_USERNAME` | Core Backend | Optional | `postgres` | `marketlink_user` | Medium |
| `SPRING_DATASOURCE_PASSWORD` | Core Backend | Optional | `postgres` | `sample_db_password` | **High (Secret)** |
| `SPRING_DATA_MONGODB_URI` | Core Backend | Optional | `mongodb://localhost:27017`| `mongodb://localhost:27017/marketlink` | Medium |
| `MODEL_APP_PORT` | Model-app | Optional | `8000` | `8000` | Low |
| `DATA_GOV_API_KEY` | Model-app | Optional | None | `sample_data_gov_in_api_key` | **High (Secret)** |
| `REDIS_HOST` | Model-app | Optional | `localhost` | `127.0.0.1` | Low |
| `REDIS_PORT` | Model-app | Optional | `6379` | `6379` | Low |
| `REDIS_PASSWORD` | Model-app | Optional | None | `sample_redis_auth_token` | **High (Secret)** |
| `RABBITMQ_HOST` | Model-app | Optional | `localhost` | `127.0.0.1` | Low |
| `RABBITMQ_PORT` | Model-app | Optional | `5672` | `5672` | Low |
| `RABBITMQ_USERNAME` | Model-app | Optional | `guest` | `ai_worker` | Medium |
| `RABBITMQ_PASSWORD` | Model-app | Optional | `guest` | `sample_rabbit_password` | **High (Secret)** |
| `OLLAMA_BASE_URL` | Model-app | Optional | `http://localhost:11434`| `http://127.0.0.1:11434` | Low |
| `OLLAMA_MODEL` | Model-app | Optional | `llama3` | `llama3:8b-instruct-q4_K_M` | Low |

---

## 3. Spring Boot `application.yml` Reference

```yaml
server:
  port: ${SERVER_PORT:8080}

spring:
  application:
    name: marketlink-backend
  datasource:
    url: ${SPRING_DATASOURCE_URL:jdbc:postgresql://localhost:5432/marketlink_db}
    username: ${SPRING_DATASOURCE_USERNAME:postgres}
    password: ${SPRING_DATASOURCE_PASSWORD:postgres}
    driver-class-name: org.postgresql.Driver
  data:
    mongodb:
      uri: ${SPRING_DATA_MONGODB_URI:mongodb://localhost:27017/marketlink_images}

marketlink:
  model-app:
    base-url: ${MODEL_APP_BASE_URL:http://localhost:8000}
    connect-timeout-ms: ${MODEL_APP_CONNECT_TIMEOUT_MS:5000}
    read-timeout-ms: ${MODEL_APP_READ_TIMEOUT_MS:15000}
    query-timeout-ms: ${MODEL_APP_QUERY_TIMEOUT_MS:30000}
  security:
    jwt:
      secret: ${JWT_SECRET:dGhpcy1pcy1hLXNhbXBsZS1iYXNlNjQtc2VjcmV0LWtleS1mb3ItZGV2ZWxvcG1lbnQ=}
      expiration-ms: ${JWT_EXPIRATION_MS:86400000}
```

---

## 4. Security & Secret Hygiene

1. `.env` is listed in `.gitignore` and **must never be committed**.
2. `.env.example` provides template placeholders only; real API keys or private keys are strictly barred from version control.
3. CI/CD pipelines inject production variables using protected environment secrets (e.g. GitHub Actions Secrets or HashiCorp Vault).
