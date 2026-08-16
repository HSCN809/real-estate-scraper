
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.validators import DataNormalizer


def test_normalize_price_benchmark(benchmark):
    result = benchmark(DataNormalizer.normalize_price, "1.500.000 TL")
    assert result == 1_500_000.0
