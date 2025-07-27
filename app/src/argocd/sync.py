import requests

class ArgoCDSyncer:
    def __init__(self, logger):
        self.logger = logger

    def sync(self, region, namespace, resource, app_name, argocd_url, argocd_token):
        app_name_full = f"{region}-{namespace}-{resource}-{app_name}"
        url = f"http://localhost:8080/api/v1/applications/{app_name_full}/sync"
        headers = {"Authorization": f"Bearer {argocd_token}"}
        try:
            resp = requests.post(url, headers=headers, timeout=10, verify=False)
            print(resp.json())
            resp.raise_for_status()
            self.logger.info(f"Triggered ArgoCD sync for {app_name_full}")
            return resp.json()
        except Exception as e:
            self.logger.error(f"ArgoCD sync failed for {app_name_full}: {e}")
            raise 