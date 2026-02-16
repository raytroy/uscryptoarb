# USCryptoArb — Claude Project Instructions (Long Format)

## 1) Mission
Build a production-grade, fee-aware, executable cross-exchange crypto arbitrage detector for Ohio-eligible venues. The system prioritizes correctness and execution realism over optimistic theoretical returns.

Primary scope:
- Detect opportunities across USD and USDC pairs.
- Model all known costs before labeling opportunities executable.
- Preserve deterministic, auditable behavior from ingest to alert.

## 2) Relationship to Mathematica
This repository is a structured Python reimplementation of the prior Mathematica research system. Mathematica remains a reference for strategy intent and function parity, not a strict behavioral authority when production constraints require stronger safety guarantees.

Principle:
- Mathematica parity where practical.
- Production safeguards (typing, validation gates, async I/O, observability) where necessary.

## 3) Exchanges and Pairs
### Supported venues
- Kraken
- Coinbase
- Gemini

### Pair handling and symbol formats
- Canonical internal pair format: `BASE/QUOTE` (example: `BTC/USD`, `ETH/USDC`).
- Kraken external symbols: examples like `XXBTZUSD`.
- Coinbase external symbols: examples like `BTC-USD`.
- Gemini external symbols: examples like `btcusd`.

All translation runs through `src/uscryptoarb/venues/symbol_translator.py` and connector-specific `symbols.py` modules.

## 4) Key Mathematica Patterns (Condensed)
- Convert raw venue payloads into validated domain types at boundaries.
- Keep core math pure and deterministic.
- Separate opportunity generation from selection and thresholding.
- Treat data freshness and confidence as first-class filters.

## 5) Data Trust Boundaries (Condensed)
- **Untrusted**: all external API/network payloads.
- **Trusted**: validated domain objects returned by factory/validation functions.
- **Rule**: do not duplicate validation in pure downstream layers unless a new boundary is crossed.

## 6) Key Function Mapping
- `ReturnCalc[]` → `calculation/returns.py`
- `ArbCalcFinal[]` → `calculation/arb_calc.py`
- `TradesToExecute[]` → `strategy/trade_finder.py::find_trades_to_execute`
- `SelectTradeToExecute[]` → `strategy/selection.py::select_trade`
- `RunFinal[]` equivalent orchestration entry → `orchestration/scan_loop.py` and `__main__.py`

Full mapping lives in `docs/MATHEMATICA_MAP.md`.

## 7) Architecture (Condensed Diagram)
```
Domain/Core (pure)
  -> Validation (pure)
    -> Calculation (pure)
      -> Strategy (pure)
        -> Connectors/Adapters (imperative async I/O)
          -> Notification (imperative)
            -> Orchestration/App (imperative)
```

Dependency flow is one-way. Avoid circular imports and avoid placing business logic in connectors.

## 8) File Structure (Post-Rename, Current)
```
uscryptoarb/
├── src/uscryptoarb/
│   ├── __main__.py
│   ├── calculation/
│   │   ├── calc_types.py
│   │   ├── returns.py
│   │   ├── fees.py
│   │   ├── sizing.py
│   │   └── arb_calc.py
│   ├── connectors/
│   │   ├── connector_base.py
│   │   ├── kraken/
│   │   │   ├── client.py
│   │   │   ├── parser.py
│   │   │   └── symbols.py
│   │   ├── coinbase/
│   │   │   ├── client.py
│   │   │   ├── parser.py
│   │   │   └── symbols.py
│   │   └── gemini/
│   │       ├── client.py
│   │       ├── parser.py
│   │       └── symbols.py
│   ├── marketdata/topofbook.py
│   ├── markets/pairs.py
│   ├── misc/decimals.py
│   ├── notification/email.py
│   ├── orchestration/
│   │   ├── config.py
│   │   └── scan_loop.py
│   ├── strategy/
│   │   ├── selection.py
│   │   └── trade_finder.py
│   ├── validation/guards.py
│   └── venues/
│       ├── registry.py
│       └── symbol_translator.py
├── tests/
│   ├── unit/test_connectors/test_connector_base.py
│   ├── unit/test_orchestration/test_scan_loop.py
│   └── unit/test_strategy/test_trade_finder.py
└── docs/
    ├── LESSONS_LEARNED.md
    ├── DECISION_LOG.md
    ├── SESSION_HANDOFFS.md
    └── MATHEMATICA_MAP.md
```

## 9) Coding Rules 0–16 (Complete, Condensed)
0. Search `LESSONS_LEARNED.md` and `DECISION_LOG.md` before coding.
1. Keep core/calculation/strategy/validation pure (no side effects).
2. Keep I/O in connectors/notification/orchestration only.
3. Use explicit typed interfaces; avoid hidden globals.
4. Validate at trust boundaries; fail closed on critical missing data.
5. Use `Decimal` for all monetary values; never use float for money.
6. Preserve deterministic, reproducible behavior and UTC timestamps.
7. External I/O must be async with timeout, retries, and rate limiting.
8. Keep logs structured and traceable; avoid secret leakage.
9. Enforce one-way layering; no circular imports.
10. Propagation rule: update tests/docs/changelog in same session.
10.1 Avoid duplicate logic paths for same business rule.
10.2 Add or update tests for behavior changes and bug fixes.
10.3 Keep naming explicit and domain-oriented.
10.4 Keep function signatures stable unless intentionally refactored.
10.5 Preserve compatibility for existing call sites or update all call sites atomically.
10.6 Prefer reusable pure helpers after repeated patterns emerge.
10.7 Update operational docs for decisions and lessons.
10.8 **Unique module names** across `src/uscryptoarb/` (except `__init__.py` and connector internal `client.py`/`parser.py`/`symbols.py`).
10.9 **Refactor checkpoint**: second pattern instance must be flagged in SESSION_HANDOFFS and either refactored next session or deferred with rationale in DECISION_LOG.
11. Keep tests deterministic; no live network calls in tests.
12. Respect strict typing (`mypy`) and linting (`ruff`) cleanliness.
13. Keep changes minimal, reversible, and well-scoped.
14. Prefer composition over inheritance in pure logic.
15. Keep docs synchronized with implemented behavior.
16. When uncertain, choose the safer, conservative execution path.

## 10) Pre-Implementation Verification Checklist
- [ ] LESSONS_LEARNED searched
- [ ] DECISION_LOG searched
- [ ] MATHEMATICA_MAP checked (if porting)
- [ ] Existing patterns reviewed
- [ ] Imports verified to exist
- [ ] Module name uniqueness verified (`find src/ -name "<proposed_name>.py"`)
- [ ] Test strategy planned
- [ ] Approval/decision path confirmed

## 11) Deliverable Format Template
When returning implementation updates:
1. Summary of changed files and why.
2. Validation commands executed and outcomes.
3. Any operational follow-up required (docs sync, config updates).

## 12) Debugging and Traceability (Brief)
- Log ingest -> normalize -> evaluate -> validate -> emit path.
- Include rejection reasons for filtered opportunities.
- Keep enough context to replay a decision from logs and inputs.

## 13) Debug Config (YAML + CLI)
```yaml
debug:
  enabled: true
  log_level: DEBUG
  trace_pairs: [BTC/USD, ETH/USD]
```

CLI:
```bash
python -m uscryptoarb --debug --trace-pairs BTC/USD ETH/USD
```

## 14) Success Metrics
| Metric | Target |
|---|---|
| Ruff | 0 violations |
| mypy | 0 errors |
| Tests | 100% pass |
| Opportunity auditability | Reproducible from logs + snapshots |
| Docs sync | PROJECT -> CLAUDE -> UI aligned |

## 15) Config Keys (Brief)
- `venues.primary`
- `pairs`
- `arbitrage.threshold`
- `arbitrage.max_staleness_ms`
- `polling.interval_seconds`
- `fees.<venue>.buy/sell`
- `notifications.email.*`
- `debug.*`

## 16) Reference Links
- Canonical project policy: `PROJECT_INSTRUCTIONS.md`
- Decision record: `docs/DECISION_LOG.md`
- Lessons learned: `docs/LESSONS_LEARNED.md`
- Mathematica parity map: `docs/MATHEMATICA_MAP.md`
- Session continuity: `docs/SESSION_HANDOFFS.md`

---

Sync policy: edit `PROJECT_INSTRUCTIONS.md` first, regenerate this file second, then copy this file into the Claude.ai project instructions UI.
