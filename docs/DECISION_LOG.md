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
- **Status**: Accepted
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
- **Status**: Accepted
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
- **References**: PROJECT_INSTRUCTIONS.md Section 3, `venues/symbols.py`

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

## Document History

| Date | Entry | Description |
|------|-------|-------------|
| 2026-02-13 | DEC-001 through DEC-010 | Initial creation with decisions extracted from project history |
