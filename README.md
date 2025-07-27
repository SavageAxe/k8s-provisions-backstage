# OS4 API Provisioning Server

This FastAPI server provisions OS4 resources by writing a `values.yaml` file to a remote git repository based on the request body.

## Requirements
- Python 3.8+
- See `requirements.txt`

## Installation

```bash
pip install -r requirements.txt
```

## Environment Variables
- `GIT_REPO_URL`: The HTTPS URL of the remote git repository (e.g., `https://github.com/yourorg/yourrepo.git`)
- `GIT_USERNAME`: Username for git authentication
- `GIT_PASSWORD`: Password or token for git authentication
- `GIT_BRANCH`: (Optional) Branch to use (default: `main`)

## Running the Server

```bash
uvicorn main:app --reload
```

## Project Structure

- `main.py`: Entrypoint, imports the FastAPI app
- `os4api/`
  - `api.py`: FastAPI app and endpoints
  - `schemas.py`: Pydantic models
  - `git_ops.py`: Git operations logic
  - `logger.py`: Logger configuration

## API Documentation (Swagger UI)

Once running, visit [http://localhost:8000/docs](http://localhost:8000/docs) for interactive Swagger UI.

## API Endpoint

### POST `/provision`

Provision an OS4 resource by sending a JSON body:

```json
{
  "region": "my-region",
  "namespace": "my-namespace",
  "applicationName": "my-app",
  "values": {
    "key1": "value1",
    "key2": "value2"
  }
}
```

This will wriite a YAML file to the path `/my-region/my-namespace/my-app.yaml` in the remote git repository.


## Example cURL

```bash
curl -X POST "http://localhost:8000/provision" \
  -H "Content-Type: application/json" \
  -d '{
    "region": "my-region",
    "namespace": "my-namespace",
    "applicationName": "my-app",
    "values": {"foo": "bar"}
  }'
``` 
# k8s-provisions-backstage
