from typing import Any, Union
try:
    import b_fast
except ImportError as e:
    raise ImportError(
        "Could not import 'b_fast'. The 'bfast-py' is a required dependency. "
        "Please ensure it is installed correctly: 'pip install bfast-py'"
    ) from e

class BFastError(Exception):
    """Exception raised for B-FAST parsing and decoding errors."""
    pass

class BFastDecoder:
    """Decoder for the B-FAST binary serialization protocol."""

    @classmethod
    def decode(cls, data: Union[bytes, bytearray]) -> Any:
        """
        Decode B-FAST binary data to Python objects.
        
        Args:
            data: bytes or bytearray containing B-FAST data compressed
            
        Returns:
            Decoded Python object
        """
        if isinstance(data, bytearray):
            data = bytes(data)
            
        try:
            bf = b_fast.BFast()
            return bf.decode_packed(data, decompress=True)
        except Exception as e:
            raise BFastError(f"B-FAST decoding failed: {e}")
