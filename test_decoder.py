import json
import sys
from pathlib import Path
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from bfast_llm.decoder import BFastDecoder


def test_decoder():
    binary_path = Path("/tmp/bfast_typed_test.bin")
    expected_path = Path("/tmp/bfast_typed_expected.json")

    if not binary_path.exists() or not expected_path.exists():
        print(
            "Test files not found in /tmp. Please run the b-fast test generator first."
        )
        sys.exit(1)

    print("Reading binary data...")
    binary_data = binary_path.read_bytes()

    print("Decoding binary data with BFastDecoder...")
    decoded = BFastDecoder.decode(binary_data)

    print("Reading expected JSON...")
    with open(expected_path, "r") as f:
        expected = json.load(f)

    print("\nDecoded object:")
    print(decoded)

    # Assertions
    # Note: decoded is [model] (a list of one object) based on test_integration_types.py
    assert isinstance(decoded, list), "Expected decoded data to be a list"
    assert len(decoded) == 1, "Expected list of length 1"

    item = decoded[0]

    assert item["name"] == expected["name"]
    assert item["age"] == expected["age"]
    assert isinstance(item["created_at"], datetime)
    assert item["created_at"].isoformat() == expected["created_at"]
    assert isinstance(item["birth_date"], date)
    assert item["birth_date"].isoformat() == expected["birth_date"]
    assert isinstance(item["wake_time"], time)
    assert item["wake_time"].isoformat() == expected["wake_time"]
    assert isinstance(item["user_id"], UUID)
    assert str(item["user_id"]) == expected["user_id"]
    assert isinstance(item["balance"], Decimal)
    assert str(item["balance"]) == expected["balance"]
    assert item["active"] == expected["active"]

    print(
        "\n✅ All assertions passed successfully! The Python BFastDecoder matches the Rust encoder perfectly."
    )


if __name__ == "__main__":
    test_decoder()
