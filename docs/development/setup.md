# Local Developer Setup Guide

## 1. System Prerequisites

Ensure the following runtimes are installed on your development machine:

| Component | Minimum Version | Verification Command |
| :--- | :--- | :--- |
| **Java JDK** | Java 21 (LTS) | `java -version` |
| **Python** | Python 3.10+ | `python3 --version` |
| **Maven Wrapper** | Maven 3.9+ | `./backend/mvnw -version` |
| **Redis Server** | Redis 7.0+ | `redis-cli ping` |
| **RabbitMQ Server**| RabbitMQ 3.11+ | `rabbitmqctl status` |
| **Ollama** | Latest (Optional)| `curl http://localhost:11434/api/version` |

---

## 2. Step-by-Step Setup

### Step 2.1: Clone and Configure Environment
```bash
cd /path/to/MarketLink
cp .env.example .env
```
Edit `.env` to configure your local credentials and API keys:
```properties
DATA_GOV_API_KEY=your_datagov_api_key_here
JWT_SECRET=your_base64_jwt_secret_here
```

### Step 2.2: Python Virtual Environment & Model-App Dependencies
```bash
# Create and activate virtual environment if not already present
python3 -m venv .venv
source .venv/bin/activate

# Install Model-app dependencies
cd Model-app
pip install -r requirements.txt
```

### Step 2.3: Start Infrastructure Services
Ensure local instances of Redis and RabbitMQ are running:
```bash
# If running as native Linux systemd services:
sudo systemctl start redis-server
sudo systemctl start rabbitmq-server

# Or verify local availability:
redis-cli ping           # Expected: PONG
curl -I http://localhost:15672 # RabbitMQ Management console
```

### Step 2.4: Start the FastAPI Model-App
From the `Model-app` directory:
```bash
cd Model-app
../.venv/bin/uvicorn src.main:app --host 127.0.0.1 --port 8000 --reload
```
Verify Model-app health in another terminal:
```bash
curl -s http://127.0.0.1:8000/health
# Expected: {"status":"HEALTHY","service":"marketlink-ai","version":"1.0.0",...}
```

### Step 2.5: Build and Run Spring Boot Core Backend
In a new terminal:
```bash
cd backend
./mvnw clean spring-boot:run
```
The server will start on port `8080`.

Verify backend health:
```bash
curl -s http://localhost:8080/api/v1/ai/health
```

---

## 3. Developer Tooling & Swagger

- **Core Backend Swagger UI**: [http://localhost:8080/swagger-ui/index.html](http://localhost:8080/swagger-ui/index.html)
- **Core Backend OpenAPI JSON**: [http://localhost:8080/v3/api-docs](http://localhost:8080/v3/api-docs)
- **Model-app Interactive Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
