"""Typed runtime settings loaded from ABH_* environment variables."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration for ABHEDYA control-plane services."""

    model_config = SettingsConfigDict(env_prefix="ABH_", extra="ignore")

    db_dsn: str = ""
    session_idle_min: int = 30
    session_abs_hours: int = 8
    env_ttl_min: int = 60
    sandbox_runtime: str = "runsc"
    allow_degraded: bool = False
    host_reserved_cpu_millis: int = 1000
    host_reserved_mem_mb: int = 2048
    quarantine_dir: str = "/quarantine"
    volume_dir: str = "/var/lib/abhedya/vol"
    notary_key_path: str = "/run/secrets/notary_ed25519"
    notary_pubkey_path: str = "/run/secrets/notary_ed25519.pub"
    witness_path: str = "/witness/checkpoints.ndjson"
    checkpoint_every_n: int = 20
    checkpoint_every_sec: int = 30
    audit_retention_days: int = 180
    metric_interval_sec: int = 2
