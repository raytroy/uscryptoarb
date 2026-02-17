# Decision Log

> **Purpose**: Track architectural and design decisions with rationale, so future sessions don't re-debate settled questions.
> **Rule**: Every significant design choice gets logged here. When a decision is revisited, check here first.
> **Authoritative for**: Why things are the way they are. This is the "institutional memory" of the project.

---

## How to Use This File

**Before proposing a design change**: Search this file to see if the topic was already decided.
**When making a new decision**: Add an entry using the template below.
**When revisiting a decision**: Add a new entry referencing the original, with the new rationale.

### Entry Template

```
### DEC-NNN: <Decision title>
- **Date**: YYYY-MM-DD
- **Status**: [Accepted | Superseded by DEC-XXX | Under Review]
- **Context**: <What problem or question prompted this decision>
- **Decision**: <What was decided>
- **Alternatives Considered**:
  1. <Alternative A> — rejected because <reason>
  2. <Alternative B> — rejected because <reason>
- **Rationale**: <Why this option was chosen>
- **Consequences**: <What this means for implementation>
- **References**: <Links to relevant docs, conversations, or code>
```

---

## Foundational Decisions

### DEC-001: USD and USDC are distinct currencies — no implicit conversion
- **Date**: 2026-01-04
- **Status**: Superseded by DEC-011, DEC-018
- **Context**: USDC is pegged to USD at ~$1.00 but they are not identical. Treating them as interchangeable would create false arbitrage signals and incorrect P&L calculations.
- **Decision**: USD and USDC are always treated as separate currencies. No implicit conversion, no peg assumptions. `BTC/USD` and `BTC/USDC` are different trading pairs.
- **Alternatives Considered**:
  1. Treat USDC as equivalent to USD with a configurable spread tolerance — rejected because peg deviations do occur (e.g., March 2023 USDC depeg to $0.88), and assuming equivalence creates systemic risk.
  2. Model USDC→USD as a separate conversion step with fees — deferred to Phase 2+; adds complexity without value in Phase 1 detection.
- **Rationale**: Correctness over convenience. The Mathematica system also treats them separately, and this has been validated across 10,000+ trades. Arbitrage between USD and USDC pairs is itself a valid opportunity, not an equivalence.
- **Consequences**: All pair matching, return calculations, and balance tracking must distinguish USD from USDC. Symbol translation must map them independently per exchange.
- **References**: PROJECT_INSTRUCTIONS.md Section 4, CLAUDE_INSTRUCTIONS.md Pairs section

### DEC-002: Functional core, imperative shell architecture
- **Date**: 2026-01-04
- **Status**: Accepted
- **Context**: Need to balance testability with the inherently I/O-heavy nature of exchange connectivity.
- **Decision**: Pure functions for all transforms, calculations, and logic. Side effects (HTTP, WebSocket, file I/O, scheduling) only in connectors, execution, notification, and orchestration layers.
- **Alternatives Considered**:
  1. Full OOP with dependency injection — rejected because adds ceremony without value for a system that's fundamentally data-transform pipelines.
  2. Pure functional with IO monad — rejected because Python doesn't support this idiom well and it would hinder readability.
- **Rationale**: Pure functions are trivially testable (input → output, no mocks needed). The Mathematica system is inherently functional. This maps naturally.
- **Consequences**: `calculation/` and `strategy/` layers have zero side effects and zero I/O imports. All state flows through function parameters, not global state.
- **References**: PROJECT_INSTRUCTIONS.md Section 5.1, Coding Rule 2.1

### DEC-003: Validate at boundaries, trust downstream (not scattered MissingCheck)
- **Date**: 2026-01-04
- **Status**: Accepted
- **Context**: Mathematica's `MissingCheck[]` is called inside nearly every function because Mathematica lacks typed frozen containers. Porting this literally would mean `if x is None` checks in every Python function.
- **Decision**: Validation happens ONLY at data boundaries (connectors, factories, `__post_init__`, config loaders). Pure layers (`calculation/`, `strategy/`) have zero validation code and trust their typed inputs.
- **Alternatives Considered**:
  1. Port MissingCheck literally — add `is_missing()` calls in every function — rejected because it's noise in a typed language with frozen dataclasses. Makes code harder to read and creates false sense of safety (if boundary is wrong, interior checks won't save you).
  2. Use Optional types everywhere and force callers to unwrap — rejected because it pushes complexity to every call site instead of concentrating it at boundaries.
- **Rationale**: Frozen dataclasses are the contract. Once a `TopOfBook` is constructed, it's guaranteed valid (non-None, non-NaN, non-crossed, positive prices). Downstream code trusts the type. This is both safer and cleaner than scattered checks.
- **Consequences**: Adding validation in `calculation/` or `strategy/` is a code smell — fix the boundary instead. `ValueError` at boundaries, not sentinel returns.
- **References**: PROJECT_INSTRUCTIONS.md Section 6.2, `validation/guards.py` module docstring, LESSONS_LEARNED.md LL-020

### DEC-004: Frozen dataclasses as domain contracts
- **Date**: 2026-01-04
- **Status**: Accepted
- **Context**: Need immutable domain objects that can be safely passed between layers without defensive copying.
- **Decision**: All domain types use `@dataclass(frozen=True, slots=True)`. Return new objects instead of mutating existing ones.
- **Alternatives Considered**:
  1. Regular (mutable) dataclasses — rejected because mutation bugs are hard to trace in financial systems. A TopOfBook that changes after creation could cause inconsistent arbitrage calculations.
  2. NamedTuples — rejected because they lack `__post_init__` for invariant checking and have less ergonomic field access for complex types.
  3. Pydantic models — rejected because Pydantic adds a heavy dependency, has complex validation semantics, and we need explicit control over validation timing (boundaries only, not every construction).
- **Rationale**: Frozen + slots gives immutability, memory efficiency, and slot-based attribute access. Combined with factory functions, this pattern ensures validated, immutable domain objects.
- **Consequences**: All mutations create new objects. `__post_init__` can enforce invariants as a defense-in-depth layer.
- **References**: PROJECT_INSTRUCTIONS.md Section 7.5, Coding Rule 2.2

---

## Exchange Decisions

### DEC-005: Exchange SDK choices
- **Date**: 2026-01-04
- **Status**: Superseded by DEC-011 and DEC-018
- **Context**: Each exchange needs a client library. Options include official SDKs, third-party wrappers, and custom REST/WebSocket clients.
- **Decision**:
  - Kraken: `python-kraken-sdk` (well-maintained, good async support)
  - Coinbase: `coinbase-advanced-py` (official SDK for Advanced Trade API)
  - Gemini: Custom wrapper (no well-maintained Python SDK available)
- **Alternatives Considered**:
  1. `ccxt` (unified multi-exchange library) — rejected because it abstracts away exchange-specific details we need for accurate fee modeling, rate limit handling, and symbol translation. The abstraction hides exactly the details that matter for arbitrage.
  2. Raw `httpx` for all exchanges — rejected for Kraken and Coinbase because SDK handles auth, rate limiting, and response parsing. Acceptable for Gemini where no good SDK exists.
- **Rationale**: Use SDKs where they save significant effort and are well-maintained. Use custom code where SDKs don't exist or abstract away needed details. Never use unified libraries that hide exchange-specific behavior.
- **Consequences**: Each connector has exchange-specific code. SymbolTranslator handles the format differences. Connectors output canonical types regardless of SDK used.
- **References**: PROJECT_INSTRUCTIONS.md Section 3, `venues/symbol_translator.py`

### DEC-006: Ohio-eligible exchanges only
- **Date**: 2026-01-04
- **Status**: Accepted
- **Context**: Crypto exchange regulatory status varies by US state. Need to ensure all exchanges are legally available in Ohio.
- **Decision**: Primary exchanges (Kraken, Coinbase, Gemini) are verified Ohio-eligible. Secondary exchanges (Bitstamp, bitFlyer, OKCoin) to be verified before Phase 2. Exchanges without Ohio money transmitter licenses are excluded.
- **Alternatives Considered**:
  1. Include all major exchanges and filter later — rejected because trading on a non-licensed exchange in Ohio creates legal risk regardless of profitability.
- **Rationale**: Legal compliance is non-negotiable. Better to start with fewer verified exchanges than risk issues.
- **Consequences**: Exchange additions require Ohio MTL verification. `venues/registry.py` tracks eligibility status.
- **References**: PROJECT_INSTRUCTIONS.md Section 3, `venues/registry.py`

---

## Technical Decisions

### DEC-007: Decimal (not float) for all financial values
- **Date**: 2026-01-04
- **Status**: Accepted
- **Context**: Financial calculations require exact decimal arithmetic. IEEE 754 binary floating-point introduces representation errors.
- **Decision**: Use Python `Decimal` for all prices, quantities, fees, balances, and return calculations. `to_decimal()` is the single entry point that explicitly rejects `float` inputs.
- **Alternatives Considered**:
  1. Python `float` with rounding — rejected because rounding errors compound across multi-leg calculations. `0.1 + 0.2 != 0.3` in float.
  2. Integer cents/satoshis — rejected because different pairs have different precisions (BTC to 8 decimals, USD to 2), making a universal integer representation complex and error-prone.
- **Rationale**: `Decimal` provides exact decimal arithmetic, configurable precision, and explicit rounding modes. It's the standard for financial Python code.
- **Consequences**: All numeric conversions go through `to_decimal()`. Factory functions convert raw API strings to `Decimal`. Performance is acceptable for polling-based detection (sub-millisecond for typical calculations).
- **References**: PROJECT_INSTRUCTIONS.md Section 7.6, `core/decimal_utils.py`, LESSONS_LEARNED.md LL-010

---

## Process Decisions

### DEC-008: Exploration notebooks before production connectors
- **Date**: 2026-01-04
- **Status**: Accepted
- **Context**: Each exchange API has unique behaviors (symbol formats, rate limits, response structures, authentication quirks) that are hard to anticipate from documentation alone.
- **Decision**: Create a Jupyter exploration notebook for each exchange BEFORE building the production connector. Notebook captures: symbol mapping, response structures, rate limit behavior, error codes, and parsing patterns.
- **Alternatives Considered**:
  1. Build connector directly from API documentation — rejected because API docs are often incomplete or inaccurate. Live API behavior is the source of truth.
  2. Build connector with heavy test mocking — rejected because mocked tests only test what you think the API does, not what it actually does.
- **Rationale**: Notebooks provide interactive exploration, visual output, and a permanent record of API behavior observations. Findings feed directly into connector implementation.
- **Consequences**: Notebook sequence: `01_kraken_exploration.ipynb`, `02_coinbase_exploration.ipynb`, etc. Each notebook has sections for symbol mapping, data parsing, rate limits, error handling, and async patterns.
- **References**: `notebooks/01_kraken_exploration.ipynb`, PROJECT_INSTRUCTIONS.md Section 5.3

### DEC-009: Operational docs in docs/ directory, not repo root
- **Date**: 2026-02-13
- **Status**: Accepted
- **Context**: Adding 5 new operational documents (lessons learned, session handoffs, decision log, Mathematica map, fixture README) to repo root would create clutter alongside the 6 existing root files.
- **Decision**: Operational documents live in `docs/`. Repo root keeps only project-level essentials (README, CHANGELOG, LICENSE, pyproject.toml, PROJECT_INSTRUCTIONS.md, CLAUDE_INSTRUCTIONS.md).
- **Alternatives Considered**:
  1. All in repo root — rejected because 11 markdown files in root is unwieldy.
  2. Nested in `src/` — rejected because these are project-level docs, not source code.
- **Rationale**: Clean separation between project essentials (root) and operational references (docs/).
- **Consequences**: PROJECT_INSTRUCTIONS.md Section 2 and 14 point to `docs/`. CLAUDE_INSTRUCTIONS.md Reference section includes `docs/`.
- **References**: PROJECT_INSTRUCTIONS.md Sections 2 and 14

### DEC-010: MATHEMATICA_MAP.md replaces inline Section 12 table
- **Date**: 2026-02-13
- **Status**: Accepted
- **Context**: PROJECT_INSTRUCTIONS.md Section 12 has a 10-row Mathematica function mapping table. The comprehensive version with sub-functions, status tracking, and behavioral notes needs much more space.
- **Decision**: `docs/MATHEMATICA_MAP.md` is the single source of truth for porting status. Section 12 of PROJECT_INSTRUCTIONS.md becomes a pointer to this file.
- **Alternatives Considered**:
  1. Expand Section 12 in place — rejected because it would make PROJECT_INSTRUCTIONS.md too long and the table would dominate the document.
  2. Keep both (inline summary + detailed doc) — rejected because Coding Rule 10.1 says single source of truth. Duplicate tables inevitably diverge.
- **Rationale**: Single source of truth. One place to check porting status, one place to update it.
- **Consequences**: When porting a function, update MATHEMATICA_MAP.md status. When checking what's been ported, search MATHEMATICA_MAP.md.
- **References**: Coding Rule 10.1, `docs/MATHEMATICA_MAP.md`

---


### DEC-013: Phase 1 fee model — hardcoded flat rates

- **Date**: 2026-02-14
- **Status**: Accepted
- **Context**: Kraken has 12 volume tiers, Coinbase has its own schedule. Building a full tiered lookup adds complexity.
- **Decision**: Use hardcoded flat rates from config.yaml for Phase 1. Kraken taker: 0.26%, Coinbase taker: 0.60%, Gemini taker: 0.40%.
- **Rationale**: Phase 1 is detection-only. Flat rates are sufficient for identifying opportunities. Accuracy can be improved in Phase 2 by reading the user's actual tier from authenticated API calls.
- **Consequences**: Detected returns may be slightly off for users on lower fee tiers. Conservative (we overestimate fees).

### DEC-014: Kelly Criterion parameters — industry defaults

- **Date**: 2026-02-14
- **Status**: Accepted
- **Context**: Mathematica code uses `probSuccess` and `kellyNumber` as parameters without hardcoding defaults.
- **Decision**: prob_success=0.95 (95% success rate), kelly_multiplier=0.25 (quarter Kelly). Configurable via function parameters.
- **Rationale**: Quarter Kelly is standard conservative practice in quantitative trading. 95% probability reflects the high success rate of detected arb opportunities from the Mathematica system's 10,000+ trade history.
- **Consequences**: Very conservative sizing — a $1000 bankroll with 0.25% edge yields ~$0.59 position. This is intentional; Kelly is for risk management, not profit maximization.

### DEC-015: Include withdrawal fees in Phase 1

- **Date**: 2026-02-14
- **Status**: Accepted
- **Context**: Mathematica code includes withdrawal fees in returnNet calculation. Question was whether to defer to Phase 3.
- **Decision**: Include withdrawal fees now using conservative estimates from exchange documentation.
- **Rationale**: Without withdrawal fees, returnNet would overstate profitability. A detected "profitable" opportunity that loses money to withdrawal fees is worse than no detection. Accurate net return is critical even for detection-only Phase 1.
- **Consequences**: Requires maintaining a withdrawal fee database (tests/fixtures/fee_schedules.json). Fees are dynamic on Kraken so estimates may drift. Will need refresh mechanism in Phase 2+.


### DEC-016: Build orchestration layer before Gemini connector

- **Date**: 2026-02-14
- **Status**: Accepted
- **Context**: The pure detection pipeline is complete (connectors → calculation → strategy). Next steps listed Gemini exploration first, then orchestration. However, Kraken + Coinbase already provide 2 exchanges — sufficient for Type-2 arbitrage detection.
- **Decision**: Build the orchestration layer (config loader, polling loop, wiring connectors to strategy, email notification) with 2 exchanges before adding Gemini as a third connector.
- **Alternatives Considered**:
  1. Gemini first, then orchestration — rejected because the third connector can't be tested in an end-to-end pipeline until orchestration exists. Building it first adds a connector that sits unused until the pipeline is wired up.
  2. Build both in parallel — rejected because orchestration may surface integration issues that affect connector design (e.g., error handling patterns, partial failure modes). Better to learn from 2 connectors before building the third.
- **Rationale**: Proves the end-to-end pipeline with real data. Surfaces integration bugs early — the kind that only appear when wiring real connectors to real strategy functions. Delivers a working Phase 1 system sooner (detection + email alerts with 2 exchanges). Makes Gemini a low-risk incremental add afterward — just plug in another connector to an already-proven pipeline.
- **Consequences**: SESSION_HANDOFFS next steps reordered. Gemini becomes priority 3-4 instead of priority 1. Phase 1 completion defined as: 2-exchange detection with email alerts, Gemini added incrementally.
- **References**: SESSION_HANDOFFS.md 2026-02-14 strategy layer entry, Coding Rule 7.1 (reliability over cleverness)


### DEC-017: EmailConfig owned by notification layer, not orchestration

- **Date**: 2026-02-15
- **Status**: Accepted
- **Context**: `notification/email.py` imported `EmailConfig` from `orchestration/config.py`, violating the Section 5.2 import rule `Notification → Domain/Core` (notification should not import from orchestration, the top layer).
- **Decision**: Move `EmailConfig` dataclass definition to `notification/email.py`. Orchestration imports it from there when building the config.
- **Alternatives Considered**:
  1. Move to `core/types.py` — rejected because EmailConfig is notification-specific, not a domain type about markets/prices/pairs.
  2. Have `send_alert` accept primitive parameters — rejected because it scatters 6 parameters across every call site and loses grouping.
  3. Create shared `config/types.py` — rejected as premature; only one type needs moving. Revisit when a second config type needs cross-layer sharing (Coding Rule 10.1).
- **Rationale**: Types belong in the layer that defines their contract. EmailConfig is consumed only by the notification layer. The orchestration layer creates and passes it, but doesn't need to own the definition. This follows the same principle as LL-053 (calculation types eventually moving to core).
- **Consequences**: `notification/email.py` now defines EmailConfig. `orchestration/config.py` imports it from notification. Import direction: orchestration → notification (allowed). No circular dependency.



### DEC-018: BaseAsyncConnector ABC design — shared retry, subclass parsing
- **Date**: 2026-02-15
- **Status**: Accepted
- **Context**: Code review identified the retry-with-backoff loop as duplicated across KrakenClient._request() and CoinbaseClient._fetch_product_book(). Both have identical constructor signatures, rate limiting, backoff sleep, and retry classification logic, but different response formats and error extraction.
- **Decision**: Extract a `BaseAsyncConnector` ABC in `connectors/connector_base.py` that provides shared constructor, venue property, and `_fetch_with_retry()` returning raw `httpx.Response`. Subclasses handle venue-specific JSON parsing and error extraction. The `ExchangeConnector` Protocol stays as the structural typing interface.
- **Alternatives Considered**:
  1. ABC with abstract hooks for `_is_retryable()` and `_parse_response()` — rejected because it forces artificial abstraction over fundamentally different response formats, and the hooks would be complex to accommodate Kraken's error-in-200 pattern.
  2. Standalone retry utility function (not a class) — rejected because the retry logic shares state with the connector (rate limiter, timeout, backoff policy, venue name for logging). Passing all these as parameters defeats the purpose.
  3. Keep duplication — rejected because Gemini connector will be the 3rd instance, and the retry loop is ~30 lines of identical logic per connector.
- **Rationale**: Approach A (return raw Response) deduplicates the actual repeated code (retry/rate-limit/backoff loop) without creating false abstractions. Each subclass retains full control over its response parsing. The ABC also unifies 429 retry handling — Kraken previously did not retry on 429, which was an oversight since Kraken can return 429 for rate limiting.
- **Consequences**: KrakenClient and CoinbaseClient inherit from BaseAsyncConnector. Constructor signature unchanged (same positional/keyword args). ExchangeConnector Protocol unaffected. Future Gemini connector inherits from BaseAsyncConnector and only needs to implement fetch_tickers().
- **References**: Coding Rule 10.1 (don't generalize until 2 real callers — now 2, soon 3), LL-052 (Coinbase per-pair requests)


### DEC-019: Type-1 and Type-3 arbitrage deferred to Phase 2+
- **Date**: 2026-02-16
- **Status**: Deferred
- **Context**: Code review noted absence of triangular (Type-1) and cross-pair (Type-3) arbitrage engines.
- **Decision**: Defer. The Mathematica system ran 10,000+ trades primarily on Type-2 arbitrage. Type-2 is validated and is the current focus. Type-1/3 can be added when Type-2 is fully live and profitable.
- **Rationale**: Type-2 alone provides sufficient opportunity with 3 exchanges × 8 pairs = 24 directional comparisons per scan cycle.
- **References**: PROJECT_INSTRUCTIONS.md ("Type-2 primary")

### DEC-020: Execution-feasibility gate deferred to Phase 3+
- **Date**: 2026-02-16
- **Status**: Deferred
- **Context**: Code review noted no slippage modeling, partial-fill risk assessment, or "unknown cost → block execution" gate.
- **Decision**: Defer. Phase 1 is detection/alerts only — no trades are executed. Execution gates will be implemented in Phase 3 (paper trading) and Phase 4 (live trading).
- **Rationale**: Adding execution complexity to a detection-only system provides no value and increases maintenance burden.
- **References**: PROJECT_INSTRUCTIONS.md Section 11 (Development Phases)

### DEC-021: Structured rejection telemetry via RejectionReason enum
- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: `find_trades_to_execute()` returned bare `None` for 4 different failure modes, making operator diagnosis impossible without parsing logs.
- **Decision**: Return `ArbOpportunity | RejectionReason` with 4 enum variants: INSUFFICIENT_VENUES, ALL_STALE, MISSING_FEES, BELOW_THRESHOLD.
- **Alternatives Considered**: (1) Logging-only — rejected because structured returns enable programmatic reaction. (2) Exception hierarchy — rejected because "no trade found" is an expected outcome, not an error. (3) Result wrapper dataclass — over-engineered for 4 boolean outcomes.
- **Consequences**: Callers use `isinstance(result, RejectionReason)` to distinguish. Existing tests updated from `is None` checks to enum comparisons.

## Document History

| Date | Entry | Description |
|------|-------|-------------|
| 2026-02-13 | DEC-001 through DEC-010 | Initial creation with decisions extracted from project history |
| 2026-02-14 | DEC-011 | Raw httpx for Coinbase connector (partially supersedes DEC-005) |
| 2026-02-14 | DEC-012 | Mathematica as reference not gospel — philosophical shift |
| 2026-02-14 | Added DEC-013 (flat fee model), DEC-014 (Kelly defaults), DEC-015 (withdrawal fees in Phase 1) |
| 2026-02-14 | DEC-016 | Orchestration before Gemini connector (strategic pivot) |
| 2026-02-15 | DEC-017 | EmailConfig moved from orchestration to notification layer |
| 2026-02-15 | DEC-018 | BaseAsyncConnector ABC design — shared retry, subclass parsing |


### DEC-011: Use raw httpx (not SDK) for Coinbase connector
- **Date**: 2026-02-14
- **Status**: Accepted (partially supersedes DEC-005 for Coinbase)
- **Context**: DEC-005 selected `coinbase-advanced-py` SDK for Coinbase. Notebook exploration (02_coinbase_exploration.ipynb) revealed the SDK is synchronous-only (uses `requests`), violating Coding Rule 2.3 (all external I/O must be async/await).
- **Decision**: Use raw `httpx.AsyncClient` for the Coinbase production connector, consistent with the Kraken connector pattern. The SDK remains useful for interactive exploration in notebooks.
- **Alternatives Considered**:
  1. Wrap SDK in `asyncio.to_thread()` — rejected because it adds thread pool overhead, loses header control (needed for cache-control), and creates an inconsistent pattern vs. Kraken connector.
  2. Use SDK as-is (synchronous) — rejected because it violates Coding Rule 2.3 and would block the event loop.
- **Rationale**: httpx provides async-native requests, full header control, and a consistent pattern across all connectors. The response structure is identical between SDK and raw httpx (same JSON shape, same keys), so there is zero loss of functionality.
- **Consequences**: Coinbase connector mirrors Kraken connector structure: `client.py` uses `httpx.AsyncClient`, `parser.py` has pure parsing functions, `symbols.py` has the symbol map. All three connectors now use custom httpx per DEC-018. DEC-005 is fully superseded.
- **References**: `notebooks/02_coinbase_exploration.ipynb` Section 5, LL-052, Coding Rule 2.3

### DEC-012: Mathematica as reference, not gospel
- **Date**: 2026-02-14
- **Status**: Accepted
- **Context**: The project was originally framed as a "port" of the Mathematica system to Python. While the Mathematica system is proven (10,000+ trades) and provides invaluable reference patterns, treating it as gospel constrains the Python system unnecessarily. Mathematica's patterns were shaped by Mathematica's language constraints (lack of typed containers, expression-based evaluation, mutable associations), and Python has different strengths.
- **Decision**: The Mathematica system is a validated reference and guide, not a specification. Where Python idioms, modern libraries, or better algorithms exist, prefer those. Where Mathematica's approach is clunky or constrained by its language, redesign freely. Where Mathematica's approach is elegant and proven, adopt it. Claude should proactively suggest improvements rather than defaulting to literal porting.
- **Alternatives Considered**:
  1. Continue literal porting — rejected because it imports Mathematica's language-specific limitations into Python unnecessarily.
  2. Ignore Mathematica entirely and design from scratch — rejected because 10,000+ successful trades represent hard-won domain knowledge that shouldn't be discarded.
- **Rationale**: The value of the Mathematica system is in its *domain logic* (fee models, return calculations, trade selection, limiting reactant pattern), not its *implementation patterns*. Python can preserve the domain logic while using better implementation patterns. Examples already exist: DEC-003 (boundary validation vs scattered MissingCheck) and DEC-011 (async httpx vs sync SDK) are cases where we already improved over Mathematica's approach.
- **Consequences**: MATHEMATICA_MAP.md gains a `🔧 Improved` status for functions where the Python version intentionally diverges. Pre-implementation verification now includes "Improvements over Mathematica approach considered." Calculation Match metric allows documented divergence.
- **References**: CLAUDE_INSTRUCTIONS.md "Relationship to Mathematica" section, DEC-003, DEC-011

### DEC-019: Unique module name rule and document authority hierarchy
- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: Duplicate module basenames reduced navigation clarity and three instruction documents drifted out of sync.
- **Decision**:
  - Add Rule 10.8: module names must be unique across `src/uscryptoarb/` except connector sub-package internal `client.py`/`parser.py`/`symbols.py`.
  - Add Rule 10.9: second-instance patterns must be flagged in SESSION_HANDOFFS as Refactor Candidates and addressed next session or deferred with rationale.
  - Define documentation authority hierarchy: `PROJECT_INSTRUCTIONS.md` -> `CLAUDE_INSTRUCTIONS.md` -> Claude.ai UI copy.
- **Alternatives considered**:
  - Rename connector internal `client.py`/`parser.py`/`symbols.py` files (rejected: package namespace already disambiguates and this pattern is intentional).
  - Keep short-form `CLAUDE_INSTRUCTIONS.md` (rejected: excessive context loss and drift risk).
  - Execute as multiple sessions (rejected: increases churn and transition risk during path rename sweep).
- **Rationale**: Unique filenames improve code navigation and AI retrieval quality; explicit hierarchy prevents instruction drift.
- **Consequences**: Five source modules and related tests renamed; checklists and operational docs updated; manual UI sync remains required by project owner.
- **References**: LL-065, LL-066, Coding Rules 10.8 and 10.9.


### DEC-022: Kraken taker fee corrected to 0.40%

- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: Fee audit discovered config.yaml used 0.26% for Kraken, which doesn't match any current Kraken Pro tier. The lowest-tier taker rate is 0.40% ($0-$10K monthly volume). Multiple sources (kraken.com, CoinBureau Jan 2026, CryptoSlate Jan 2026) confirm this rate.
- **Decision**: Update Kraken buy/sell fee to 0.0040 (0.40%) per DEC-013 (most conservative tier).
- **Consequences**: Kraken trading costs increase ~54%. Fewer Kraken-involved opportunities pass threshold. Remaining opportunities are more reliable.
- **References**: DEC-013, fee audit 2026-02-16

### DEC-023: Coinbase taker fee updated to 1.20% (Intro 1 tier)

- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: Fee audit discovered Coinbase restructured fee tiers, introducing "Intro 1" (0.60% maker / 1.20% taker for <$1K 30-day volume) and "Intro 2" (0.35% / 0.75% for ≥$1K). The old base tier of 0.40% maker / 0.60% taker has been replaced. Alternative was 0.40% at the Advanced 1 tier ($10K+ monthly volume), which is more realistic for active trading.
- **Decision**: Use 1.20% taker (Intro 1) per strict interpretation of DEC-013.
- **Rationale**: Strict DEC-013 compliance. If we later demonstrate consistent volume exceeding $10K/month, this can be revisited with a new DEC entry.
- **Consequences**: Combined Coinbase buy+sell cost is ~2.40%. Very few cross-exchange spreads will exceed this plus the 0.55% threshold. Coinbase effectively becomes a high-cost exchange in our model. This is conservative — any opportunity that passes is highly likely to be real.
- **References**: DEC-013, fee audit 2026-02-16

### DEC-024: OKX connector uses batch ticker endpoint (like Kraken)
- **Date**: 2026-02-16
- **Status**: Accepted
- **Context**: OKX offers both per-pair ticker (`/api/v5/market/ticker?instId=BTC-USD`) and batch ticker (`/api/v5/market/tickers?instType=SPOT`). Notebook testing showed batch is 13.2x faster (207ms vs 2738ms for 7 pairs).
- **Decision**: Use batch endpoint. Single API call per scan cycle, client-side filtering to 7 target pairs.
- **Alternatives Considered**: Per-pair requests (slower, unnecessary since batch endpoint exists and provides all TopOfBook fields).
- **Rationale**: Batch approach matches Kraken pattern, minimizes API calls, well under rate limits.
- **Consequences**: OKX fetch_tickers() overrides the abstract method directly (like KrakenClient) instead of using _fetch_tickers_per_pair() template (used by Coinbase/Gemini).
- **References**: notebooks/05_okx_exploration.ipynb Section 4, DEC-018


### DEC-025: Keep assert statements in returns.py as programmer invariants
- **Date**: 2026-02-17
- **Decision**: Retain `assert` (not `if/raise`) in returns.py for invariant checks.
- **Context**: Two code reviews flagged that `assert` is stripped under `-O`. These assertions were consciously added in the Consolidated Refactor session with tests asserting on `AssertionError`. Changing to `if/raise ValueError` would break those tests.
- **Rationale**: Nobody runs production Python with `-O`. These are programmer invariants, not input validation. Boundary validation happens upstream.
- **Risk**: If someone runs with `-O`, invariants are silently skipped. Mitigated by: (a) documentation, (b) CI never uses `-O`.
- **Revisit when**: Phase 3+ execution layer, or if any CI/deployment uses `-O`.

### DEC-026: Defer property-based tests (Hypothesis) to Phase 2+
- **Date**: 2026-02-17
- **Decision**: Do not add Hypothesis tests now despite PROJECT_INSTRUCTIONS Section 8.1 listing them.
- **Rationale**: No existing Hypothesis infrastructure. ~2h to add. Good candidates: return_net <= return_grs <= return_raw invariant, fee symmetry, TopOfBook field ranges. Better ROI when WebSocket streams introduce sub-millisecond update rates in Phase 2.
- **Revisit when**: Phase 2 (WebSocket) or when a calculation bug is found that unit tests missed.

### DEC-027: Defer pytest-asyncio migration
- **Date**: 2026-02-17
- **Decision**: Keep `asyncio.run()` pattern in ~75+ async test functions.
- **Rationale**: Large mechanical change. Risk of subtle event loop differences between pytest-asyncio modes (auto vs strict). Current pattern works. Better as a dedicated session.
- **Revisit when**: Adding WebSocket tests (Phase 2) where async test lifecycle matters more.

### DEC-028: Defer circuit breaker pattern for venue failures
- **Date**: 2026-02-17
- **Decision**: Do not add circuit breaker for persistent venue failures.
- **Rationale**: Phase 1 is detection-only with human oversight. Current behavior: log warning, skip venue, continue. Circuit breaker adds complexity for a scenario that hasn't been observed in production.
- **Revisit when**: Phase 2 (WebSocket) or when operational patterns show repeated venue failures.

### DEC-029: Defer parallel per-pair fetching within connectors
- **Date**: 2026-02-17
- **Decision**: Keep sequential per-pair fetching in _fetch_tickers_per_pair().
- **Rationale**: Would reduce latency for Coinbase/Gemini/Bitstamp from ~1.2s to ~300ms. But adds concurrency complexity (rate limiter interaction, partial failure ordering). Current sequential approach is simple and correct.
- **Revisit when**: Phase 2 (WebSocket) when latency is critical, or when profiling shows fetch time as bottleneck.

### DEC-030: Defer now_ms() dependency injection
- **Date**: 2026-02-17
- **Decision**: Keep _patch_now_ms decorator approach for test determinism.
- **Rationale**: Clean DI (clock parameter) would touch many files. The patch decorator works with 4 sites currently. LL-067 documents the fragility.
- **Revisit when**: A 6th patch site appears, or Phase 2 needs testable timestamp handling for WebSocket streams.

### DEC-031: Defer ScannerConfig splitting into sub-configs
- **Date**: 2026-02-17
- **Decision**: Keep ScannerConfig as a single configuration object.
- **Rationale**: Current structure works for Phase 1. The `replace()` pattern handles test overrides. Split when Phase 3/4 adds execution config, bankroll config, etc.
- **Revisit when**: Phase 3 (Paper Trading) when execution-specific config is needed.

### DEC-032: Defer rounding to exchange TradingAccuracy in fee calculations
- **Date**: 2026-02-17
- **Decision**: TradingAccuracy data is loaded but unused in current fee calcs.
- **Rationale**: calc_buy_leg/calc_sell_leg operate on exact Decimal arithmetic. Rounding to exchange precision only matters for actual order placement (Phase 3+). Detection accuracy is unaffected.
- **Revisit when**: Phase 3 (Paper Trading) when calc_position_size() feeds into order placement.

### DEC-033: Push connector defaults to class-level ClassVar attributes
- **Date**: 2026-02-17
- **Decision**: Replaced 5 identical __init__ methods with ClassVar declarations (VENUE_NAME, DEFAULT_SYMBOLS) on each subclass. BaseAsyncConnector.__init__ reads these. Also removed the cast() union in create_connectors() which was flagged as a refactor candidate 3 times across sessions.
- **Rationale**: 5 × ~15 lines of identical boilerplate. DEC-018 established BaseAsyncConnector ABC but left the __init__ duplication. Rule 10.5 mandates refactoring when same logic exists in 2+ places. The cast union grew with every new connector — 5 types after OKX.
- **Alternatives considered**: (a) Keep status quo — each connector provides defaults in its own __init__. Rejected: pure boilerplate. (b) Registry-based defaults — too indirect. (c) __init_subclass__ — over-engineered for this use case.
