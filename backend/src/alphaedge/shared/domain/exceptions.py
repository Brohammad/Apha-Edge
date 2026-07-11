class DomainException(Exception):  # noqa: N818
    """Base class for domain-level errors."""

    def __init__(self, message: str, code: str = "DOMAIN_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(DomainException):
    def __init__(self, resource: str, identifier: str) -> None:
        super().__init__(f"{resource} not found: {identifier}", code="NOT_FOUND")


class ConflictError(DomainException):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="CONFLICT")


class ValidationError(DomainException):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="VALIDATION_ERROR")


class AuthenticationError(DomainException):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, code="AUTHENTICATION_ERROR")


class AuthorizationError(DomainException):
    def __init__(self, message: str = "Insufficient permissions") -> None:
        super().__init__(message, code="AUTHORIZATION_ERROR")


class RiskRejectedError(DomainException):
    def __init__(self, message: str, *, stage: str | None = None) -> None:
        details_msg = message if not stage else f"[{stage}] {message}"
        super().__init__(details_msg, code="RISK_REJECTED")
        self.stage = stage
