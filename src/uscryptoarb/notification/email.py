from __future__ import annotations

import asyncio
import logging
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage

from uscryptoarb.calculation.calc_types import ArbOpportunity

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class EmailConfig:
    """Email notification configuration.

    Populated from config.yaml notifications.email section + .env credentials.
    Owned by the notification layer per Section 5.2 import rules.
    """

    enabled: bool
    smtp_host: str
    smtp_port: int
    from_addr: str
    recipients: tuple[str, ...]
    password: str


def format_opportunity_email(opp: ArbOpportunity) -> tuple[str, str]:
    pct_display = f"{float(opp.return_net) * 100:+.2f}%"
    subject = f"ARB: {opp.pair} {pct_display} buy {opp.buy_venue} sell {opp.sell_venue}"
    ts_utc = datetime.fromtimestamp(
        opp.ts_calculated_ms / 1000,
        tz=timezone.utc,
    )
    body = "\n".join(
        [
            f"Pair: {opp.pair}",
            f"Buy: {opp.buy_venue} @ {opp.buy_price}",
            f"Sell: {opp.sell_venue} @ {opp.sell_price}",
            f"Return raw: {opp.return_raw}",
            f"Return gross: {opp.return_grs}",
            f"Return net: {opp.return_net}",
            f"Profit net ({opp.base_currency}): {opp.profit_net_base}",
            f"Trade amount ({opp.market_currency}): {opp.trade_amount}",
            f"Timestamp (UTC): {ts_utc.isoformat()}",
        ]
    )
    return subject, body


async def send_alert(opp: ArbOpportunity, config: EmailConfig) -> None:
    if not config.enabled or not config.from_addr or not config.password or not config.recipients:
        return

    subject, body = format_opportunity_email(opp)
    try:
        await asyncio.to_thread(
            _send_smtp,
            config.smtp_host,
            config.smtp_port,
            config.from_addr,
            config.password,
            config.recipients,
            subject,
            body,
        )
    except Exception as exc:
        logger.error("Email delivery failed for %s: %s", opp.pair, exc)


def _send_smtp(
    host: str,
    port: int,
    from_addr: str,
    password: str,
    recipients: tuple[str, ...],
    subject: str,
    body: str,
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"CAS Crypto Asset Systems <{from_addr}>"
    msg["To"] = ", ".join(recipients)
    msg.set_content(body)

    with smtplib.SMTP(host, port) as server:
        server.starttls()
        server.login(from_addr, password)
        server.send_message(msg)
