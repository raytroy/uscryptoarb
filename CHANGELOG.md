# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `docs/LESSONS_LEARNED.md`: Mistake prevention database with seed entries from project history
- `docs/SESSION_HANDOFFS.md`: Append-only session continuity log for multi-chat workflows
- `docs/DECISION_LOG.md`: Architectural decision records with rationale (10 seed entries)
- `docs/MATHEMATICA_MAP.md`: Comprehensive Mathematica→Python porting tracker (~58 functions)
- `tests/fixtures/README.md`: Test fixture conventions and provenance documentation
- PROJECT_INSTRUCTIONS.md Section 14: Operational Documents reference and workflow integration
- GitHub Actions CI workflow with Ruff, mypy, and pytest
- `validation/guards.py`: Runtime validation guards (`is_missing`, `require_present`, `require_positive`, `require_non_negative`)
- Unit tests for validation module (30+ test cases)
- mypy strict configuration in pyproject.toml
- `py.typed` marker for PEP 561 compliance
- `connectors/base.py`: `ExchangeConnector` Protocol defining the interface for all exchange connectors
- `connectors/kraken/`: First exchange connector (Kraken)
  - `symbols.py`: Verified symbol mapping for all 8 target pairs (BTC/USD, BTC/USDC, LTC/USD, LTC/USDC, LTC/BTC, SOL/USD, SOL/USDC, SOL/BTC)
  - `parser.py`: Pure parsing functions for ticker and orderbook responses → TopOfBook
  - `client.py`: Async httpx-based client with rate limiting, retry, and startup symbol validation
- `http/rate_limiter.py`: Async rate limiter for respecting exchange API limits
- `venues/symbols.py`: Added `to_canonical()` reverse lookup to SymbolTranslator
- `fixtures/`: Kraken API response fixtures from live exploration notebook
- `tests/conftest.py`: Shared pytest fixtures for API response data
- `httpx>=0.27` added as runtime dependency

### Changed
- PROJECT_INSTRUCTIONS.md: Added operational docs to Source Documents (Section 2), Workflow (7.2), Propagation Rule (7.3), Deliverable Format (7.4), PR Checklist (10.3), Pre-Implementation and Propagation Checklists (13); replaced Section 12 inline table with pointer to MATHEMATICA_MAP.md
- CLAUDE_INSTRUCTIONS.md: Added doc searches to workflow, pre-implementation verification, deliverable format, and reference section
- README.md: Added Documentation section with links to all project docs
- Documented "Data Trust Boundaries" pattern (validate at boundaries, trust downstream) across PROJECT_INSTRUCTIONS.md (Section 6.2), CLAUDE_INSTRUCTIONS.md, and `validation/guards.py` module docstring
- `pyproject.toml`: Added httpx to runtime dependencies

## [0.0.1] - 2025-01-04

### Added
- Initial project structure
- `misc/decimals.py`: `to_decimal()`, `floor_to_step()`, `ceil_to_step()`
- `markets/pairs.py`: `CanonicalPair`, `parse_pair()`
- `venues/registry.py`: `VenueInfo`, `ohio_eligible()`
- `venues/symbols.py`: `SymbolTranslator`
- `config/app_config.py`: `AppConfig`, `validate_config()`
- `marketdata/topofbook.py`: `TopOfBook`, `validate_tob()`, `tob_from_raw()`
- Basic test suite for registry and config validation
- PROJECT_INSTRUCTIONS.md with comprehensive coding standards

[Unreleased]: https://github.com/raytroy/uscryptoarb/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/raytroy/uscryptoarb/releases/tag/v0.0.1
