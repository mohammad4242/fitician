import logging
from unittest.mock import Mock

from app.observability.diagnostics_logs import DiagnosticLogHandler


def test_sentry_transport_errors_do_not_recursively_create_actionable_issues():
    runtime = Mock()
    record = logging.LogRecord(
        "sentry_sdk.errors", logging.ERROR, __file__, 1, "transport unavailable", (), None
    )
    DiagnosticLogHandler(runtime).emit(record)
    runtime.submit.assert_not_called()
