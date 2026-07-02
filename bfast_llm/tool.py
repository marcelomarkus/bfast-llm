import json
from typing import Any, Dict
import csv
import io

from .registry import BFastRegistry

class BFastTool:
    """Implement LLM tools for interacting with B-FAST context."""
    
    def __init__(self, registry: BFastRegistry):
        self.registry = registry

    def bfast_retrieve(self, ref_id: str, format: str = "markdown") -> str:
        """
        Retrieve and decode a B-FAST payload from the registry, formatting it as requested.
        
        Args:
            ref_id: The reference ID of the payload (e.g., 'bfast_abc123')
            format: Output format. One of 'markdown', 'json', 'yaml', or 'csv'. Default is 'markdown'.
            
        Returns:
            Decoded payload formatted as a string.
        """
        try:
            decoded = self.registry.get_decoded(ref_id)
        except KeyError:
            return f"Error: Payload ID '{ref_id}' not found in registry."
        except Exception as e:
            return f"Error: Failed to decode payload '{ref_id}': {e}"
            
        format = format.lower()
        
        if format == "json":
            # Handle non-serializable types by converting to string
            def default_serializer(o):
                if hasattr(o, 'isoformat'):
                    return o.isoformat()
                return str(o)
            return json.dumps(decoded, indent=2, default=default_serializer)
            
        elif format == "yaml":
            try:
                import yaml
                # Custom representers for special types
                def decimal_representer(dumper, data):
                    return dumper.represent_scalar('tag:yaml.org,2002:float', str(data))
                def datetime_representer(dumper, data):
                    return dumper.represent_scalar('tag:yaml.org,2002:timestamp', data.isoformat())
                def uuid_representer(dumper, data):
                    return dumper.represent_scalar('tag:yaml.org,2002:str', str(data))
                
                yaml.add_representer(type(None), lambda dumper, _: dumper.represent_scalar('tag:yaml.org,2002:null', 'null'))
                # Register if types are present
                from decimal import Decimal
                from datetime import datetime, date, time
                from uuid import UUID
                yaml.add_representer(Decimal, decimal_representer)
                yaml.add_representer(datetime, datetime_representer)
                yaml.add_representer(date, datetime_representer)
                yaml.add_representer(time, datetime_representer)
                yaml.add_representer(UUID, uuid_representer)
                
                return yaml.dump(decoded, default_flow_style=False)
            except ImportError:
                # Fallback to JSON
                return self.bfast_retrieve(ref_id, format="json") + "\n\n(Note: PyYAML not installed. Fell back to JSON.)"
                
        elif format == "csv":
            if isinstance(decoded, list) and decoded and isinstance(decoded[0], dict):
                output = io.StringIO()
                headers = list(decoded[0].keys())
                writer = csv.DictWriter(output, fieldnames=headers)
                writer.writeheader()
                for row in decoded:
                    # format non-serializable objects
                    formatted_row = {}
                    for k, v in row.items():
                        if hasattr(v, 'isoformat'):
                            formatted_row[k] = v.isoformat()
                        else:
                            formatted_row[k] = str(v)
                    writer.writerow(formatted_row)
                return output.getvalue()
            else:
                return self.bfast_retrieve(ref_id, format="json") + "\n\n(Note: Payload is not a list of dictionaries. Fell back to JSON.)"
                
        # Default/Markdown
        else:
            return self._format_markdown(decoded, ref_id)

    def _format_markdown(self, decoded: Any, ref_id: str) -> str:
        """Format decoded B-FAST values nicely as Markdown."""
        summary = self.registry.get_summary(ref_id) or "BFast Payload"
        header = f"### ⚡ B-FAST Payload `{ref_id}`\n*{summary}*\n\n"
        
        # Table formatting for list of dicts
        if isinstance(decoded, list) and decoded and isinstance(decoded[0], dict):
            headers = list(decoded[0].keys())
            lines = []
            lines.append("| " + " | ".join(headers) + " |")
            lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
            
            for item in decoded:
                row = []
                for h in headers:
                    val = item.get(h, "")
                    if val is None:
                        row.append("null")
                    elif isinstance(val, bool):
                        row.append("✅ Yes" if val else "❌ No")
                    elif hasattr(val, 'isoformat'):
                        row.append(val.isoformat())
                    else:
                        row.append(str(val).replace("\n", " ").replace("|", "\\|"))
                lines.append("| " + " | ".join(row) + " |")
                
            return header + "\n".join(lines)
            
        # List formatting for single dict
        elif isinstance(decoded, dict):
            lines = []
            lines.append("| Key | Value (Type) |")
            lines.append("| --- | --- |")
            for k, v in decoded.items():
                val_str = ""
                if v is None:
                    val_str = "*null*"
                elif isinstance(v, bool):
                    val_str = "✅ Yes" if v else "❌ No"
                elif hasattr(v, 'isoformat'):
                    val_str = f"`{v.isoformat()}`"
                else:
                    val_str = f"`{v}`"
                lines.append(f"| **{k}** | {val_str} ({type(v).__name__}) |")
            return header + "\n".join(lines)
            
        # Fallback for plain values
        return f"{header}```python\n{repr(decoded)}\n```"

    def get_openai_tool_definition(self) -> Dict[str, Any]:
        """Get the OpenAI/Anthropic compatible tool schema for bfast_retrieve."""
        return {
            "type": "function",
            "function": {
                "name": "bfast_retrieve",
                "description": (
                    "Retrieve the original content of a compressed B-FAST payload. "
                    "Use this when you need to inspect the full contents of data references (e.g. <bfast-ref id='...'/>)."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "ref_id": {
                            "type": "string",
                            "description": "The unique reference ID of the payload to retrieve, starting with 'bfast_'."
                        },
                        "format": {
                            "type": "string",
                            "enum": ["markdown", "json", "yaml", "csv"],
                            "default": "markdown",
                            "description": "The format to return the decoded data in. Default is 'markdown'."
                        }
                    },
                    "required": ["ref_id"]
                }
            }
        }
