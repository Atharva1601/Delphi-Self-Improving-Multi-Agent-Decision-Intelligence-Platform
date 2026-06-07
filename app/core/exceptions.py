"""
app/core/exceptions.py
──────────────────────
Base exception hierarchy for Delphi.
All custom exceptions inherit from DelphiException so callers can
catch the entire family with a single except clause.
"""
from typing import Any


class DelphiException(Exception):
    """Root exception for all Delphi-domain errors."""

    status_code: int = 500
    error_code: str = "DELPHI_ERROR"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        detail: Any = None,
        error_code: str | None = None,
    ) -> None:
        self.message = message or self.__class__.message
        self.detail = detail
        if error_code:
            self.error_code = error_code
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "error_code": self.error_code,
            "message": self.message,
            "detail": self.detail,
        }


# ── Infrastructure ─────────────────────────────────────────────────────────────

class DatabaseError(DelphiException):
    status_code = 503
    error_code = "DATABASE_ERROR"
    message = "A database error occurred."


class MigrationError(DatabaseError):
    error_code = "MIGRATION_ERROR"
    message = "Database migration failed."


# ── Validation ─────────────────────────────────────────────────────────────────

class ValidationError(DelphiException):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "Input validation failed."


# ── Agent / Workflow ───────────────────────────────────────────────────────────

class AgentError(DelphiException):
    status_code = 500
    error_code = "AGENT_ERROR"
    message = "An agent encountered an error."


class LLMProviderError(AgentError):
    error_code = "LLM_PROVIDER_ERROR"
    message = "The LLM provider returned an error."


class RouterError(AgentError):
    error_code = "ROUTER_ERROR"
    message = "Query routing failed."


class CouncilError(AgentError):
    error_code = "COUNCIL_ERROR"
    message = "Council formation failed."


class DebateError(AgentError):
    error_code = "DEBATE_ERROR"
    message = "Debate execution failed."


class JudgeError(AgentError):
    error_code = "JUDGE_ERROR"
    message = "Judge evaluation failed."


class ConsensusError(AgentError):
    error_code = "CONSENSUS_ERROR"
    message = "Consensus formation failed."


# ── Not Found ──────────────────────────────────────────────────────────────────

class NotFoundError(DelphiException):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "The requested resource was not found."


class ExpertNotFoundError(NotFoundError):
    error_code = "EXPERT_NOT_FOUND"
    message = "Expert not found."


class CaseNotFoundError(NotFoundError):
    error_code = "CASE_NOT_FOUND"
    message = "Case not found."
