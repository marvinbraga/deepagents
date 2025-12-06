"""Logging configuration for UltrathinkMiddleware.

This module provides structured logging for the ultrathink middleware,
enabling detailed tracking of thinking operations, fallback decisions,
and tool usage.

Logs are written to both console (minimal) and file (detailed) for
debugging and analysis purposes.

Example:
    Basic usage::

        from deepagents.middleware.ultrathink_logging import get_ultrathink_logger

        logger = get_ultrathink_logger()
        logger.info("Ultrathink enabled", budget_tokens=10000)

    Configure custom log file::

        from deepagents.middleware.ultrathink_logging import configure_logging

        configure_logging(
            log_dir="/path/to/logs",
            rotation="10 MB",
            retention="7 days",
        )
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    pass


# Default log directory
DEFAULT_LOG_DIR = Path.home() / ".deepagents" / "logs"

# Logger instance for ultrathink
_ultrathink_logger: logger.__class__ | None = None

# Configuration state
_configured = False


def configure_logging(
    log_dir: str | Path | None = None,
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    rotation: str = "10 MB",
    retention: str = "7 days",
    compression: str = "zip",
) -> None:
    """Configure logging for ultrathink middleware.

    This function sets up dual logging: minimal console output and
    detailed file logging for analysis.

    Args:
        log_dir: Directory for log files. Defaults to ~/.deepagents/logs.
        console_level: Minimum level for console output. Defaults to INFO.
        file_level: Minimum level for file output. Defaults to DEBUG.
        rotation: When to rotate log files. Defaults to "10 MB".
        retention: How long to keep old logs. Defaults to "7 days".
        compression: Compression format for rotated logs. Defaults to "zip".

    Example:
        Configure with custom settings::

            configure_logging(
                log_dir="/tmp/ultrathink_logs",
                file_level="TRACE",
                rotation="5 MB",
            )
    """
    global _configured

    if _configured:
        return

    # Resolve log directory
    log_path = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
    log_path.mkdir(parents=True, exist_ok=True)

    # Remove default handler
    logger.remove()

    # Add console handler (minimal, only warnings and above by default)
    logger.add(
        sys.stderr,
        level=console_level,
        format="<level>{level: <8}</level> | <cyan>ultrathink</cyan> | {message}",
        filter=lambda record: record["extra"].get("module") == "ultrathink",
    )

    # Add file handler (detailed)
    log_file = log_path / "ultrathink_{time:YYYY-MM-DD}.log"
    logger.add(
        str(log_file),
        level=file_level,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {message} | {extra}",
        rotation=rotation,
        retention=retention,
        compression=compression,
        filter=lambda record: record["extra"].get("module") == "ultrathink",
        enqueue=True,  # Thread-safe
    )

    _configured = True


def get_ultrathink_logger() -> logger.__class__:
    """Get the configured logger for ultrathink middleware.

    Returns a logger instance bound to the ultrathink module context.
    Automatically configures logging if not already done.

    Returns:
        Logger instance for ultrathink operations.

    Example:
        Get logger and log an event::

            logger = get_ultrathink_logger()
            logger.info("Tool executed", tool_name="think_step_by_step")
    """
    global _ultrathink_logger

    if not _configured:
        configure_logging()

    if _ultrathink_logger is None:
        _ultrathink_logger = logger.bind(module="ultrathink")

    return _ultrathink_logger


class UltrathinkLogContext:
    """Context manager for structured ultrathink logging.

    Provides a convenient way to log operations with consistent
    context and timing information.

    Attributes:
        logger: The bound logger instance.
        operation: Name of the operation being performed.
        context: Additional context data.

    Example:
        Log a tool execution with timing::

            with UltrathinkLogContext("think_step_by_step", problem="math") as ctx:
                # perform operation
                ctx.add_detail("steps", 5)
            # Automatically logs duration on exit
    """

    def __init__(self, operation: str, **context) -> None:
        """Initialize log context.

        Args:
            operation: Name of the operation (e.g., "tool_execution").
            **context: Additional context key-value pairs.
        """
        self.logger = get_ultrathink_logger()
        self.operation = operation
        self.context = context
        self._details: dict = {}
        self._start_time: float | None = None

    def add_detail(self, key: str, value: object) -> None:
        """Add a detail to the context.

        Args:
            key: Detail key.
            value: Detail value.
        """
        self._details[key] = value

    def __enter__(self) -> "UltrathinkLogContext":
        """Enter context and log start."""
        import time

        self._start_time = time.perf_counter()
        self.logger.debug(
            f"[START] {self.operation}",
            operation=self.operation,
            **self.context,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and log completion."""
        import time

        duration_ms = (
            (time.perf_counter() - self._start_time) * 1000
            if self._start_time
            else 0
        )

        if exc_type:
            self.logger.error(
                f"[ERROR] {self.operation}",
                operation=self.operation,
                duration_ms=round(duration_ms, 2),
                error=str(exc_val),
                **self.context,
                **self._details,
            )
        else:
            self.logger.debug(
                f"[END] {self.operation}",
                operation=self.operation,
                duration_ms=round(duration_ms, 2),
                **self.context,
                **self._details,
            )


# Convenience functions for common log operations
def log_middleware_init(
    budget_tokens: int,
    enabled_by_default: bool,
    fallback_mode: str,
    interleaved_thinking: bool,
) -> None:
    """Log middleware initialization.

    Args:
        budget_tokens: Configured token budget.
        enabled_by_default: Whether enabled by default.
        fallback_mode: Fallback mode setting.
        interleaved_thinking: Whether interleaved thinking is enabled.
    """
    log = get_ultrathink_logger()
    log.info(
        "UltrathinkMiddleware initialized",
        budget_tokens=budget_tokens,
        enabled_by_default=enabled_by_default,
        fallback_mode=fallback_mode,
        interleaved_thinking=interleaved_thinking,
    )


def log_model_detection(
    model_name: str,
    is_anthropic: bool,
    supports_native: bool,
    requires_fallback: bool,
) -> None:
    """Log model detection results.

    Args:
        model_name: Name of the detected model.
        is_anthropic: Whether it's an Anthropic model.
        supports_native: Whether it supports native thinking.
        requires_fallback: Whether fallback mode is needed.
    """
    log = get_ultrathink_logger()
    log.info(
        "Model detected",
        model_name=model_name,
        is_anthropic=is_anthropic,
        supports_native_thinking=supports_native,
        requires_fallback=requires_fallback,
    )


def log_thinking_enabled(budget_tokens: int, is_native: bool) -> None:
    """Log when thinking is enabled for a request.

    Args:
        budget_tokens: Token budget being used.
        is_native: Whether using native API or fallback.
    """
    log = get_ultrathink_logger()
    mode = "native" if is_native else "fallback"
    log.info(
        f"Extended thinking enabled ({mode})",
        budget_tokens=budget_tokens,
        mode=mode,
    )


def log_think_tool_call(
    problem: str,
    num_steps: int,
    conclusion: str,
) -> None:
    """Log think_step_by_step tool execution.

    Args:
        problem: The problem being reasoned about.
        num_steps: Number of reasoning steps.
        conclusion: The conclusion reached.
    """
    log = get_ultrathink_logger()
    log.info(
        "think_step_by_step executed",
        problem=problem[:100] + "..." if len(problem) > 100 else problem,
        num_steps=num_steps,
        conclusion=conclusion[:100] + "..." if len(conclusion) > 100 else conclusion,
    )


def log_tool_creation(tools: list[str], for_fallback: bool) -> None:
    """Log tool creation.

    Args:
        tools: List of tool names created.
        for_fallback: Whether includes fallback tools.
    """
    log = get_ultrathink_logger()
    log.debug(
        "Tools created",
        tools=tools,
        includes_fallback_tools=for_fallback,
    )


def log_state_change(key: str, old_value: object, new_value: object) -> None:
    """Log state changes.

    Args:
        key: State key being changed.
        old_value: Previous value.
        new_value: New value.
    """
    log = get_ultrathink_logger()
    log.debug(
        f"State changed: {key}",
        key=key,
        old_value=old_value,
        new_value=new_value,
    )
