"""Pydantic schemas for request validation."""

from pydantic import BaseModel, Field, EmailStr, validator
from typing import Optional, List


# Authentication Schemas
class LoginRequest(BaseModel):
    """Schema for login requests."""

    username: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=255)

    class Config:
        schema_extra = {
            "example": {"username": "reviewer1", "password": "securepassword123"}
        }


class TokenResponse(BaseModel):
    """Schema for token responses."""

    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_in: int


class UserCreateRequest(BaseModel):
    """Schema for user creation."""

    username: str = Field(..., min_length=3, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=255)
    roles: Optional[List[str]] = None

    @validator("password")
    def validate_password(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v

    class Config:
        schema_extra = {
            "example": {
                "username": "reviewer1",
                "email": "reviewer@example.com",
                "password": "SecurePass123",
                "roles": ["reviewer"],
            }
        }


class UserResponse(BaseModel):
    """Schema for user responses."""

    id: str
    username: str
    email: str
    roles: List[str]
    is_active: bool
    created_at: str
    updated_at: str
    last_login: Optional[str] = None


# Document Schemas
class RiskFlagSchema(BaseModel):
    """Schema for risk flags."""

    field: Optional[str] = None
    issue: str = Field(..., max_length=500)
    severity: str = Field(..., pattern="^(low|medium|high)$")


class DocumentCreateRequest(BaseModel):
    """Schema for document creation."""

    title: str = Field(..., min_length=1, max_length=255)
    content: str = Field(..., min_length=1)
    doc_type: str = Field(..., min_length=1, max_length=100)
    source: Optional[str] = Field("automation", max_length=100)
    extracted_fields: Optional[dict] = None
    extraction_confidence: Optional[dict] = None
    template_id: Optional[str] = None

    @validator("doc_type")
    def validate_doc_type(cls, v):
        allowed_types = ["invoice", "contract", "form", "report", "other"]
        if v not in allowed_types:
            raise ValueError(f"doc_type must be one of {allowed_types}")
        return v

    class Config:
        schema_extra = {
            "example": {
                "title": "Invoice ABC123",
                "content": "This is the document content...",
                "doc_type": "invoice",
                "source": "automation",
                "extracted_fields": {"amount": "$1000", "due_date": "2024-12-31"},
            }
        }


class DocumentUpdateRequest(BaseModel):
    """Schema for document updates."""

    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    editor: Optional[str] = Field(None, max_length=255)


class DocumentApprovalRequest(BaseModel):
    """Schema for document approval/rejection."""

    notes: Optional[str] = Field(None, max_length=1000)
    reviewer: Optional[str] = Field(None, max_length=255)


class BulkApprovalRequest(BaseModel):
    """Schema for bulk approval requests."""

    document_ids: List[str] = Field(..., min_items=1, max_items=100)
    max_risk: str = Field("low", pattern="^(low|medium|high)$")
    notes: Optional[str] = Field(None, max_length=1000)
    reviewer: Optional[str] = Field(None, max_length=255)


class TemplateCreateRequest(BaseModel):
    """Schema for template creation."""

    name: str = Field(..., min_length=1, max_length=255)
    doc_type: str = Field(..., min_length=1, max_length=100)
    content: str = Field(..., min_length=1)

    @validator("doc_type")
    def validate_doc_type(cls, v):
        allowed_types = ["invoice", "contract", "form", "report", "other"]
        if v not in allowed_types:
            raise ValueError(f"doc_type must be one of {allowed_types}")
        return v


class TemplateGenerateRequest(BaseModel):
    """Schema for template generation."""

    title: Optional[str] = Field(None, max_length=255)
    values: dict = Field(default_factory=dict)
    confidence: Optional[dict] = None
    source: Optional[str] = Field("template", max_length=100)


class ErrorResponse(BaseModel):
    """Schema for error responses."""

    detail: str
    error_code: Optional[str] = None
    timestamp: Optional[str] = None
