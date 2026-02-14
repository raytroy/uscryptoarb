# Mathematica → Python Function Map

> **Purpose**: Single source of truth for porting status. Tracks every Mathematica function, its Python equivalent, implementation status, and behavioral notes.
> **Authoritative for**: What has been ported, what hasn't, and where the Python behavior intentionally differs from Mathematica.
> **Replaces**: The inline table in PROJECT_INSTRUCTIONS.md Section 12 (which now points here).

---

## How to Use This File

**Before porting a function**: Check status here. Read behavioral notes and dependencies.
**After porting a function**: Update status, add Python path, note any behavioral differences.
**During review**: Verify the Python implementation matches the Mathematica semantics documented here.

### Status Key

| Status | Meaning |
|--------|---------|
| ✅ Ported | Implemented, tested, in production code |
| 🔄 In Progress | Implementation started, not yet complete |
| 📋 Planned | Identified for next phase, not started |
| ⏳ Deferred | Not needed until later phase |
| ❌ Not Porting | Intentionally not porting (with reason) |
| 🔧 Improved | Functionality exists but with intentionally better approach than Mathematica |

---

## Pipeline Overview

The Mathematica system executes in this order:

```
Databases (fees, withdrawal, accuracy)
    → BidAskData collection (per exchange, per pair)
        → TrimExchangesToCalc (filter valid data)
            → ArbOppAll (calculate all arbitrage opportunities)
                → ArbReturns (sort/rank by return)
                    → SelectTradeToExecute (pick best trade)
                        → GetInterestedTradeOrderBooks (get depth)
                            → CalcArbAmount (size the trade)
                                → ExecuteTradesL3 (place orders)
                                    → SaveTradeData (log results)
```

---

## 1. Core Data Structures

| Mathematica | Python | Module | Status | Notes |
|-------------|--------|--------|--------|-------|
| `TradingFeesDataStructure[]` | `TradingFeeRate` | `calculation/types.py` | ✅ Ported | Per-venue buy/sell fee rate with pct_fee and flat_fee. Flat fee currently 0 for all exchanges (Phase 1). |
| `WithdrawalFeeDataStructure[]` | `WithdrawalFee` | `calculation/types.py` | ✅ Ported | Per-venue, per-currency withdrawal fee with flat_fee and pct_fee. |
| `TradingAccuracyDataStructure[]` | `TradingAccuracy` | `calculation/types.py` | ✅ Ported | Per-venue, per-pair precision constraints (price_decimals, lot_decimals, min/max order size, tick/lot step). |
| `OrderbookEachOrderDataStructure[]` | `OrderBookEntry` | `core/types.py` | 📋 Planned | Association with: price, volume. Used for individual orderbook levels. |
| `OrderbookEachOrderDataStructureInverse[]` | — | — | 🔀 Redesigned | Handles inverse pairs (e.g., USD/BTC → BTC/USD). In Python, handled by `market_base_convert()` |
| `ResponseDataStructure[]` | — | `connectors/*/parser.py` | 🔀 Redesigned | Generic JSON response parser. In Python, each connector has its own typed parser. |
| `missingArbCalcStructure` | — | — | 🔀 Redesigned | Sentinel "empty" ArbCalc result. In Python, use `Optional` return or raise `ValueError`. |
| `missingTradesToExec` | — | — | 🔀 Redesigned | Sentinel "no trades" result. In Python, return empty list or `None`. |

---

## 2. Database Headers & Initialization

| Mathematica | Python | Module | Status | Notes |
|-------------|--------|--------|--------|-------|
| `withdrawalHeader` | — | `core/types.py` | 🔀 Redesigned | Defines column names. In Python, dataclass field names serve this purpose. |
| `tradingFeesHeader` | — | `core/types.py` | 🔀 Redesigned | Same — replaced by dataclass fields. |
| `tradingAccuracyHeader` | — | `core/types.py` | 🔀 Redesigned | Same — replaced by dataclass fields. |
| `exchangeTradingFeesDatabase` | `trading_fees_db` | Passed as param | 📋 Planned | `List[TradingFees]` — loaded from config, passed to calculation functions |
| `withdrawalDatabase` | `withdrawal_db` | Passed as param | 📋 Planned | `List[WithdrawalFee]` — loaded from config, passed to calculation functions |
| `tradingInfoDatabase` | `trading_info_db` | Passed as param | 📋 Planned | `List[TradingAccuracy]` — loaded from config, passed to calculation functions |

---

## 3. Validation & Missing Data

| Mathematica | Python | Module | Status | Notes |
|-------------|--------|--------|--------|-------|
| `MissingCheck[]` | `is_missing()` | `validation/guards.py` | ✅ Ported | **Behavioral difference**: Mathematica checks `MissingQ[]` on any expression. Python version checks for None, empty containers, NaN, Infinity. Mathematica's `Missing[]` propagates; Python's boundary pattern rejects immediately. See DEC-003. |
| — | `require_present()` | `validation/guards.py` | ✅ Ported | No Mathematica equivalent — new pattern for boundary enforcement. |
| — | `require_positive()` | `validation/guards.py` | ✅ Ported | No Mathematica equivalent — new pattern for prices/fees. |
| — | `require_non_negative()` | `validation/guards.py` | ✅ Ported | No Mathematica equivalent — new pattern for balances. |

---

## 4. Symbol Translation & Pair Handling

| Mathematica | Python | Module | Status | Notes |
|-------------|--------|--------|--------|-------|
| `PairTranslator[]` | `pair_translator()` | `core/pair_utils.py` | 📋 Planned | Converts canonical pair to exchange format. Mathematica uses string manipulation with flags (NoSpace, UnderScore, Hyphen). Python version should use SymbolTranslator lookup. |
| `PairTranslatorReverse[]` | `pair_translator_reverse()` | `core/pair_utils.py` | 📋 Planned | Reverse of PairTranslator — exchange format → canonical. Mathematica handles both string and non-string pair inputs. |
| `MarketBaseConvert[]` | `market_base_convert()` | `core/pair_utils.py` | 📋 Planned | Splits canonical pair into market and base currencies. E.g., `BTC/USD` → market=`BTC`, base=`USD`. **Note**: In Mathematica, handles both "forward" and "inverse" pairs for orderbook processing. |
| — | `CanonicalPair` | `markets/pairs.py` | ✅ Ported | Frozen dataclass with `base` and `quote` fields. `parse_pair()` factory. |
| — | `SymbolTranslator` | `venues/symbols.py` | ✅ Ported | Maps canonical pairs to venue-specific symbols. More structured than Mathematica's string manipulation approach. |

---

## 5. Exchange Connectivity (Per-Exchange)

| Mathematica | Python | Module | Status | Notes |
|-------------|--------|--------|--------|-------|
| `BidAskData[]` (Kraken) | `fetch_ticker()` | `connectors/kraken/client.py` | ✅ Ported | Async httpx client with rate limiting. Produces TopOfBook via tob_from_raw(). |
| `BidAskData[]` (Coinbase) | `fetch_tickers()` | `connectors/coinbase/` | ✅ Ported | Async httpx client. Per-pair requests via `/market/product_book` (no public batch — LL-052). Parser converts to TopOfBook via `tob_from_raw()`. |
| `BidAskData[]` (Gemini) | `fetch_ticker()` | `connectors/gemini/` | 📋 Planned | Fetches ticker from Gemini. Notebook not yet created. |
| `OrderBookPerExchange[]` | `fetch_orderbook()` | `connectors/*/orderbook.py` | ⏳ Deferred | Full orderbook depth. Phase 1 uses top-of-book only. Needed for trade sizing in Phase 3+. |
| `GetTradingBalances[]` | `fetch_balances()` | `connectors/*/balances.py` | ⏳ Deferred | Account balance retrieval. Requires authenticated API. Phase 3+. |
| `CheckExisitngOrders[]` | `check_open_orders()` | `connectors/*/orders.py` | ⏳ Deferred | Check for open orders before placing new ones. Phase 4. |

### Orderbook Parsing (Sub-functions)

| Mathematica | Python | Module | Status | Notes |
|-------------|--------|--------|--------|-------|
| `OrderBookParser[]` | `parse_orderbook()` | `connectors/*/parser.py` | 📋 Planned | Generic orderbook parser. In Mathematica, handles multiple response formats. |
| `OrderbookEachOrderDataStructure[]` | — | `connectors/*/parser.py` | 🔀 Redesigned | Structures individual order entries. In Python, each connector parses natively into canonical types. |
| `OrderbookEachOrderDataStructureInverse[]` | — | `connectors/*/parser.py` | 🔀 Redesigned | Handles inverse orderbook entries. Python handles this via `market_base_convert()`. |

---

## 6. Data Filtering & Preparation

| Mathematica | Python | Module | Status | Notes |
|-------------|--------|--------|--------|-------|
| `TrimExchangesToCalc[]` | `filter_valid_exchanges()` | `strategy/scanner.py` | 🔧 Improved | Combined L1/L2/L3 into single function with optional staleness parameter. Filters stale data; skips filtering when no staleness config provided. |
| `TrimExchangesToCalcL2[]` | — | — | 🔀 Redesigned | L2 variant with additional filtering. In Python, combined into single function with optional parameters. |
| `TrimExchangesToCalcL3[]` | — | — | 🔀 Redesigned | L3 variant. Same — combined into single function. |
| `NonDupExchangesWithMoney[]` | `filter_funded_exchanges()` | `strategy/scanner.py` | ⏳ Deferred | Filters to exchanges where user has balance. Requires Phase 3+ (balance checking). |

---

## 7. Fee Retrieval & Calculation

| Mathematica | Python | Module | Status | Notes |
|-------------|--------|--------|--------|-------|
| `GetTradingFees[]` | `TradingFeeRate` dataclass | `calculation/types.py` | ✅ Ported | Per-venue buy/sell trading fee model for calculation context. |
| `GetWithdrawalFees[]` | `WithdrawalFee` dataclass | `calculation/types.py` | ✅ Ported | Per-venue, per-currency withdrawal fee model. |
| `GetAccuracyData[]` | `TradingAccuracy` dataclass | `calculation/types.py` | ✅ Ported | Precision/min/max model for exchange-compliant sizing. |

### Fee Application (Buy/Sell Sides)

| Mathematica | Python | Module | Status | Notes |
|-------------|--------|--------|--------|-------|
| Buy side: `MktCurrAmt → BaseCurrAmt → MktCurrAmtGrs` | `calc_buy_leg()` | `calculation/fees.py` | ✅ Ported | Buy leg with base cost, trading fee, and withdrawal fee breakdown. |
| Sell side: `MktCurrAmt → MktCurrAmtGrs` | `calc_sell_leg()` | `calculation/fees.py` | ✅ Ported | Sell leg with proceeds, trading fee, and withdrawal fee breakdown. |
| Net: `MktCurrAmtGrs → MktCurrAmtNet` | `total_buy_cost()` / `net_sell_proceeds()` | `calculation/fees.py` | ✅ Ported | Net amount helpers include trading and withdrawal fee effects. |
| `LiquiPairsInfoParserL2[]` | — | `connectors/*/parser.py` | 📋 Planned | Parses exchange-specific trading info (min sizes, precision). In Python, each connector normalizes to `TradingAccuracy`. |

---

## 8. Arbitrage Calculation

| Mathematica | Python | Module | Status | Notes |
|-------------|--------|--------|--------|-------|
| `ArbOppAll[]` | `calc_all_opportunities()` | `calculation/arb_calc.py` | ✅ Ported | Generates all pairwise directional opportunities for a pair. |
| `ArbCalcFinal[]` | `calc_arb_opportunity()` | `calculation/arb_calc.py` | ✅ Ported | Full directed opportunity calc with raw/gross/net returns and profits. |
| `ReturnCalc[]` | `calc_return_raw()` / `calc_return_grs()` / `calc_return_net()` | `calculation/returns.py` | ✅ Ported | Split into explicit raw/gross/net return functions. |
| `ReturnCalcAll[]` | `calc_return_all()` | `calculation/returns.py` | 📋 Planned | Computes returnRaw, returnGrs, returnNet, and profit metrics in one pass. Takes buy/sell prices and fee-adjusted amounts. |
| `ArbSort[]` / `ArbReturns[]` | `sort_opportunities()` / `filter_profitable()` | `calculation/arb_calc.py` | ✅ Ported | Sorting + threshold filtering helpers. |


---

## 9. Trade Sizing

| Mathematica | Python | Module | Status | Notes |
|-------------|--------|--------|--------|-------|
| `CalcKellyAmount[]` | `calc_kelly_amount()` | `calculation/sizing.py` | ✅ Ported | Fractional Kelly position sizing with cap and edge clamp. |
| `GetInterestedTradeOrderBooks[]` | `get_trade_orderbooks()` | `execution/pre_trade.py` | ⏳ Deferred | Fetches full orderbook for the specific trade being considered. Uses `pctOfMarket` (default 0.85) to determine depth needed. Phase 3+. |
| `GetInterestedTradeOrderBooksL3[]` | — | — | 🔀 Redesigned | L3 variant with direction/length params. Combined into single function. |
| `Kelly[]` | `calc_kelly_fraction()` | `calculation/sizing.py` | ✅ Ported | Pure Kelly fraction helper (edge × probability). |
| `TradeToInvestigateBalances[]` | `get_trade_balances()` | `execution/pre_trade.py` | ⏳ Deferred | Gets current balances for the exchanges involved in a specific trade. Phase 3+. |

---

## 10. Trade Selection & Execution

| Mathematica | Python | Module | Status | Notes |
|-------------|--------|--------|--------|-------|
| `TradesToExecute[]` | `find_trades_to_execute()` | `strategy/scanner.py` | ✅ Ported | Top-level pipeline: filter_valid_exchanges → calc_all_opportunities → sort → select_trade. Returns best ArbOpportunity or None. |
| `SelectTradeToExecute[]` | `select_trade()` | `strategy/selection.py` | 🔧 Improved | Picks best trade by return_net (not sellMarket size). Uses > not >= for threshold. Checks only return_net (implies return_grs and return_raw). |
| `ExecuteTradesL2[]` | `execute_trade_l2()` | `execution/orders.py` | ⏳ Deferred | Mid-level execution: checks threshold, delegates to L3 if passes. Phase 4. |
| `ExecuteTradesL3[]` | `execute_trades()` | `execution/orders.py` | ⏳ Deferred | Full execution: check existing orders → get orderbooks → get balances → calc amount → execute. Phase 4. |
| `RunFinal[]` | `run_scan_cycle()` | `__main__.py` | 📋 Planned | Top-level orchestration: TradesToExecute → threshold check → ExecuteTradesL3. Phase 1 will detect + alert only. |

---

## 11. Trade Execution Engine

| Mathematica | Python | Module | Status | Notes |
|-------------|--------|--------|--------|-------|
| `TradeEngine[]` | `trade_engine()` | `execution/engine.py` | ⏳ Deferred | Wraps TradeEngineL2 + SaveTradeData. Phase 4. |
| `TradeEngineL2[]` | `trade_engine_l2()` | `execution/engine.py` | ⏳ Deferred | Places actual orders on exchanges. Phase 4. |
| `PlaceTrade[]` | `place_order()` | `connectors/*/orders.py` | ⏳ Deferred | Per-exchange order placement. Phase 4. |

---

## 12. Data Persistence & Logging

| Mathematica | Python | Module | Status | Notes |
|-------------|--------|--------|--------|-------|
| `SaveTradeData[]` | `save_trade_data()` | `execution/logging.py` | ⏳ Deferred | Saves trade data + response to file. Mathematica uses `.m` files. Python will use JSON or structured logging. Phase 4. |
| `SendEmail[]` | `send_alert()` | `notification/email.py` | 📋 Planned | Email notification for detected opportunities. Phase 1. |

---

## 13. Utility / Helper Functions

| Mathematica | Python | Module | Status | Notes |
|-------------|--------|--------|--------|-------|
| `to_decimal()` | `to_decimal()` | `core/decimal_utils.py` | ✅ Ported | No direct Mathematica equivalent (Mathematica uses arbitrary precision natively). Rejects floats. |
| `floor_to_step()` | `floor_to_step()` | `core/decimal_utils.py` | ✅ Ported | Floor to exchange step size. |
| `ceil_to_step()` | `ceil_to_step()` | `core/decimal_utils.py` | ✅ Ported | Ceil to exchange step size. |
| `parse_pair()` | `parse_pair()` | `markets/pairs.py` | ✅ Ported | Parses "BTC/USD" → CanonicalPair(base="BTC", quote="USD"). |
| `validate_tob()` | `validate_tob()` | `marketdata/topofbook.py` | ✅ Ported | Validates TopOfBook invariants (not crossed, positive prices). |
| `tob_from_raw()` | `tob_from_raw()` | `marketdata/topofbook.py` | ✅ Ported | Factory function — primary validation boundary for market data. |
| `ohio_eligible()` | `ohio_eligible()` | `venues/registry.py` | ✅ Ported | Checks if an exchange is eligible for Ohio operation. |
| `validate_config()` | `validate_config()` | `config/app_config.py` | ✅ Ported | Validates application configuration at startup. |

---

## Porting Statistics

| Status | Count |
|--------|-------|
| ✅ Ported | 26 |
| 🔄 In Progress | 0 |
| 📋 Planned (Phase 1) | ~6 |
| ⏳ Deferred (Phase 2+) | ~15 |
| ❌ Not Porting | 0 |
| 🔀 Redesigned | ~12 |
| **Total tracked** | **~58** |

---

## Behavioral Differences Summary

These are intentional differences between Mathematica and Python implementations:

| Area | Mathematica Behavior | Python Behavior | Rationale |
|------|---------------------|-----------------|-----------|
| Missing data | `Missing[]` propagates through expressions | `ValueError` at boundary, rejected immediately | DEC-003: Validate at boundaries, trust downstream |
| Numeric types | Arbitrary precision by default | `Decimal` (explicit), `float` rejected | DEC-007: Exact decimal arithmetic |
| Data structures | Associations (mutable dictionaries) | Frozen dataclasses (immutable) | DEC-004: Immutability prevents mutation bugs |
| Response parsing | Single `ResponseDataStructure[]` | Per-connector typed parsers | Each exchange has unique response formats |
| Pair translation | String manipulation with flags | Lookup-based SymbolTranslator | More maintainable, explicit mapping |
| Function naming | CamelCase, multi-level (L2, L3) | snake_case, flattened where possible | Python conventions, reduce nesting |
| Threshold check | returnRaw >= thr AND returnGrs >= thr | return_net > thr | return_net implies both (more conservative); > not >= avoids boundary risk |

---

## Document History

| Date | Changes |
|------|---------|
| 2026-02-13 | Initial creation with comprehensive function inventory from CryptoArbitrage_V14.9.4_NoKeys.nb |
| 2026-02-14 | Updated Sections 7, 8, 9: 12 functions 📋→✅ for calculation layer implementation |
| 2026-02-14 | Updated Sections 6, 10: TrimExchangesToCalc → 🔧 Improved, TradesToExecute → ✅ Ported, SelectTradeToExecute → 🔧 Improved. Added threshold behavior to differences table. |
