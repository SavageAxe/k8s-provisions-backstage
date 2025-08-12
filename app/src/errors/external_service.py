class ExternalServiceError(Exception):
    def __init__(self, service_name, status_code=None, detail=None):
        # Initialize the error with a service name, message, status code, and optional details
        self.error = f"Request to {service_name} failed."
        self.status_code = status_code
        self.detail = detail
        super().__init__(self.detail)