import hashlib
import sqlite3
from typing import Any, Dict, Optional, Union
from pathlib import Path

from .decoder import BFastDecoder
from .compressor import BFastCompressor


class BFastRegistry:
    """Registry for managing and storing B-FAST binary payloads."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        """
        Initialize the registry.

        Args:
            db_path: Path to SQLite file for persistent storage. If None, uses in-memory storage.
        """
        self.db_path = db_path
        self.in_memory_cache: Dict[str, bytes] = {}
        self.summaries: Dict[str, str] = {}

        if db_path is not None:
            self._init_db()

    def _init_db(self) -> None:
        db_file = Path(self.db_path)
        # Ensure parent directories exist
        db_file.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bfast_payloads (
                ref_id TEXT PRIMARY KEY,
                binary_data BLOB NOT NULL,
                summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()

    def register(self, binary_data: bytes, summary: Optional[str] = None) -> str:
        """
        Register a B-FAST binary payload in the registry.

        Args:
            binary_data: The B-FAST binary payload (bytes)
            summary: Optional pre-computed summary. If None, it will be automatically generated.

        Returns:
            A formatted XML/HTML reference tag that can be sent to the LLM.
        """
        # Generate content-hash-based reference ID to automatically deduplicate identical payloads
        hasher = hashlib.sha256(binary_data)
        ref_id = f"bfast_{hasher.hexdigest()[:12]}"

        if summary is None:
            try:
                decoded = BFastDecoder.decode(binary_data)
                summary = BFastCompressor.summarize(decoded)
            except Exception as e:
                summary = f"BFast Payload (failed to decode: {e})"

        # Format human-readable size
        size_bytes = len(binary_data)
        if size_bytes < 1024:
            size_str = f"{size_bytes}B"
        else:
            size_str = f"{size_bytes / 1024:.2f}KB"

        # Store in database if persistent, else in-memory
        if self.db_path is not None:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO bfast_payloads (ref_id, binary_data, summary) VALUES (?, ?, ?)",
                (ref_id, binary_data, summary),
            )
            conn.commit()
            conn.close()
        else:
            self.in_memory_cache[ref_id] = binary_data
            self.summaries[ref_id] = summary

        return f'<bfast-ref id="{ref_id}" size="{size_str}" summary="{summary}"/>'

    def get(self, ref_id: str) -> Optional[bytes]:
        """Retrieve the binary payload by reference ID."""
        # Clean up ID if LLM included surrounding quotes or brackets
        ref_id = ref_id.strip("'\"<>[]")

        if self.db_path is not None:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT binary_data FROM bfast_payloads WHERE ref_id = ?", (ref_id,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return row[0]
        else:
            return self.in_memory_cache.get(ref_id)

        return None

    def get_summary(self, ref_id: str) -> Optional[str]:
        """Retrieve the summary of a payload by reference ID."""
        ref_id = ref_id.strip("'\"<>[]")

        if self.db_path is not None:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute(
                "SELECT summary FROM bfast_payloads WHERE ref_id = ?", (ref_id,)
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return row[0]
        else:
            return self.summaries.get(ref_id)

        return None

    def get_decoded(self, ref_id: str) -> Any:
        """Retrieve and decode the payload by reference ID."""
        binary_data = self.get(ref_id)
        if binary_data is None:
            raise KeyError(f"Payload ID '{ref_id}' not found in registry.")
        return BFastDecoder.decode(binary_data)

    def clear(self) -> None:
        """Clear all payloads in the registry."""
        if self.db_path is not None:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("DELETE FROM bfast_payloads")
            conn.commit()
            conn.close()
        else:
            self.in_memory_cache.clear()
            self.summaries.clear()
