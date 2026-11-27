from pydantic import BaseModel


class ErrorResponse(BaseModel):
    message: str


class ErrorDescription(BaseModel):
    field: str
    error: str


class ValidationErrorResponse(ErrorResponse):
    errors: list[ErrorDescription]
