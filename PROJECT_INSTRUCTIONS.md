# USCryptoArb — Project Instructions

> **For WebUI**: Use condensed version in `CLAUDE_INSTRUCTIONS.md` (under 8K chars)
> **For Repo**: This document contains full specifications

---

## 1. Mission

Build a production-grade cross-exchange crypto arbitrage system for Ohio-eligible exchanges. Port the proven Mathematica system (10,000+ successful Type-2 trades) to Python with modern async architecture.

**Primary Focus**: Type-2 arbitrage (same pair, different exchanges)
**Secondary**: Type-1 triangular (same exchange)

---

## 2. Source Documents

| Document | Purpose | Location |
|----------|---------|----------|
| `CLAUDE_INSTRUCTIONS.md` | WebUI system prompt (<8K chars) | Repo root |
| `PROJECT_INSTRUCTIONS.md` | Full specifications (this file) | Repo root |
| `CryptoArbitrage_V14.9.4_NoKeys.nb` | Mathematica reference implementation | Repo root |
| `README.md` | User-facing documentation | Repo root |
| `CHANGELOG.md` | Version history | Repo root |

---

## 3. Exchanges

### 3.1 Primary (Phase 1)
| Exchange | Ohio Status | SDK | Symbol Format |
|----------|-------------|-----|---------------|
| Kraken | ✅ (not ME/NY) | `python-kraken-sdk` | `XBTUSD` (XBT=BTC) |
| Coinbase | ✅ | `coinbase-advanced-py` | `BTC-USD` |
| Gemini | ✅ OHMT licensed | Custom wrapper | `btcusd` |

### 3.2 Secondary (Phase 2)
| Exchange | Ohio Status | SDK |
|----------|-------------|-----|
| Bitstamp | Verify | Direct REST |
| bitFlyer USA | ✅ OHMT126 | Lightning API |
| OKCoin | ✅ | V5 REST/WS |

### 3.3 Tertiary (Phase 3)
CEX.IO, Crypto.com (verify eligibility)

---

## 4. Trading Pairs

```yaml
pairs:
  - BTC/USD
  - BTC/USDC
  - LTC/USD
  - LTC/USDC
  - LTC/BTC
  - SOL/USD
  - SOL/USDC
  - SOL/BTC
```

**Rule**: USD ≠ USDC. Never assume equivalence.

---

## 5. Architecture

### 5.1 Layer Diagram

```
┌────────────────────────────────────────────────────────────┐
│  Orchestration (imperative)                                │
│  - main.py, CLI, scheduling, config loading                │
└────────────────────────────────────────────────────────────┘
                            │
┌────────────────────────────────────────────────────────────┐
│  Notification (imperative) - Email alerts                  │
└────────────────────────────────────────────────────────────┘
                            │
┌────────────────────────────────────────────────────────────┐
│  Execution (imperative) - Order placement, balances        │
└────────────────────────────────────────────────────────────┘
                            │
┌────────────────────────────────────────────────────────────┐
│  Connectors (imperative) - Per-exchange API adapters       │
└────────────────────────────────────────────────────────────┘
                            │
┌────────────────────────────────────────────────────────────┐
│  Strategy (pure) - TradesToExecute, SelectTradeToExecute   │
└────────────────────────────────────────────────────────────┘
                            │
┌────────────────────────────────────────────────────────────┐
│  Calculation (pure) - ReturnCalc, ArbCalcFinal, fees       │
└────────────────────────────────────────────────────────────┘
                            │
┌────────────────────────────────────────────────────────────┐
│  Validation (pure) - MissingCheck, orderbook validation    │
└────────────────────────────────────────────────────────────┘
                            │
┌────────────────────────────────────────────────────────────┐
│  Domain/Core (pure) - Dataclasses, MarketBaseConvert       │
└────────────────────────────────────────────────────────────┘
```

### 5.2 Import Rules

**Imports flow DOWN only. Circular imports are a hard failure.**

```
Domain/Core     → (nothing)
Validation      → Domain/Core
Calculation     → Domain/Core, Validation
Strategy        → Domain/Core, Validation, Calculation
Connectors      → Domain/Core
Execution       → All pure layers, Connectors
Notification    → Domain/Core
Orchestration   → Everything
```

### 5.3 File Structure

```
uscryptoarb/
├── src/uscryptoarb/
│   ├── __init__.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── types.py          # All dataclasses
│   │   ├── pair_utils.py     # MarketBaseConvert, PairTranslator
│   │   └── decimal_utils.py  # to_decimal, floor_to_step
│   ├── validation/
│   │   ├── __init__.py
│   │   ├── guards.py         # is_missing, require_present, require_positive, require_non_negative
│   │   └── orderbook.py      # validate_orderbook
│   ├── calculation/
│   │   ├── __init__.py
│   │   ├── returns.py        # calc_return, calc_returns
│   │   ├── fees.py           # apply_trading_fees, apply_withdrawal_fees
│   │   └── arb_calc.py       # calc_arb_final
│   ├── strategy/
│   │   ├── __init__.py
│   │   ├── selection.py      # select_trade, passes_threshold
│   │   └── scanner.py        # find_trades_to_execute
│   ├── connectors/
│   │   ├── __init__.py
│   │   ├── base.py           # BaseConnector protocol
│   │   ├── kraken/
│   │   ├── coinbase/
│   │   └── gemini/
│   ├── execution/
│   │   ├── __init__.py
│   │   └── orders.py
│   ├── notification/
│   │   ├── __init__.py
│   │   └── email.py
│   └── config.py
├── tests/
│   ├── unit/
│   │   ├── test_core/
│   │   ├── test_validation/
│   │   ├── test_calculation/
│   │   └── test_strategy/
│   ├── integration/
│   └── conftest.py           # Shared fixtures
├── notebooks/
│   ├── 01_kraken_connectivity.ipynb
│   ├── 02_coinbase_connectivity.ipynb
│   ├── 03_cross_exchange_comparison.ipynb
│   └── ...
├── config.yaml
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── CLAUDE_INSTRUCTIONS.md    # WebUI version
└── PROJECT_INSTRUCTIONS.md   # This file
```

---

## 6. Key Patterns (from Mathematica)

### 6.1 Three Databases

```python
# Must exist and be passed to calculation functions
trading_fees_db: List[TradingFees]      # exchangeTradingFeesDatabase
withdrawal_db: List[WithdrawalFee]      # withdrawalDatabase
trading_info_db: List[TradingAccuracy]  # tradingInfoDatabase
```

### 6.2 Data Trust Boundaries

**Principle**: Validate once at data boundaries, trust downstream. This replaces the Mathematica pattern of checking `MissingQ` inside every function.
```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  External Data  │────▶│  Boundary Layer  │────▶│  Pure Functions │
│  (untrusted)    │     │  (validates)     │     │  (trusts input) │
└─────────────────┘     └──────────────────┘     └─────────────────┘
     API response          Connector/Parser        Calculation/Strategy
     Config file           Factory function        No validation code
     User input            __post_init__           Just math
```

#### 6.2.1 Where Validation Lives

| Location | What Gets Validated | Example |
|----------|---------------------|---------|
| Connector `parse_*` functions | API responses | `parse_kraken_ticker()` |
| Factory functions | Raw inputs → domain types | `tob_from_raw()` |
| `__post_init__` methods | Dataclass invariants | Crossed book check |
| Config loaders | YAML/env inputs | `load_config()` |

#### 6.2.2 Where Validation Does NOT Live

| Layer | Why No Validation |
|-------|-------------------|
| `calculation/` | Inputs are already-validated domain types |
| `strategy/` | Same — receives validated types from calculation |

**If you're adding `if x is None` or `require_*` in calculation/strategy, something is wrong upstream.**

#### 6.2.3 Validation Guards API

Located in `validation/guards.py`:
```python
from uscryptoarb.validation import (
    is_missing,           # Check: None, "", [], {}, NaN, Infinity
    require_present,      # Raise if missing, return value unchanged
    require_positive,     # For prices, fees (must be > 0)
    require_non_negative, # For balances, quantities (can be 0)
)
```

#### 6.2.4 Factory Function Pattern (Preferred)

Factory functions are the primary validation boundary. They accept raw/untrusted inputs and return validated, frozen domain types:
```python
# marketdata/topofbook.py
def tob_from_raw(
    *,
    venue: str,
    pair: str,
    bid_px: DecimalLike,  # Could be str, int, Decimal
    bid_sz: DecimalLike,
    ask_px: DecimalLike,
    ask_sz: DecimalLike,
    ts_local_ms: int,
    ts_exchange_ms: int | None,
) -> TopOfBook:
    """
    Factory that validates at construction boundary.
    
    - Converts DecimalLike → Decimal (rejects floats)
    - Validates all fields present and positive
    - Checks orderbook invariants (not crossed)
    
    Raises ValueError if any validation fails.
    """
    t = TopOfBook(
        venue=venue,
        pair=pair,
        bid_px=to_decimal(bid_px),
        bid_sz=to_decimal(bid_sz),
        ask_px=to_decimal(ask_px),
        ask_sz=to_decimal(ask_sz),
        ts_local_ms=int(ts_local_ms),
        ts_exchange_ms=None if ts_exchange_ms is None else int(ts_exchange_ms),
    )
    validate_tob(t)  # Enforces all invariants
    return t
```

Connectors use factory functions — validation happens at the boundary:
```python
# connectors/kraken/ticker.py
async def fetch_ticker(self, pair: str) -> TopOfBook:
    raw = await self._client.get_ticker(pair)
    ts_now = int(time.time() * 1000)
    
    # Factory validates; raises ValueError if garbage
    return tob_from_raw(
        venue="kraken",
        pair=pair,
        bid_px=raw["b"][0],  # Might be missing/garbage
        bid_sz=raw["b"][2],
        ask_px=raw["a"][0],
        ask_sz=raw["a"][2],
        ts_local_ms=ts_now,
        ts_exchange_ms=None,
    )
```

#### 6.2.5 __post_init__ Pattern (Defense in Depth)

For critical invariants that must NEVER be violated, add `__post_init__` as a second layer. This catches programming errors even if a factory is bypassed:
```python
@dataclass(frozen=True, slots=True)
class TopOfBook:
    venue: str
    pair: str
    bid_px: Decimal
    ask_px: Decimal
    bid_sz: Decimal
    ask_sz: Decimal
    ts_local_ms: int
    ts_exchange_ms: int | None
    
    def __post_init__(self) -> None:
        # Critical invariant: book cannot be crossed
        if self.bid_px > 0 and self.ask_px > 0 and self.bid_px >= self.ask_px:
            raise ValueError(
                f"Crossed book: bid {self.bid_px} >= ask {self.ask_px}"
            )
```

#### 6.2.6 What "Trusted" Means Downstream

After passing through a boundary, code can assume:

| Guarantee | Enforced By | Downstream Benefit |
|-----------|-------------|-------------------|
| Not None/empty | `require_present()` | No `if x is None` checks |
| Positive price | `require_positive()` | Safe to divide by price |
| Non-negative qty | `require_non_negative()` | No negative quantity bugs |
| Finite Decimal | `is_missing()` rejects NaN/Inf | Deterministic math |
| Immutable | `@dataclass(frozen=True)` | Cannot mutate after validation |
| Invariants hold | `__post_init__` | Book not crossed, etc. |

#### 6.2.7 Error Handling at Boundaries

Validation failures raise `ValueError` immediately. The orchestration layer handles recovery:
```python
# orchestration/scanner.py
async def poll_all_venues(pairs: list[str]) -> dict[str, TopOfBook]:
    results: dict[str, TopOfBook] = {}
    
    for venue, connector in connectors.items():
        for pair in pairs:
            try:
                tob = await connector.fetch_ticker(pair)
                results[f"{venue}:{pair}"] = tob
            except ValueError as e:
                # Validation failed — log and skip
                logger.warning(f"Invalid data from {venue} for {pair}: {e}")
                continue
    
    return results  # Only contains valid data

# Pure functions receive only valid data
opportunities = find_arbitrage(results)  # No validation inside
```

#### 6.2.8 Summary Rules

1. **Validation guards live ONLY in**:
   - `validation/` module (the guards themselves)
   - Connector `parse_*` / `fetch_*` functions
   - Factory functions (`*_from_raw`)
   - Dataclass `__post_init__` methods
   - Config `load_*` functions

2. **Pure layers have ZERO validation code**:
   - `calculation/` — just math
   - `strategy/` — just logic
   - If adding validation here, fix the boundary instead

3. **Failed validation = immediate ValueError**:
   - Don't return `None` or sentinel values
   - Don't silently skip — raise and let orchestration decide

4. **Frozen dataclasses are the contract**:
   - Once constructed, a `TopOfBook` is guaranteed valid
   - Downstream code trusts the type, not runtime checks

### 6.3 Return Metrics

| Metric | Formula | Use |
|--------|---------|-----|
| `return_raw` | (sell - buy) / buy | Before any fees |
| `return_grs` | (eff_sell - eff_buy) / eff_buy | After trading fees |
| `return_net` | (net_proceeds - net_cost) / net_cost | After ALL fees |

### 6.4 Limiting Reactant

What constrains trade size:
- `buyBalance` - Your balance on buy exchange
- `sellBalance` - Your balance on sell exchange
- `buyLiquidity` - Orderbook depth at best ask
- `sellLiquidity` - Orderbook depth at best bid

### 6.5 Fee Calculation Flow

```
Buy Side:
  MktCurrAmt = input_amount
  BaseCurrAmt = MktCurrAmt * buy_price
  MktCurrAmtGrs = MktCurrAmt * (1 + buy_fee_pct)
  
Sell Side:
  MktCurrAmtGrs = MktCurrAmt * (1 - sell_fee_pct)
  
Net:
  MktCurrAmtNet = MktCurrAmtGrs - withdrawal_fee
```

---

## 7. Coding Rules

### 7.1 Prime Directive

Deliver correct, testable, observable code. Reliability over cleverness. When uncertain, ask rather than guess.

### 7.2 Workflow (MANDATORY)

```
1. ANALYZE - Understand requirements, check existing patterns
2. PLAN    - Present approach with file list, wait for approval
3. IMPLEMENT - Write code with full propagation
4. VALIDATE - Run tests, verify behavior
5. SUMMARIZE - Document what changed and why
```

**Never skip step 2 (approval).**

### 7.3 Full Propagation Rule (CRITICAL)

**Every change MUST update ALL affected items:**

| Item | When to Update |
|------|----------------|
| Source code | Always (the change itself) |
| Type hints | Always (strict mypy) |
| Docstrings | If function signature or behavior changed |
| Unit tests | Always add/update tests for the change |
| Integration tests | If external behavior changed |
| README.md | If user-facing behavior changed |
| CHANGELOG.md | Every PR-worthy change |
| config.yaml | If new config options added |
| Example notebooks | If API changed |

**Incomplete propagation = incomplete work.**

### 7.4 Change Deliverable Format

```markdown
## What Changed
- `src/uscryptoarb/calculation/returns.py`: Added `calc_return()` function
- `tests/unit/test_calculation/test_returns.py`: Added tests

## Why
Implements Mathematica's ReturnCalc[] for computing price returns.

## Propagation Checklist
- [x] Source code
- [x] Type hints (Decimal -> Decimal)
- [x] Docstrings
- [x] Unit tests (3 test cases)
- [ ] README (not needed - internal function)
- [x] CHANGELOG (added to Unreleased)

## Validation
```bash
pytest tests/unit/test_calculation/test_returns.py -v
mypy src/uscryptoarb/calculation/returns.py
```

## Test Output
```
tests/unit/test_calculation/test_returns.py::test_positive_return PASSED
tests/unit/test_calculation/test_returns.py::test_negative_return PASSED
tests/unit/test_calculation/test_returns.py::test_zero_start_raises PASSED
```
```

### 7.5 Functional Programming Rules

| Rule | Implementation |
|------|----------------|
| Immutable types | `@dataclass(frozen=True, slots=True)` |
| Pure functions | No side effects in calculation/validation/strategy |
| Explicit I/O | Side effects only in connectors/execution/notification |
| Composition | Functions return values, don't modify state |

### 7.6 Money Math Rules

```python
# NEVER use float for money
price: float = 100.50  # WRONG

# ALWAYS use Decimal
price: Decimal = Decimal("100.50")  # CORRECT

# Reject floats explicitly
def to_decimal(value: Union[str, int, Decimal]) -> Decimal:
    if isinstance(value, float):
        raise TypeError("Floats not allowed - use str or Decimal")
    return Decimal(str(value))
```

### 7.7 Async Rules

- All network I/O must be `async/await`
- No blocking calls in event loop
- Use `asyncio.gather()` for concurrent requests
- Respect per-exchange rate limits

### 7.8 Error Handling

```python
# Timeouts on all network calls
async with httpx.AsyncClient(timeout=10.0) as client:
    ...

# Bounded retries with backoff
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
async def fetch_orderbook(...):
    ...

# Stale data detection
if snapshot.ts_local_ms < now_ms - MAX_STALENESS_MS:
    logger.warning("Stale orderbook data")
```

---

## 8. Testing Standards

### 8.1 Test Requirements

| Layer | Test Type | Required |
|-------|-----------|----------|
| Core | Unit | 100% coverage |
| Validation | Unit | 100% coverage |
| Calculation | Unit + property-based | 100% coverage |
| Strategy | Unit | 90%+ coverage |
| Connectors | Integration (mocked) | Happy path + errors |

### 8.2 Test Naming

```python
# Pattern: test_<function>_<scenario>_<expected>
def test_calc_return_positive_prices_returns_correct_value():
    ...

def test_calc_return_zero_start_raises_value_error():
    ...
```

### 8.3 Fixtures Location

- Shared fixtures: `tests/conftest.py`
- Module fixtures: `tests/unit/test_<module>/conftest.py`
- Sample data: `tests/fixtures/`

---

## 9. Configuration

### 9.1 config.yaml Structure

```yaml
# === Venues ===
venues:
  primary: [kraken, coinbase, gemini]
  secondary: [bitstamp, bitflyer, okcoin]

# === Pairs ===
pairs:
  - BTC/USD
  - BTC/USDC
  - LTC/USD
  - LTC/USDC
  - LTC/BTC
  - SOL/USD
  - SOL/USDC
  - SOL/BTC

# === Arbitrage ===
arbitrage:
  threshold: "0.0055"          # 0.55% minimum return
  min_bankroll_limit: "0.10"   # Max 10% of balance per trade
  max_staleness_ms: 5000

# === Polling ===
polling:
  interval_seconds: 5
  max_concurrent_requests: 10

# === Fees (fallbacks) ===
fees:
  kraken:
    buy: "0.0026"
    sell: "0.0026"
  coinbase:
    buy: "0.006"
    sell: "0.006"
  gemini:
    buy: "0.004"
    sell: "0.004"

# === Notifications ===
notifications:
  email:
    enabled: true
    smtp_host: smtp.gmail.com
    smtp_port: 587
    recipients: []

# === Debug ===
debug:
  enabled: false
  trace_pairs: []
  log_level: INFO
```

### 9.2 Environment Variables

```bash
# .env (git-ignored)
KRAKEN_API_KEY=...
KRAKEN_API_SECRET=...
COINBASE_API_KEY=...
COINBASE_API_SECRET=...
GEMINI_API_KEY=...
GEMINI_API_SECRET=...
SMTP_PASSWORD=...
```

---

## 10. Git Workflow

### 10.1 Branch Strategy

```
main              - Production-ready code
  └── develop     - Integration branch
       └── feature/xxx  - Feature branches
       └── fix/xxx      - Bug fixes
```

### 10.2 Commit Messages

```
<type>: <short description>

<body - what and why>

Types: feat, fix, refactor, test, docs, chore
```

### 10.3 PR Checklist

- [ ] All tests pass
- [ ] mypy passes with no errors
- [ ] ruff passes with no errors
- [ ] Propagation complete (tests, docs, changelog)
- [ ] No secrets in code

---

## 11. Development Phases

### Phase 1: Detection (Current)
- Public APIs only
- REST polling
- Email alerts
- Kraken + Coinbase + Gemini

### Phase 2: WebSocket
- Real-time orderbooks
- Latency optimization
- Add secondary exchanges

### Phase 3: Paper Trading
- Simulated execution
- PnL tracking
- Performance metrics

### Phase 4: Live Trading
- API key integration
- Order placement
- Risk limits

---

## 12. Mathematica Function Mapping

| Mathematica | Python Module | Function |
|-------------|---------------|----------|
| `MarketBaseConvert[]` | `core.pair_utils` | `market_base_convert()` |
| `PairTranslator[]` | `core.pair_utils` | `pair_translator()` |
| `MissingCheck[]` | `validation.guards` | `is_missing(), require_present(), require_positive(), require_non_negative()` |
| `OrderBookParser[]` | `connectors.*.parser` | `parse_orderbook()` |
| `ReturnCalc[]` | `calculation.returns` | `calc_return()` |
| `ArbCalcFinal[]` | `calculation.arb_calc` | `calc_arb_final()` |
| `TradesToExecute[]` | `strategy.scanner` | `find_trades_to_execute()` |
| `SelectTradeToExecute[]` | `strategy.selection` | `select_trade()` |
| `ExecuteTradesL3[]` | `execution.orders` | `execute_trades()` |
| `Final[]` | `__main__` | `run_scan_cycle()` |

---

## 13. Quick Reference

### Pre-Implementation Checklist

```
[ ] Mathematica function identified (if porting)
[ ] Existing patterns in codebase reviewed
[ ] All imports verified to exist
[ ] Test approach planned
[ ] Approval received
```

### Propagation Checklist

```
[ ] Source code updated
[ ] Type hints added/updated
[ ] Docstrings match implementation
[ ] Unit tests added/updated
[ ] CHANGELOG.md updated
[ ] README.md updated (if user-facing)
[ ] config.yaml updated (if new options)
```

---

## Document History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-04 | 1.0.0 | Initial comprehensive instructions |
