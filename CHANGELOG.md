# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub Actions CI workflow with Ruff, mypy, and pytest
- `validation/guards.py`: Runtime validation guards (`is_missing`, `require_present`, `require_positive`, `require_non_negative`)
- Unit tests for validation module (30+ test cases)
- mypy strict configuration in pyproject.toml
- `py.typed` marker for PEP 561 compliance

### Changed
- Updated PROJECT_INSTRUCTIONS.md to document validation guards pattern

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
