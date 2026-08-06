from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class EndpointCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    url: HttpUrl
    interval_seconds: int = Field(default=300, ge=10, le=86_400)
    timeout_seconds: int = Field(default=10, ge=1, le=120)
    response_time_threshold_ms: int | None = Field(default=None, ge=1)


class EndpointOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    url: str
    interval_seconds: int
    timeout_seconds: int
    response_time_threshold_ms: int | None
    active: bool


class CheckOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    endpoint_id: int
    status_code: int | None
    response_time_ms: int | None
    error_message: str | None
    is_alert: bool
    checked_at: datetime


class HealthSummary(BaseModel):
    total_endpoints: int
    healthy_endpoints: int
    alerting_endpoints: int
    unchecked_endpoints: int


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class DashboardEndpoint(BaseModel):
    id: int
    name: str
    url: str
    status_code: int | None
    response_time_ms: int | None
    is_alert: bool


class DashboardData(BaseModel):
    summary: HealthSummary
    endpoints: list[DashboardEndpoint]
