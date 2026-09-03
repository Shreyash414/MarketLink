# Secrets Management & Configuration Hygiene

## 1. Secret Management Policy

MarketLink strictly prohibits hardcoding secrets, passwords, encryption keys, or third-party API tokens in version-controlled source files.

### Regulated Sensitive Values:
1. `JWT_SECRET`: Base64-encoded secret key used to sign and verify authentication tokens.
2. `DATA_GOV_API_KEY`: Official Open Government Data API key used for AGMARKNET price fetching.
3. `SPRING_DATASOURCE_PASSWORD`: Relational PostgreSQL database password.
4. `REDIS_PASSWORD`: Optional authentication token for Redis cluster access.
5. `RABBITMQ_PASSWORD`: AMQP broker credentials for queue access.

---

## 2. Git Hygiene & `.gitignore`

The repository `.gitignore` ensures that runtime secret files are never accidentally staged or pushed:

```gitignore
# Environment & Secret Files
.env
.env.local
*.env

# Build & Runtime Artifacts
target/
*.class
.venv/
__pycache__/
*.pyc
*.pyo
.pytest_cache/
```

- **`.env.example`** is checked into version control to document the variable schema with safe placeholder values (e.g. `DATA_GOV_API_KEY=your_registered_key_here`).
- **Secret Scanning**: Automated pre-commit hooks and repository scanning tools reject commits containing unmasked API tokens or high-entropy strings.

---

## 3. Production Deployment Secret Injection

In staging and production environments:
- Secrets are never stored on filesystem disks in plaintext.
- Kubernetes Secrets, Docker Swarm Secrets, or Cloud Key Vaults (AWS Secrets Manager / HashiCorp Vault) inject credentials directly into container environment variables at runtime.
