from __future__ import annotations


class ApiError(RuntimeError):
    status_code = 500

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class DataUnavailableError(ApiError):
    status_code = 503


class ResourceNotFoundError(ApiError):
    status_code = 404


class EmptyResultError(ApiError):
    status_code = 404


class InvalidDateRangeError(ApiError):
    status_code = 422
