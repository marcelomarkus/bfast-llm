import pytest
from datetime import datetime, date
from decimal import Decimal
from uuid import UUID
import b_fast
from bfast_llm.decoder import BFastDecoder, BFastError


def test_decoder_with_mock_data():
    # 1. Create a test payload with various types
    payload = {
        "name": "Markus",
        "age": 30,
        "active": True,
        "balance": Decimal("100.50"),
        "user_id": UUID("12345678-1234-5678-1234-567812345678"),
        "created_at": datetime(2026, 7, 5, 20, 0, 0),
        "birth_date": date(1996, 7, 5),
    }

    # 2. Encode using b_fast
    bf = b_fast.BFast()
    binary_data = bf.encode_packed(payload, compress=True)

    # 3. Decode using BFastDecoder
    decoded = BFastDecoder.decode(binary_data)

    # 4. Verify
    assert decoded["name"] == payload["name"]
    assert decoded["age"] == payload["age"]
    assert decoded["active"] == payload["active"]
    assert decoded["balance"] == payload["balance"]
    assert decoded["user_id"] == payload["user_id"]
    assert decoded["created_at"] == payload["created_at"]
    assert decoded["birth_date"] == payload["birth_date"]


def test_decoder_invalid_data():
    with pytest.raises(BFastError):
        BFastDecoder.decode(b"invalid binary data")
