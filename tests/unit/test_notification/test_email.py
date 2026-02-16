from __future__ import annotations

import asyncio
from unittest.mock import patch

from tests.helpers import make_arb_opportunity
from uscryptoarb.notification.email import EmailConfig, format_opportunity_email, send_alert


def _email_cfg(enabled: bool = True) -> EmailConfig:
    return EmailConfig(
        enabled=enabled,
        smtp_host="smtp.gmail.com",
        smtp_port=587,
        from_addr="bot@example.com",
        recipients=("a@example.com",),
        password="x",
    )


def test_format_opportunity_email_subject() -> None:
    subject, _ = format_opportunity_email(make_arb_opportunity())
    assert subject.startswith("ARB: BTC/USD")


def test_format_opportunity_email_body_contains_key_fields() -> None:
    _, body = format_opportunity_email(make_arb_opportunity())
    assert "Buy: kraken" in body
    assert "Sell: coinbase" in body
    assert "Timestamp (UTC):" in body


def test_send_alert_disabled_is_noop() -> None:
    async def run() -> None:
        with patch("uscryptoarb.notification.email._send_smtp") as mock_smtp:
            await send_alert(make_arb_opportunity(), _email_cfg(enabled=False))
            mock_smtp.assert_not_called()

    asyncio.run(run())


def test_send_alert_calls_smtp() -> None:
    async def run() -> None:
        with patch("uscryptoarb.notification.email._send_smtp") as mock_smtp:
            await send_alert(make_arb_opportunity(), _email_cfg())
            mock_smtp.assert_called_once()

    asyncio.run(run())


def test_send_alert_smtp_failure_logged_not_raised() -> None:
    async def run() -> None:
        with patch(
            "uscryptoarb.notification.email._send_smtp",
            side_effect=RuntimeError("smtp down"),
        ):
            await send_alert(make_arb_opportunity(), _email_cfg())

    asyncio.run(run())
