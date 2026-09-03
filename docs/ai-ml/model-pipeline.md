# XGBoost Model Pipeline & Inference Architecture

## 1. Overview & Model Registry

MarketLink's price prediction subsystem uses gradient-boosted decision trees implemented via **XGBoost**. The system organizes models through a centralized registry (`ModelRegistry`) located in `Model-app/src/models/model_registry.py`.

### Supported Commodity-Market Pairs:
1. **Onion**: Bareilly (UP), Bargarh (Odisha), Nagpur (Maharashtra)
2. **Potato**: Agra (UP)
3. **Tomato**: Kolar (Karnataka)
4. **Wheat**: Khanna (Punjab), Indore (MP)
5. **Rice**: Burdwan (West Bengal)

---

## 2. Model Loading & Preload Lifespan

During application startup, `main.py` executes a preloading routine:
```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Preload registered models into memory
    loaded = model_registry.preload_all()
    logger.info(f"Pre-loaded models into memory: {loaded}")
    yield
    # Graceful shutdown
```

Each registered model corresponds to:
1. **Model Weights Artifact**: XGBoost model serialized to JSON (e.g. `change_xgboost_v3.json`).
2. **Feature Metadata & Scaler**: Feature columns, lag features, and rolling price averages.
3. **Historical Feature Companion File**: Processed baseline feature table used for input construction.

---

## 3. Inference Pipeline

When a price prediction is evaluated:
```mermaid
graph TD
    Req[Prediction Request: Market, Commodity, Current Price] --> Reg[Model Registry Lookup]
    Reg --> Valid{Model Artifacts Present?}
    
    Valid -->|Yes| Feat[Feature Construction & Lag Injection]
    Feat --> DMatrix[XGBoost DMatrix Generation]
    DMatrix --> Predict[Model.predict()]
    Predict --> Stats[Calculate Expected Change & Direction]
    Stats --> Bounds[Calculate Confidence Intervals]
    Bounds --> Gate[Quality Gate Evaluation]
    Gate --> Resp[ModelAppPredictionResponse]
    
    Valid -->|Missing Feature CSV| Error[Return Controlled ARTIFACT_MISSING Error]
```

### 3.1 Derived Outputs
- **`predicted_price`**: $\hat{y} = \text{Current Price} + \Delta_{\text{predicted}}$
- **`expected_change`**: $\Delta = \hat{y} - \text{Current Price}$
- **`expected_change_pct`**: $(\Delta / \text{Current Price}) \times 100$
- **`expected_direction`**: `UP` if $\Delta > 0$, `DOWN` if $\Delta < 0$, `STABLE` if $\Delta = 0$.
- **`confidence_intervals`**: $[\hat{y} - 1.96 \cdot \text{RMSE}, \hat{y} + 1.96 \cdot \text{RMSE}]$.

---

## 4. Known Deployment Limitation: Artifact Gap

> [!IMPORTANT]
> **Status: DEPLOYMENT ARTIFACT GAP (Deferred Issue)**
> 
> The XGBoost model architecture is completely implemented and structurally valid. However, the companion historical feature CSV files (e.g. `bareilly_final_features.csv`, `bargarh_final_features.csv`) required to construct real-time feature lag matrices are currently absent from the deployment repository.

### Key Facts:
1. **No Data Fabrication**: Following project guidelines, no fake CSV files or synthetic market records were generated.
2. **Structural Validation**: XGBoost model JSON files load and validate structurally in unit tests.
3. **Controlled Degradation**: When a feature CSV is absent during inference, `ModelPredictor` returns a controlled error stating:
   > *"Required feature CSV artifact not found for commodity '{crop}', market '{market}'. Please ensure feature CSV artifacts are included in deployment."*
4. **Deferred Resolution**: The training team will supply the finalized feature extraction CSV files during production deployment packaging.
