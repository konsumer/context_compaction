#!/usr/bin/env python3
"""
Test script for context compaction extension
"""
import asyncio
import json
from typing import Dict, Any


class MockProvider:
    """Mock provider for testing"""

    def __init__(self, name, models_data):
        self.name = name
        self.models_data = models_data

    def model_info(self, model):
        """Return model metadata"""
        for model_id, info in self.models_data.items():
            if model_id.lower() == model.lower():
                return info
        return None


class MockContext:
    """Mock extension context for testing"""

    def __init__(self):
        self.request_filters = []
        self.response_filters = []
        self.routes = {}

        # Set up mock providers with model data
        self.providers = {
            'openai': MockProvider('openai', {
                'gpt-4-turbo': {'limit': {'context': 128000, 'output': 4096}},
                'gpt-3.5-turbo': {'limit': {'context': 4096, 'output': 4096}},
            }),
            'anthropic': MockProvider('anthropic', {
                'claude-3-opus-20240229': {'limit': {'context': 200000, 'output': 4096}},
                'claude-3-sonnet-20240229': {'limit': {'context': 200000, 'output': 4096}},
            }),
        }

    def get_provider(self, name):
        """Get provider by name"""
        return self.providers.get(name)

    def get_providers(self):
        """Get all providers"""
        return self.providers

    def register_request_filter(self, func):
        self.request_filters.append(func)
        print(f"✓ Registered request filter: {func.__name__}")

    def register_response_filter(self, func):
        self.response_filters.append(func)
        print(f"✓ Registered response filter: {func.__name__}")

    def add_get(self, path, handler):
        self.routes[f"GET {path}"] = handler
        print(f"✓ Registered GET /ext/context_compaction{path}")

    def add_post(self, path, handler):
        self.routes[f"POST {path}"] = handler
        print(f"✓ Registered POST /ext/context_compaction{path}")

    async def chat_completion(self, request: Dict[str, Any]):
        """Mock chat completion"""
        messages = request.get('messages', [])
        summary = f"Summary of {len(messages)} messages with key context preserved."
        return {
            'choices': [
                {
                    'message': {
                        'content': summary
                    }
                }
            ]
        }


async def test_extension():
    """Test the extension installation and functionality"""
    print("=" * 60)
    print("Testing Context Compaction Extension")
    print("=" * 60)

    # Import the extension
    import __init__ as ext

    print("\n1. Testing installation...")
    ctx = MockContext()
    await ext.__install__(ctx)

    print(f"\n2. Testing configuration...")
    config = await ext.get_config(None)
    print(f"   Config: {json.dumps(config, indent=2)}")

    print(f"\n3. Testing context limit retrieval...")
    test_cases = [
        ("openai", "gpt-4-turbo"),
        ("openai", "gpt-3.5-turbo"),
        ("anthropic", "claude-3-opus-20240229"),
        (None, "llama-2-7b"),  # Unknown model, should use fallback
    ]
    for provider_name, model in test_cases:
        limit = ext.get_model_context_limit(ctx, provider_name, model)
        source = "provider metadata" if limit > 8192 or provider_name else "fallback estimate"
        print(f"   {model} ({provider_name or 'unknown'}): {limit:,} tokens ({source})")

    print(f"\n4. Testing message formatting...")
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"},
        {"role": "assistant", "content": "Hi there! How can I help?"},
        {"role": "user", "content": "Tell me about Python."},
    ]
    formatted = ext.format_messages_for_summary(messages)
    print(f"   Formatted {len(messages)} messages:")
    print(f"   {formatted[:100]}...")

    print(f"\n5. Testing compaction...")
    summary = await ext.compact_conversation(ctx, messages)
    print(f"   Generated summary: {summary}")

    print(f"\n6. Testing history replacement...")
    compacted = ext.apply_compaction(messages, summary)
    print(f"   Original: {len(messages)} messages")
    print(f"   Compacted: {len(compacted)} messages")
    print(f"   New structure:")
    for i, msg in enumerate(compacted):
        role = msg.get('role')
        content_preview = msg.get('content', '')[:50]
        print(f"     [{i+1}] {role}: {content_preview}...")

    print(f"\n7. Testing response filter...")
    request_data = {
        "model": "gpt-4-turbo",
        "provider": "openai",
        "messages": messages
    }
    response_data = {
        "usage": {
            "prompt_tokens": 100000,  # High usage to trigger compaction
            "total_tokens": 105000
        }
    }
    result = await ext.on_response(ctx, request_data, response_data)
    conv_id = ext.get_conversation_id(request_data)
    status = ext.chat_contexts.get(conv_id, {})
    print(f"   Conversation status:")
    print(f"     Usage ratio: {status.get('usage_ratio', 0):.1%}")
    print(f"     Needs compaction: {status.get('needs_compaction', False)}")

    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_extension())
