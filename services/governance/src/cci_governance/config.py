from pydantic_settings import BaseSettings, SettingsConfigDict


class GovernanceSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    CCI_GOVERNANCE_PORT: int = 8005
    MONGODB_AUDIT_URI: str = (
        "mongodb://cci_audit_writer:changeme_audit@mongodb:27017/"
        "cci_governance?authSource=cci_governance"
    )
    CCI_GOVERNANCE_DB: str = "cci_governance"
    CCI_AUDIT_ACTOR: str = "governance-service"
    CCI_SERVICE_VERSION: str = "0.1.0"
