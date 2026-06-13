import logging
import sys

from app.core.logging import SecureLogFormatter


def test_secure_log_formatter_redacts_structured_sensitive_values() -> None:
    record = logging.LogRecord(
        name="security-test",
        level=logging.INFO,
        pathname=__file__,
        lineno=12,
        msg="request payload=%s",
        args=(
            {
                "password": "correct horse battery staple",
                "api_token": "integration-token-value",
                "Cookie": "session=session-cookie-value",
                "card_number": "4111 1111 1111 1111",
                "raw_text": "ACME invoice total 9900 USD",
                "safe": "visible",
            },
        ),
        exc_info=None,
    )

    output = SecureLogFormatter("%(levelname)s %(request_id)s %(message)s").format(record)

    assert "correct horse battery staple" not in output
    assert "integration-token-value" not in output
    assert "session-cookie-value" not in output
    assert "4111 1111 1111 1111" not in output
    assert "ACME invoice total 9900 USD" not in output
    assert "visible" in output
    assert "[REDACTED]" in output


def test_secure_log_formatter_redacts_message_and_exception_text() -> None:
    try:
        raise ValueError(
            "Authorization: Bearer bearer-secret-value "
            "Cookie: session=exception-cookie-value"
        )
    except ValueError:
        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="security-test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=42,
        msg=(
            "password=message-password token=message-token "
            "card=5555-5555-5555-4444 raw_text=private invoice body"
        ),
        args=(),
        exc_info=exc_info,
    )

    output = SecureLogFormatter("%(levelname)s %(request_id)s %(message)s").format(record)

    for secret in (
        "bearer-secret-value",
        "exception-cookie-value",
        "message-password",
        "message-token",
        "5555-5555-5555-4444",
        "private invoice body",
    ):
        assert secret not in output
