import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import HttpUrl, Field

env_file = ".env"
if os.environ.get("NETBOX_APP_ENV") == "test":
    env_file = ".test.env"


class Settings(BaseSettings):
    """
    Operator Settings
    """

    netbox_url: HttpUrl = Field(
        description="The NetBox URL that includes the scheme, TLD, and host"
    )
    netbox_token: str = Field(description="The NetBox token with read-write access")
    netbox_verify_ssl: bool = Field(
        default=True, description="Whether to verify NetBox SSL"
    )

    operator_worker_limit: int = Field(
        default=10,
        description="How many workers can be running simultaneously on per-object event queue",
    )
    operator_retry_limit: int = Field(
        default=30,
        description="The number of times a handler can be retried in case of an error",
    )
    operator_backoff_seconds: int = Field(
        default=5,
        description="The number of seconds to wait between handler retries in case of an error",
    )
    operator_timer_idle_seconds: int = Field(
        default=10,
        description="The number of seconds the object has to be idle for the timer to fire",
    )
    operator_timer_interval_seconds: int = Field(
        default=600, description="The number of seconds between timer runs"
    )
    namespace: str = Field(description="The namespace where the operator is running")

    prometheus_metrics_port: int = Field(
        default=9090, description="The port to expose Prometheus metrics on"
    )

    model_config = SettingsConfigDict(env_file=env_file)
