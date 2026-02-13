from setuptools import find_packages, setup

setup(
    name="uscryptoarb",
    version="0.0.1",
    description="Cross-exchange, taker-only crypto arbitrage scanner (Phase 0/1)",
    package_dir={"": "src"},
    packages=find_packages("src"),
    include_package_data=True,
    package_data={"uscryptoarb": ["py.typed"]},
)
