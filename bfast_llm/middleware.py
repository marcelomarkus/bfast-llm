import sys
import json
from typing import Any, Dict, List, Tuple, Optional

from .registry import BFastRegistry
from .tool import BFastTool

try:
    import b_fast
except ImportError as e:
    raise ImportError(
        "Could not import 'b_fast'. The 'bfast-py' is a required dependency. "
        "Please ensure it is installed correctly: 'pip install bfast-py'"
    ) from e


class BFastLLM:
    """Middleware for transparently compressing LLM contexts using the B-FAST binary protocol."""

    def __init__(
        self,
        registry: Optional[BFastRegistry] = None,
        threshold_bytes: int = 1024,
        compress_payloads: bool = True,
    ):
        """
        Initialize BFastLLM middleware.

        Args:
            registry: A BFastRegistry instance. If None, creates an in-memory registry.
            threshold_bytes: Content size threshold above which compression is triggered (default: 1KB).
            compress_payloads: Whether to apply compression to BFast payloads.
        """
        self.registry = registry or BFastRegistry()
        self.tool = BFastTool(self.registry)
        self.threshold_bytes = threshold_bytes
        self.compress_payloads = compress_payloads
        self.encoder = b_fast.BFast()

    def compress_messages(
        self, messages: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """
        Interprets messages, serializing large payloads into B-FAST binaries and swapping them with references.

        Args:
            messages: List of message dictionaries in standard Chat Completion format.

        Returns:
            A tuple of (modified_messages, was_compressed)
        """
        modified_messages = []
        was_compressed = False

        for msg in messages:
            msg.get("role")
            content = msg.get("content")

            # We compress large content in user or tool messages, or assistant tool results
            if (
                content is not None
                and isinstance(content, str)
                and len(content) >= self.threshold_bytes
            ):
                # Check if the content is valid JSON (list or dict)
                parsed_data = None
                stripped = content.strip()
                if (stripped.startswith("{") and stripped.endswith("}")) or (
                    stripped.startswith("[") and stripped.endswith("]")
                ):
                    try:
                        parsed_data = json.loads(content)
                    except json.JSONDecodeError:
                        pass

                if parsed_data is not None:
                    # Encode to B-FAST binary format
                    try:
                        binary_data = self.encoder.encode_packed(
                            parsed_data, compress=self.compress_payloads
                        )
                        # Register in our BFast cache registry
                        ref_tag = self.registry.register(binary_data)

                        # Create new message with content replaced by reference tag
                        new_msg = msg.copy()
                        new_msg["content"] = (
                            f"The data was compressed using B-FAST to save tokens:\n{ref_tag}\n"
                            f"To inspect or read this data, call the 'bfast_retrieve' tool with id."
                        )
                        modified_messages.append(new_msg)
                        was_compressed = True
                        continue
                    except Exception as e:
                        # Log error internally and keep original message if encoding fails
                        print(
                            f"[BFastLLM] Warning: Failed to serialize payload: {e}",
                            file=sys.stderr,
                        )

            # Also handle if the content is a dictionary, list, NumPy array, or Pandas DataFrame
            else:
                is_supported = False
                processed_content = content

                # Check for Pandas DataFrame (lazy check by class name)
                if content is not None and type(content).__name__ == "DataFrame":
                    try:
                        import pandas as pd

                        if isinstance(content, pd.DataFrame):
                            processed_content = content.to_dict(orient="records")
                            is_supported = True
                    except ImportError:
                        pass

                # Check for NumPy ndarray (numpy is already a dependency of bfast-py)
                elif content is not None and type(content).__name__ == "ndarray":
                    try:
                        import numpy as np

                        if isinstance(content, np.ndarray):
                            is_supported = True
                    except ImportError:
                        pass

                # Accept dict/list
                elif content is not None and isinstance(content, (dict, list)):
                    is_supported = True

                if is_supported:
                    try:
                        # Convert object/array to BFast directly
                        binary_data = self.encoder.encode_packed(
                            processed_content, compress=self.compress_payloads
                        )
                        ref_tag = self.registry.register(binary_data)
                        new_msg = msg.copy()
                        new_msg["content"] = (
                            f"The data was compressed using B-FAST to save tokens:\n{ref_tag}\n"
                            f"To inspect or read this data, call the 'bfast_retrieve' tool with id."
                        )
                        modified_messages.append(new_msg)
                        was_compressed = True
                        continue
                    except Exception as e:
                        print(
                            f"[BFastLLM] Warning: Failed to serialize object/array payload: {e}",
                            file=sys.stderr,
                        )

            modified_messages.append(msg)

        return modified_messages, was_compressed

    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the retrieve tool definition to inject into the LLM call."""
        return [self.tool.get_openai_tool_definition()]

    def handle_tool_call(self, tool_call: Any) -> Optional[str]:
        """
        Handle a tool call if it is 'bfast_retrieve'.

        Args:
            tool_call: The tool call object (e.g. from OpenAI response, having 'function' attribute with 'name' and 'arguments')

        Returns:
            The string result of the retrieval if handled, otherwise None.
        """
        # Supports both object style and dictionary style tool calls
        name = getattr(tool_call, "name", None) or getattr(
            getattr(tool_call, "function", None), "name", None
        )
        arguments = getattr(tool_call, "arguments", None) or getattr(
            getattr(tool_call, "function", None), "arguments", None
        )

        if name != "bfast_retrieve":
            if isinstance(tool_call, dict):
                func = tool_call.get("function", {})
                if func.get("name") == "bfast_retrieve":
                    name = "bfast_retrieve"
                    arguments = func.get("arguments")
                else:
                    return None
            else:
                return None

        if isinstance(arguments, str):
            try:
                args = json.loads(arguments)
            except json.JSONDecodeError:
                return "Error: Invalid arguments JSON."
        else:
            args = arguments or {}

        ref_id = args.get("ref_id")
        fmt = args.get("format", "markdown")

        if not ref_id:
            return "Error: Missing 'ref_id' argument."
        return self.tool.bfast_retrieve(ref_id, format=fmt)


def wrap_completion(
    completion_func, threshold_bytes: int = 1024, compress_payloads: bool = True
):
    """
    Wrap any OpenAI-compatible chat completion function to automatically
    apply B-FAST compression and transparently handle retrieval tool calls.
    """
    bfast_llm = BFastLLM(
        threshold_bytes=threshold_bytes, compress_payloads=compress_payloads
    )

    def wrapped(*args, **kwargs):
        messages = kwargs.get("messages")
        if not messages:
            return completion_func(*args, **kwargs)

        # Copy to avoid side-effects on original user messages list
        compressed_messages, was_compressed = bfast_llm.compress_messages(messages)
        kwargs["messages"] = list(compressed_messages)

        if was_compressed:
            tools = kwargs.get("tools", [])
            has_tool = any(
                t.get("function", {}).get("name") == "bfast_retrieve" for t in tools
            )
            if not has_tool:
                tools = list(tools) + bfast_llm.get_tools()
                kwargs["tools"] = tools
                if "tool_choice" not in kwargs:
                    kwargs["tool_choice"] = "auto"

        while True:
            response = completion_func(*args, **kwargs)

            is_dict = isinstance(response, dict)
            choices = (
                response.get("choices", [])
                if is_dict
                else getattr(response, "choices", [])
            )
            if not choices:
                return response

            message = choices[0].get("message", {}) if is_dict else choices[0].message
            tool_calls = (
                message.get("tool_calls", [])
                if is_dict
                else getattr(message, "tool_calls", None)
            )

            if not tool_calls:
                return response

            bfast_calls = []
            for tc in tool_calls:
                name = (
                    tc.get("function", {}).get("name")
                    if is_dict
                    else getattr(getattr(tc, "function", None), "name", None)
                )
                if name == "bfast_retrieve":
                    bfast_calls.append(tc)

            if not bfast_calls:
                return response

            print(f"[BFastLLM] Resolving {len(bfast_calls)} retrieval calls...")

            kwargs["messages"].append(message)

            for tc in bfast_calls:
                result = bfast_llm.handle_tool_call(tc)
                tc_id = tc.get("id") if is_dict else getattr(tc, "id", None)
                kwargs["messages"].append(
                    {
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "name": "bfast_retrieve",
                        "content": result,
                    }
                )

    return wrapped


def bfast_tune(client, threshold_bytes: int = 1024, compress_payloads: bool = True):
    """
    Tune an LLM client instance (e.g. OpenAI) to automatically apply B-FAST prompt
    compression and handle retrieval tool calls transparently.
    """
    original_create = client.chat.completions.create
    wrapped_create = wrap_completion(
        original_create, threshold_bytes, compress_payloads
    )

    class WrappedCompletions:
        def __init__(self, original):
            self._original = original

        def __getattr__(self, name):
            return getattr(self._original, name)

        def create(self, *args, **kwargs):
            return wrapped_create(*args, **kwargs)

    client.chat.completions = WrappedCompletions(client.chat.completions)
    return client
