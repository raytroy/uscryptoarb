"""
Strategy layer — pure trade selection logic on validated inputs.

This layer receives already-validated domain types (TopOfBook, ArbOpportunity,
FeeSchedule) from the calculation layer and applies strategic filtering:
staleness checks, threshold comparisons, and trade selection.

NO I/O. NO validation. NO side effects. (DEC-002, DEC-003, LL-020)

Mathematica equivalents:
    TradesToExecute[]        -> scanner.find_trades_to_execute
    SelectTradeToExecute[]   -> selection.select_trade
    TrimExchangesToCalc[]    -> scanner.filter_valid_exchanges
"""
