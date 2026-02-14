"""
Calculation layer — pure deterministic math on validated inputs.

This layer receives already-validated domain types (TopOfBook, Decimal,
CanonicalPair) and performs arbitrage return calculations, fee math,
and Kelly Criterion position sizing.

NO I/O. NO validation. NO side effects.

Mathematica equivalents:
    ReturnCalc[]      → returns.calc_return_raw / calc_return_grs / calc_return_net
    ArbCalcFinal[]    → arb_calc.calc_arb_opportunity
    CalcKellyAmount[] → sizing.calc_kelly_amount
"""
