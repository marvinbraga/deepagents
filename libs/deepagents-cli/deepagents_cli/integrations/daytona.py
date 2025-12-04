"""Daytona sandbox backend implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

from deepagents.backends.protocol import (
    ExecuteResponse,
    FileDownloadResponse,
    FileUploadResponse,
)
from deepagents.backends.sandbox import BaseSandbox

from deepagents_cli.integrations.error_codes import map_error_to_code

if TYPE_CHECKING:
    from daytona import Sandbox


class DaytonaBackend(BaseSandbox):
    """Daytona backend implementation conforming to SandboxBackendProtocol.

    This implementation inherits all file operation methods from BaseSandbox
    and only implements the execute() method using Daytona's API.
    """

    def __init__(self, sandbox: Sandbox) -> None:
        """Initialize the DaytonaBackend with a Daytona sandbox client.

        Args:
            sandbox: Daytona sandbox instance
        """
        self._sandbox = sandbox
        self._timeout: int = 30 * 60  # 30 mins

    @property
    def id(self) -> str:
        """Unique identifier for the sandbox backend."""
        return self._sandbox.id

    def execute(
        self,
        command: str,
    ) -> ExecuteResponse:
        """Execute a command in the sandbox and return ExecuteResponse.

        Args:
            command: Full shell command string to execute.

        Returns:
            ExecuteResponse with combined output, exit code, optional signal, and truncation flag.
        """
        result = self._sandbox.process.exec(command, timeout=self._timeout)

        return ExecuteResponse(
            output=result.result,  # Daytona combines stdout/stderr
            exit_code=result.exit_code,
            truncated=False,
        )

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        """Download multiple files from the Daytona sandbox.

        Leverages Daytona's native batch download API for efficiency.
        Supports partial success - individual downloads may fail without
        affecting others.

        Args:
            paths: List of file paths to download.

        Returns:
            List of FileDownloadResponse objects, one per input path.
            Response order matches input order.
        """
        from daytona import FileDownloadRequest

        # Create batch download request using Daytona's native batch API
        download_requests = [FileDownloadRequest(source=path) for path in paths]
        daytona_responses = self._sandbox.fs.download_files(download_requests)

        # Convert Daytona results to our response format with error code mapping
        responses = []
        for resp in daytona_responses:
            error = None
            if resp.error:
                error_code = map_error_to_code(resp.error)
                error = f"{error_code.name if error_code else 'UNKNOWN'}: {resp.error}"
            responses.append(
                FileDownloadResponse(
                    path=resp.source,
                    content=resp.result if resp.result else b"",
                    error=error,
                )
            )
        return responses

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        """Upload multiple files to the Daytona sandbox.

        Leverages Daytona's native batch upload API for efficiency.
        Supports partial success - individual uploads may fail without
        affecting others.

        Args:
            files: List of (path, content) tuples to upload.

        Returns:
            List of FileUploadResponse objects, one per input file.
            Response order matches input order.
        """
        from daytona import FileUpload

        # Create batch upload request using Daytona's native batch API
        upload_requests = [FileUpload(source=content, destination=path) for path, content in files]
        upload_responses = self._sandbox.fs.upload_files(upload_requests)

        # Map Daytona responses with error code handling
        responses = []
        for upload_resp, (path, _) in zip(upload_responses, files):
            error = None
            if hasattr(upload_resp, "error") and upload_resp.error:
                error_code = map_error_to_code(upload_resp.error)
                error = f"{error_code.name if error_code else 'UNKNOWN'}: {upload_resp.error}"
            responses.append(FileUploadResponse(path=path, error=error))
        return responses
