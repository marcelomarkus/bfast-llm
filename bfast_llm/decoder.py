import struct
import lz4.block
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID
from typing import Any, List, Union

class BFastError(Exception):
    """Exception raised for B-FAST parsing and decoding errors."""
    pass

class BFastDecoder:
    """Decoder for the B-FAST binary serialization protocol in Python."""

    @staticmethod
    def decompress(data: bytes) -> bytes:
        """Decompress B-FAST data if compressed, otherwise return it as is."""
        if len(data) < 2:
            raise BFastError("Buffer too small for B-FAST payload")
        
        # If starts with 'BF' magic, it is not compressed
        if data[0:2] == b'BF':
            return data
        
        if len(data) < 8:
            raise BFastError("Buffer too small for compressed B-FAST data")
        
        uncompressed_size = struct.unpack('<I', data[:4])[0]
        
        # Try direct block decompression first (single-chunk)
        try:
            decompressed = lz4.block.decompress(data)
            return decompressed
        except Exception:
            # Fall back to parallel chunk decompression
            try:
                chunks_count = struct.unpack('<I', data[4:8])[0]
                offset = 8
                decompressed_chunks = []
                for _ in range(chunks_count):
                    if offset + 4 > len(data):
                        raise BFastError("Unexpected end of data in parallel compression chunk headers")
                    chunk_len = struct.unpack('<I', data[offset:offset+4])[0]
                    offset += 4
                    if offset + chunk_len > len(data):
                        raise BFastError("Unexpected end of data in parallel compression chunk data")
                    chunk_data = data[offset:offset+chunk_len]
                    offset += chunk_len
                    # Decompress single chunk (contains its own 4-byte uncompressed chunk size prefix)
                    decompressed_chunks.append(lz4.block.decompress(chunk_data))
                
                result = b''.join(decompressed_chunks)
                if len(result) != uncompressed_size:
                    raise BFastError(f"Decompressed size mismatch: expected {uncompressed_size}, got {len(result)}")
                return result
            except Exception as e:
                raise BFastError(f"LZ4 decompression failed: {e}")

    @classmethod
    def decode(cls, data: Union[bytes, bytearray]) -> Any:
        """
        Decode B-FAST binary data to Python objects.
        
        Args:
            data: bytes or bytearray containing B-FAST data (optionally compressed)
            
        Returns:
            Decoded Python object
        """
        if isinstance(data, bytearray):
            data = bytes(data)
            
        decompressed_data = cls.decompress(data)
        
        if len(decompressed_data) < 6:
            raise BFastError("Decompressed buffer too small for B-FAST header")
            
        # Parse Header
        magic = decompressed_data[0:2]
        if magic != b'BF':
            raise BFastError("Invalid B-FAST magic number")
            
        decompressed_data[2]
        decompressed_data[3]
        string_table_count = struct.unpack('<H', decompressed_data[4:6])[0]
        
        offset = 6
        string_table: List[str] = []
        
        # Parse string table
        for _ in range(string_table_count):
            if offset >= len(decompressed_data):
                raise BFastError("Unexpected end of buffer in string table")
            length = decompressed_data[offset]
            offset += 1
            if offset + length > len(decompressed_data):
                raise BFastError("String extends beyond buffer in string table")
            string_bytes = decompressed_data[offset:offset+length]
            string_table.append(string_bytes.decode('utf-8'))
            offset += length
            
        # Parse payload
        decoder = _BFastParser(decompressed_data, offset, string_table)
        return decoder.parse()


class _BFastParser:
    def __init__(self, data: bytes, offset: int, string_table: List[str]):
        self.data = data
        self.offset = offset
        self.string_table = string_table
        self.data_len = len(data)

    def _check_bounds(self, size: int) -> None:
        if self.offset + size > self.data_len:
            raise BFastError("Unexpected end of buffer during parsing")

    def parse(self) -> Any:
        self._check_bounds(1)
        tag = self.data[self.offset]
        self.offset += 1
        
        # Null
        if tag == 0x10:
            return None
            
        # Booleans
        if tag == 0x20:
            return False
        if tag == 0x21:
            return True
            
        # Int64
        if tag == 0x38:
            self._check_bounds(8)
            val = struct.unpack('<q', self.data[self.offset:self.offset+8])[0]
            self.offset += 8
            return val
            
        # Small integers (bit-packed)
        if (tag & 0xF0) == 0x30:
            return tag & 0x0F
            
        # Float64
        if tag == 0x40:
            self._check_bounds(8)
            val = struct.unpack('<d', self.data[self.offset:self.offset+8])[0]
            self.offset += 8
            return val
            
        # Raw string
        if tag == 0x50:
            self._check_bounds(4)
            length = struct.unpack('<I', self.data[self.offset:self.offset+4])[0]
            self.offset += 4
            self._check_bounds(length)
            val = self.data[self.offset:self.offset+length].decode('utf-8')
            self.offset += length
            return val
            
        # List/Array
        if tag == 0x60:
            self._check_bounds(4)
            length = struct.unpack('<I', self.data[self.offset:self.offset+4])[0]
            self.offset += 4
            array = []
            for _ in range(length):
                array.append(self.parse())
            return array
            
        # Object start
        if tag == 0x70:
            obj = {}
            while self.offset < self.data_len and self.data[self.offset] != 0x7F:
                self._check_bounds(4)
                key_id = struct.unpack('<I', self.data[self.offset:self.offset+4])[0]
                self.offset += 4
                
                if key_id >= len(self.string_table):
                    raise BFastError(f"Invalid string table index: {key_id}")
                    
                key = self.string_table[key_id]
                value = self.parse()
                obj[key] = value
                
            if self.offset >= self.data_len:
                raise BFastError("Object not properly terminated")
                
            self.offset += 1  # Skip 0x7F
            return obj
            
        # Bytes
        if tag == 0x80:
            self._check_bounds(4)
            length = struct.unpack('<I', self.data[self.offset:self.offset+4])[0]
            self.offset += 4
            self._check_bounds(length)
            val = self.data[self.offset:self.offset+length]
            self.offset += length
            return val
            
        # NumPy Array (f64)
        if tag == 0x90:
            self._check_bounds(4)
            length = struct.unpack('<I', self.data[self.offset:self.offset+4])[0]
            self.offset += 4
            self._check_bounds(length * 8)
            
            array = []
            for _ in range(length):
                val = struct.unpack('<d', self.data[self.offset:self.offset+8])[0]
                array.append(val)
                self.offset += 8
            return array
            
        # DateTime (0xD1) - ISO 8601 string
        if tag == 0xD1:
            self._check_bounds(4)
            length = struct.unpack('<I', self.data[self.offset:self.offset+4])[0]
            self.offset += 4
            self._check_bounds(length)
            iso_str = self.data[self.offset:self.offset+length].decode('utf-8')
            self.offset += length
            return datetime.fromisoformat(iso_str)
            
        # Date (0xD2) - ISO 8601 date string
        if tag == 0xD2:
            self._check_bounds(4)
            length = struct.unpack('<I', self.data[self.offset:self.offset+4])[0]
            self.offset += 4
            self._check_bounds(length)
            iso_str = self.data[self.offset:self.offset+length].decode('utf-8')
            self.offset += length
            return date.fromisoformat(iso_str)
            
        # Time (0xD3) - ISO 8601 time string
        if tag == 0xD3:
            self._check_bounds(4)
            length = struct.unpack('<I', self.data[self.offset:self.offset+4])[0]
            self.offset += 4
            self._check_bounds(length)
            iso_str = self.data[self.offset:self.offset+length].decode('utf-8')
            self.offset += length
            return time.fromisoformat(iso_str)
            
        # UUID (0xD4) - hex string or standard uuid format
        if tag == 0xD4:
            self._check_bounds(4)
            length = struct.unpack('<I', self.data[self.offset:self.offset+4])[0]
            self.offset += 4
            self._check_bounds(length)
            hex_str = self.data[self.offset:self.offset+length].decode('utf-8')
            self.offset += length
            # If it's a raw 32-char hex string, we format or parse directly
            return UUID(hex_str)
            
        # Decimal (0xD5) - decimal string
        if tag == 0xD5:
            self._check_bounds(4)
            length = struct.unpack('<I', self.data[self.offset:self.offset+4])[0]
            self.offset += 4
            self._check_bounds(length)
            dec_str = self.data[self.offset:self.offset+length].decode('utf-8')
            self.offset += length
            return Decimal(dec_str)
            
        raise BFastError(f"Unknown tag: 0x{tag:02x}")
