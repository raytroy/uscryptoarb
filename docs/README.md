# Test Fixtures

> **Purpose**: Document what each test fixture represents, where reference values came from, and how to add new fixtures.
> **Authoritative for**: Fixture provenance and conventions. Every fixture file should be documented here.

---

## Conventions

### File Naming

```
<exchange>_<data_type>_<scenario>.json
```

Examples:
- `kraken_ticker_btcusd_normal.json` — Normal Kraken ticker response for BTC/USD
- `kraken_ticker_btcusd_crossed.json` — Crossed book (bid >= ask) for validation testing
- `coinbase_ticker_btcusd_missing_field.json` — Response with missing required field
- `mathematica_returns_btcusd_20240115.json` — Known-good return calculations from Mathematica

### Categories

| Directory | Purpose | Provenance |
|-----------|---------|------------|
| `api_responses/` | Raw API responses captured from live exchanges | Captured during notebook exploration |
| `mathematica_verified/` | Expected outputs verified against Mathematica system | Computed by Mathematica, exported as JSON |
| `edge_cases/` | Intentionally malformed or boundary-condition data | Hand-constructed for testing |
| `snapshots/` | Complete market state snapshots (multi-exchange, multi-pair) | Captured or synthetic |

### Provenance Requirements

Every fixture file MUST have an entry in this README documenting:

1. **What it contains** — data format and meaning
2. **Where it came from** — live capture, Mathematica export, or hand-constructed
3. **When it was captured** — date, so we know if it reflects current API format
4. **What tests use it** — list of test files that depend on this fixture

---

## Fixture Inventory

_(Add entries as fixtures are created)_

### Template

```
### <filename>
- **Contains**: <description of data>
- **Source**: [Live capture from <exchange> | Mathematica export | Hand-constructed]
- **Date captured**: YYYY-MM-DD
- **Used by**: `tests/unit/test_<module>/test_<file>.py`
- **Notes**: <any special considerations>
```

---

## How to Add a New Fixture

1. **Capture or construct** the data
2. **Save** to the appropriate subdirectory with conventional naming
3. **Add an entry** to this README with full provenance
4. **Reference** in your test using `conftest.py` fixture loading:

```python
# tests/conftest.py
import json
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

def load_fixture(name: str) -> dict:
    """Load a JSON fixture file by name."""
    path = FIXTURES_DIR / name
    return json.loads(path.read_text())
```

### For Mathematica-Verified Fixtures

When porting a calculation function:

1. Run the Mathematica function with known inputs
2. Export inputs AND expected outputs as JSON
3. Save to `mathematica_verified/`
4. Write Python test that loads fixture and asserts output matches

```python
def test_calc_return_matches_mathematica():
    fixture = load_fixture("mathematica_verified/return_calc_cases.json")
    for case in fixture["cases"]:
        result = calc_return(
            end=Decimal(case["end"]),
            start=Decimal(case["start"]),
        )
        expected = Decimal(case["expected"])
        assert result == expected, f"Mismatch for {case['label']}"
```

This ensures the Python port produces identical results to the proven Mathematica system.

---

## Document History

| Date | Changes |
|------|---------|
| 2026-02-13 | Initial creation with conventions and templates |
