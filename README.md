# k8s-provisions-backstage

A **GitOps provisioning service** that integrates with **ArgoCD**, **Backstage**, and Kubernetes.  
This project exposes an API for provisioning Kubernetes resources through GitOps practices — writing manifests into a values repository, syncing them with ArgoCD, and validating against JSON schemas.  
The server dynamically generates **Pydantic models** from schemas stored in Git, enabling strong request validation.  

---

## 🚀 Features

- **FastAPI server** for provisioning Kubernetes resources  
- **Schema-driven validation** with dynamic loaders (`/schemas/{resource}/{version}`)  
- **GitOps integration**: resources are written to a Git values repository in the format: {Region}/{Namespace}/{ApplicationName}.yaml
- **ArgoCD sync**: triggers ApplicationSet syncs after provisioning using the convention: {Cluster}-{Namespace}-{Resource}-{ApplicationName}
- **Dynamic routers & Pydantic models** generated automatically from JSON schemas in Git  
- Supports **multiple resources**, each with its own repos and tokens  

---

## 🛠 Dependencies

This service requires a properly configured GitOps + ArgoCD environment.  

### Repositories
Each **resource** (e.g. `tyk`, `redis`) needs:  

- **Schemas repo** → defines JSON schemas per resource/version in this path: schemas/schema-{version}.json
- **Values repo** → Git repository where generated manifests are stored  

### Services
- **ArgoCD**
- Must be deployed in your cluster  
- ApplicationSets must be configured to pick up manifests from the values repo  
- Must use the naming convention:
  ```
  {Cluster}-{Namespace}-{Resource}-{ApplicationName}
  ```
- Requires an API token for programmatic syncs  

- **Kubernetes Cluster**
- Can be k3s (local dev) or any CNCF-compliant cluster  
- Must have ArgoCD installed and accessible  

### Permissions
- **Per-resource Git tokens**:
- `${RESOURCE}_SCHEMAS_REPO_TOKEN` → read access  
- `${RESOURCE}_VALUES_REPO_TOKEN` → write access  
- **ArgoCD token**:
- Permissions to trigger sync on Applications  

---

## ⚙️ Setup

1. **Clone this repo**  
 ```bash
 git clone https://github.com/SavageAxe/k8s-provisions-backstage.git
 cd k8s-provisions-backstage
```

2. **Set environment variables (per resource)**
```dotenv
ARGOCD_URL=https://argocd.example.com
ARGOCD_TOKEN=<argocd-token>

TYK_SCHEMAS_REPO_URL=git@github.com:your-org/tyk-schemas.git
TYK_SCHEMAS_REPO_TOKEN=<tyk-schemas-token>
TYK_VALUES_REPO_URL=git@github.com:your-org/tyk-values.git
TYK_VALUES_REPO_TOKEN=<tyk-values-token>

REDIS_SCHEMAS_REPO_URL=git@github.com:your-org/redis-schemas.git
REDIS_SCHEMAS_REPO_TOKEN=<redis-schemas-token>
REDIS_VALUES_REPO_URL=git@github.com:your-org/redis-values.git
REDIS_VALUES_REPO_TOKEN=<redis-values-token>
```

3. **Install python dependencies**
```bash
pip install -r requirements.txt
```

4. **Run the FastAPI server**
```bash
python -m app.main
```

5. **Access OpenAPI docs**
```djangourlpath
Swagger UI: http://localhost:8000/docs
ReDoc: http://localhost:8000/redoc
```

---

## 📖 Example Workflow

1. User calls: POST /v1/tyk/0.1.0
with JSON body describing the application values.

2. Service:  
- Validates request against `schema-0.1.0.json` in `tyk-schemas` repo  
- Writes `dev/fintech/payments-api.yaml` into `tyk-values` repo  
- Commits with message:  
  ```
  Add dev namespace 'fintech' for tyk app 'payments-api'
  ```

3. Service triggers ArgoCD sync for Application:
dev-fintech-tyk-payments-api


4. Resource becomes active in the cluster.  

---

## 📂 Repo Structure


├── app/   
│ ├── main.py # Entrypoint (python -m app.main)  
│ ├── general/ # FastAPI setup & config  
│ └── src/  
│ ├── routers/ # Dynamic routers per resource/version  
│ ├── services/ # Git, ArgoCD, Schema loaders  
│ ├── gitops/ # GitOps-specific writers  
│ ├── models/ # Pydantic models (generated from schemas)  
│ └── utils/ # Logging, env config, helpers  
├── requirements.txt  
└── README.md

---

## 🔄 GitOps Flow Diagram

```mermaid
flowchart TD
    A[User API Request] --> B[FastAPI Server]
    B --> C[Schema Repo<br/>{RESOURCE}_SCHEMAS_REPO_URL]
    B --> D[Values Repo<br/>{RESOURCE}_VALUES_REPO_URL]
    D --> E[ArgoCD ApplicationSet]
    E --> F[Kubernetes Cluster]
```