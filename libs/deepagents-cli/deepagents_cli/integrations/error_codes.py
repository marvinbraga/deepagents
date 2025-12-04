"""Standardized error codes for sandbox file operations."""

from enum import Enum


class FileOperationErrorCode(Enum):
    """Standardized error codes for file operations."""

    SUCCESS = 0
    FILE_NOT_FOUND = 1
    PERMISSION_DENIED = 2
    TIMEOUT = 3
    NETWORK_ERROR = 4
    INVALID_PATH = 5
    UNKNOWN = 99


def map_error_to_code(error_message: str | None) -> FileOperationErrorCode | None:
    """Map error messages to standardized error codes.

    Args:
        error_message: Error message string from sandbox operation.

    Returns:
        Corresponding FileOperationErrorCode, or None if no error.
    """
    if not error_message:
        return None

    error_lower = error_message.lower()

    if "not found" in error_lower or "no such file" in error_lower:
        return FileOperationErrorCode.FILE_NOT_FOUND
    if "permission" in error_lower or "access denied" in error_lower:
        return FileOperationErrorCode.PERMISSION_DENIED
    if "timeout" in error_lower or "timed out" in error_lower:
        return FileOperationErrorCode.TIMEOUT
    if "network" in error_lower or "connection" in error_lower:
        return FileOperationErrorCode.NETWORK_ERROR
    if "invalid" in error_lower or "illegal" in error_lower:
        return FileOperationErrorCode.INVALID_PATH

    return FileOperationErrorCode.UNKNOWN
