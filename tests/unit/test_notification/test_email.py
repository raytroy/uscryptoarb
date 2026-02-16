from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import patch

from uscryptoarb.calculation.types import ArbLeg, ArbOpportunity
from uscryptoarb.notification.email import EmailConfig, format_opportunity_email, send_alert


def _opp() -> ArbOpportunity:
    leg = ArbLeg(
        venue="kraken",
        pair="BTC/USD",
        side="buy",
        price=Decimal("100"),
        mkt_curr_amt=Decimal("1"),
        base_curr_amt=Decimal("100"),
        fee_rate=Decimal("0.001"),
        trading_fee_base=Decimal("0.1"),
        withdrawal_fee=Decimal("0"),
    )
    return ArbOpportunity(
        pair="BTC/USD",
        buy_venue="kraken",
        sell_venue="coinbase",
        buy_price=Decimal("100"),
        sell_price=Decimal("101"),
        return_raw=Decimal("0.01"),
        return_grs=Decimal("0.009"),
        return_net=Decimal("0.008"),
        profit_grs_base=Decimal("1.0"),
        profit_net_base=Decimal("0.8"),
        buy_leg=leg,
        sell_leg=leg,
        market_currency="BTC",
        base_currency="USD",
        trade_amount=Decimal("1"),
        ts_calculated_ms=1707900000000,
    )


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
    subject, _ = format_opportunity_email(_opp())
    assert subject.startswith("ARB: BTC/USD")


def test_format_opportunity_email_body_contains_key_fields() -> None:
    _, body = format_opportunity_email(_opp())
    assert "Buy: kraken" in body
    assert "Sell: coinbase" in body
    assert "Timestamp (UTC):" in body


def test_send_alert_disabled_is_noop() -> None:
    async def run() -> None:
        with patch("uscryptoarb.notification.email._send_smtp") as mock_smtp:
            await send_alert(_opp(), _email_cfg(enabled=False))
            mock_smtp.assert_not_called()

    asyncio.run(run())


def test_send_alert_calls_smtp() -> None:
    async def run() -> None:
        with patch("uscryptoarb.notification.email._send_smtp") as mock_smtp:
            await send_alert(_opp(), _email_cfg())
            mock_smtp.assert_called_once()

    asyncio.run(run())


def test_send_alert_smtp_failure_logged_not_raised() -> None:
    async def run() -> None:
        with patch(
            "uscryptoarb.notification.email._send_smtp",
            side_effect=RuntimeError("smtp down"),
        ):
            await send_alert(_opp(), _email_cfg())

    asyncio.run(run())
