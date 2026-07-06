import re
import pytest
import b_fast
from bfast_llm.registry import BFastRegistry
from bfast_llm.decoder import BFastError


def get_id(xml_tag: str) -> str:
    match = re.search(r'id="([^"]+)"', xml_tag)
    return match.group(1) if match else xml_tag


def test_in_memory_registry():
    reg = BFastRegistry()

    # Test register with manual summary
    xml_tag = reg.register(b"test data", summary="manual summary")
    ref_id = get_id(xml_tag)
    assert ref_id.startswith("bfast_")

    # Test get
    assert reg.get(ref_id) == b"test data"
    assert reg.get_summary(ref_id) == "manual summary"

    # Test get_decoded raises error for invalid B-FAST payload
    with pytest.raises(BFastError):
        reg.get_decoded(ref_id)

    # Test clear
    reg.clear()
    assert reg.get(ref_id) is None
    assert reg.get_summary(ref_id) is None


def test_registry_auto_summary():
    reg = BFastRegistry()

    # Encode mock object to B-FAST
    bf = b_fast.BFast()
    binary_data = bf.encode_packed({"name": "Markus", "age": 30}, compress=True)

    # Register without summary
    xml_tag = reg.register(binary_data)
    ref_id = get_id(xml_tag)

    # Get summary
    summary = reg.get_summary(ref_id)
    assert summary is not None
    assert "Object with 2" in summary or "name" in summary or "age" in summary
    assert reg.get(ref_id) == binary_data

    # Test get_decoded
    decoded = reg.get_decoded(ref_id)
    assert decoded["name"] == "Markus"
    assert decoded["age"] == 30


def test_persistent_sqlite_registry(tmp_path):
    db_file = tmp_path / "test_registry.db"
    reg = BFastRegistry(db_path=db_file)

    xml_tag = reg.register(b"sqlite content", summary="sqlite summary")
    ref_id = get_id(xml_tag)

    assert reg.get(ref_id) == b"sqlite content"
    assert reg.get_summary(ref_id) == "sqlite summary"

    # Close connection by creating a new registry on same file to check persistence
    reg2 = BFastRegistry(db_path=db_file)
    assert reg2.get(ref_id) == b"sqlite content"
    assert reg2.get_summary(ref_id) == "sqlite summary"

    # Test clear in sqlite
    reg2.clear()
    assert reg2.get(ref_id) is None
