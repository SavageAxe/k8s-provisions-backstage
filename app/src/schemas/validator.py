from jsonschema import validate, ValidationError, RefResolver

class SchemaValidator:
    def __init__(self, schema, schema_store={}):
        self.schema = schema
        self.schema_store = schema_store

    def validate(self, payload):
        try:
            resolver = RefResolver.from_schema(
                self.schema,
                store=self.schema_store
            )
            validate(instance=payload, schema=self.schema, resolver=resolver)
        except ValidationError as e:
            raise ValueError(f"Schema validation error: {e.message}")