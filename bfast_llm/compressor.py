from typing import Any
from datetime import datetime, date, time
from decimal import Decimal
from uuid import UUID

class BFastCompressor:
    """Helper to summarize B-FAST data structure and generate token-efficient representation."""
    
    @classmethod
    def summarize(cls, data: Any, max_list_items_preview: int = 3) -> str:
        """
        Generate a concise text summary of a python object decoded from B-FAST.
        
        Args:
            data: Any Python object
            max_list_items_preview: How many items to preview if listing individual elements
            
        Returns:
            A string describing the structure and summary of the data.
        """
        if data is None:
            return "Null"
            
        if isinstance(data, bool):
            return f"Boolean ({data})"
            
        if isinstance(data, (int, float)):
            return f"{type(data).__name__} ({data})"
            
        if isinstance(data, (datetime, date, time, UUID, Decimal)):
            return f"{type(data).__name__} ({data})"
            
        if isinstance(data, str):
            if len(data) <= 100:
                return f"String: '{data}'"
            return f"String (length={len(data)}): '{data[:60]}...'"
            
        if isinstance(data, (bytes, bytearray)):
            return f"Binary data (size={len(data)} bytes)"
            
        if isinstance(data, list):
            if not data:
                return "Empty List"
            
            # Check if it's a list of dictionaries (common for datasets)
            first_item = data[0]
            if isinstance(first_item, dict):
                keys_info = []
                for k, v in first_item.items():
                    val_type = type(v).__name__
                    keys_info.append(f"{k}: {val_type}")
                schema_str = ", ".join(keys_info)
                return f"List of {len(data)} objects. Schema: {{{schema_str}}}"
            
            # Check if it's a list of numbers (float/int)
            if all(isinstance(x, (int, float)) for x in data[:10]):
                nums = [float(x) for x in data]
                if nums:
                    min_val = min(nums)
                    max_val = max(nums)
                    avg_val = sum(nums) / len(nums)
                    return f"List of {len(data)} numbers (float/int). Stats: min={min_val:.4f}, max={max_val:.4f}, avg={avg_val:.4f}"
            
            # General list
            types = set(type(x).__name__ for x in data[:10])
            types_str = "|".join(types)
            return f"List of {len(data)} items of type ({types_str})"
            
        if isinstance(data, dict):
            if not data:
                return "Empty Object"
                
            keys_preview = []
            for k, v in list(data.items())[:10]:
                val_summary = ""
                if isinstance(v, (int, float, bool, str)) and not isinstance(v, str) or (isinstance(v, str) and len(v) < 30):
                    val_summary = f"={repr(v)}"
                else:
                    val_summary = f" ({type(v).__name__})"
                keys_preview.append(f"'{k}'{val_summary}")
                
            total_keys = len(data)
            keys_str = ", ".join(keys_preview)
            if total_keys > 10:
                keys_str += f", ... (+{total_keys - 10} more)"
                
            return f"Object with {total_keys} keys: {{{keys_str}}}"
            
        return f"Unknown Type ({type(data).__name__}): {str(data)[:100]}"
