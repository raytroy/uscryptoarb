# USCryptoArb — Claude Project Instructions (Condensed)

## Mission
Build a production-grade cross-exchange crypto arbitrage system for Ohio-eligible exchanges, ported from proven Mathematica logic into Python with async architecture.

## Core Constraints
- USD and USDC are distinct currencies (never treated as equivalent)
- Functional core / imperative shell
- Validate at boundaries, trust downstream pure layers
- Use Decimal for all monetary math
- Async-only for external I/O

## Architecture
Domain/Core → Validation → Calculation → Strategy → Connectors → Execution/Notification → Orchestration

## Workflow (Every Task)
1. Search `docs/LESSONS_LEARNED.md` for relevant gotchas
2. Search `docs/DECISION_LOG.md` for settled decisions
3. Check `docs/MATHEMATICA_MAP.md` for function status (if porting)
4. Verify imports and existing patterns before coding
5. Update docs/changelog after implementation

## Key Functions
**Key Functions** (Mathematica reference → Python target):
`MarketBaseConvert[]`→`market_base_convert()`, `PairTranslator[]`→`pair_translator()`, `ReturnCalc[]`→`calc_return_raw/grs/net()`, `ArbCalcFinal[]`→`calc_arb_opportunity()`, `TradesToExecute[]`→`find_trades_to_execute()`, `SelectTradeToExecute[]`→`select_trade()`

See `docs/MATHEMATICA_MAP.md` for the complete mapping of all ~58 functions (DEC-010).

## Quality Bar
- Ruff clean
- mypy clean
- pytest passing
- No hidden side effects in pure layers
