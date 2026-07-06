from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID
from bfast_llm.summarizer import BFastSummarizer


def test_summarize_scalar_types():
    assert BFastSummarizer.summarize(None) == "Null"
    assert BFastSummarizer.summarize(True) == "Boolean (True)"
    assert BFastSummarizer.summarize(False) == "Boolean (False)"
    assert BFastSummarizer.summarize(42) == "int (42)"
    assert BFastSummarizer.summarize(3.14) == "float (3.14)"


def test_summarize_datetime_types():
    dt = datetime(2026, 7, 5, 20, 0, 0)
    d = date(2026, 7, 5)
    t = time(20, 0, 0)
    assert BFastSummarizer.summarize(dt) == f"datetime ({dt})"
    assert BFastSummarizer.summarize(d) == f"date ({d})"
    assert BFastSummarizer.summarize(t) == f"time ({t})"


def test_summarize_special_types():
    uid = UUID("12345678-1234-5678-1234-567812345678")
    dec = Decimal("100.50")
    assert BFastSummarizer.summarize(uid) == f"UUID ({uid})"
    assert BFastSummarizer.summarize(dec) == f"Decimal ({dec})"


def test_summarize_strings():
    assert BFastSummarizer.summarize("hello") == "String: 'hello'"
    long_str = "a" * 150
    assert (
        BFastSummarizer.summarize(long_str)
        == f"String (length=150): '{long_str[:60]}...'"
    )


def test_summarize_binary():
    assert BFastSummarizer.summarize(b"hello") == "Binary data (size=5 bytes)"
    assert (
        BFastSummarizer.summarize(bytearray(b"world")) == "Binary data (size=5 bytes)"
    )


def test_summarize_lists():
    assert BFastSummarizer.summarize([]) == "Empty List"

    # List of dicts
    list_dicts = [{"id": 1, "name": "Alice"}]
    assert (
        BFastSummarizer.summarize(list_dicts)
        == "List of 1 objects. Schema: {id: int, name: str}"
    )

    # List of numbers
    list_nums = [1.5, 2.5, 3.5]
    assert "List of 3 numbers (float/int)" in BFastSummarizer.summarize(list_nums)

    # General list
    list_gen = ["hello", 1, True]
    assert "List of 3 items of type" in BFastSummarizer.summarize(list_gen)


def test_summarize_dicts():
    assert BFastSummarizer.summarize({}) == "Empty Object"

    d = {"name": "Alice", "age": 30}
    summary = BFastSummarizer.summarize(d)
    assert "Object with 2 keys" in summary
    assert "'name'='Alice'" in summary
    assert "'age'=30" in summary
