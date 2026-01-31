"""
Context Compaction Extension for llms

Automatically compacts conversation context when it reaches a threshold,
replacing the history with a summary to enable extended conversations.
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class CompactionConfig:
    """Configuration for context compaction"""
    enabled: bool = True
    threshold: float = 0.8  # Trigger at 80% of context
    provider: Optional[str] = None  # Use same provider if None
    model: Optional[str] = None  # Use same model if None
    notify_user: bool = True  # Add notification message when compaction occurs
    use_simple_prompt: bool = False  # Use simpler prompt for faster models
    summary_prompt: str = """Please provide a comprehensive summary of the conversation so far. Preserve:
- All critical context and decisions
- User preferences and constraints
- Technical details and requirements
- Code snippets and configurations
- Conversation flow and key topics

Be thorough but concise. This summary will replace the conversation history."""
    simple_prompt: str = """Summarize this conversation concisely. Include: key decisions, requirements, code context, and current task. Be brief."""


# Global state
compaction_config = CompactionConfig()
chat_contexts: Dict[str, Dict[str, Any]] = {}
extension_dir: Optional[Path] = None


def load_config(config_path: Path) -> CompactionConfig:
    """Load configuration from file or create default"""
    if config_path.exists():
        try:
            with open(config_path) as f:
                data = json.load(f)
                logger.info(f"Loaded configuration from {config_path}")
                return CompactionConfig(**data)
        except Exception as e:
            logger.warning(f"Failed to load config from {config_path}: {e}, using defaults")
    else:
        logger.info(f"No config file at {config_path}, using defaults")

    return CompactionConfig()


def save_config(config: CompactionConfig, config_path: Path):
    """Save configuration to file"""
    try:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, 'w') as f:
            json.dump(asdict(config), f, indent=2)
        logger.info(f"Saved configuration to {config_path}")
    except Exception as e:
        logger.error(f"Failed to save config to {config_path}: {e}")


async def __install__(ctx):
    """Install the extension into the server"""
    global compaction_config, extension_dir

    # Determine extension directory
    # Extensions are typically in ~/.llms/extensions/<extension_name>
    home = Path.home()
    extension_dir = home / ".llms" / "extensions" / "context_compaction"
    config_path = extension_dir / "config.json"

    # Load configuration from file
    compaction_config = load_config(config_path)

    logger.info(f"Context compaction enabled: {compaction_config.enabled}, threshold: {compaction_config.threshold}")

    # Store context reference for later use
    ctx._compaction_ctx = ctx

    # Register filters
    ctx.register_request_filter(on_request)
    ctx.register_response_filter(on_response)

    # Add API endpoints
    ctx.add_get('/config', get_config)
    ctx.add_post('/config', update_config)
    ctx.add_post('/compact', trigger_compaction)
    ctx.add_get('/status', get_status)


async def on_request(ctx, request_data: Dict[str, Any]):
    """Process requests and apply compaction if needed"""
    if not compaction_config.enabled:
        return request_data

    conversation_id = get_conversation_id(request_data)
    messages = request_data.get('messages', [])

    # Check if this conversation needs compaction
    if conversation_id in chat_contexts and chat_contexts[conversation_id].get('needs_compaction', False):
        logger.info(f"Applying compaction to conversation {conversation_id}")

        # Generate summary
        summary = await compact_conversation(ctx, messages[:-1],
                                            request_data.get('provider'),
                                            request_data.get('model'))

        if summary:
            # Apply compaction
            request_data['messages'] = apply_compaction(messages, summary)

            # Reset compaction flag
            chat_contexts[conversation_id]['needs_compaction'] = False
            chat_contexts[conversation_id]['compaction_count'] = chat_contexts[conversation_id].get('compaction_count', 0) + 1

            logger.info(f"Compacted {len(messages)} messages to {len(request_data['messages'])} messages")
        else:
            logger.error("Failed to generate summary, skipping compaction")

    return request_data


async def on_response(ctx, request_data: Dict[str, Any], response_data: Dict[str, Any]):
    """Monitor responses and trigger compaction if needed"""
    if not compaction_config.enabled:
        return response_data

    # Extract usage information
    usage = response_data.get('usage', {})
    prompt_tokens = usage.get('prompt_tokens', 0)
    total_tokens = usage.get('total_tokens', 0)

    # Get model context limit from provider metadata
    model = request_data.get('model', '')
    provider_name = request_data.get('provider', '')
    context_limit = get_model_context_limit(ctx, provider_name, model)

    if context_limit == 0:
        logger.warning(f"Could not determine context limit for model {model}")
        return response_data

    # Calculate usage percentage
    usage_ratio = prompt_tokens / context_limit

    # Track per-conversation state
    conversation_id = get_conversation_id(request_data)
    if conversation_id not in chat_contexts:
        chat_contexts[conversation_id] = {
            'usage_ratio': usage_ratio,
            'needs_compaction': False,
            'message_count': len(request_data.get('messages', [])),
            'compaction_count': 0
        }
    else:
        chat_contexts[conversation_id]['usage_ratio'] = usage_ratio
        chat_contexts[conversation_id]['message_count'] = len(request_data.get('messages', []))

    # Check if we need compaction
    if usage_ratio >= compaction_config.threshold:
        logger.warning(f"Context usage at {usage_ratio:.1%}, threshold: {compaction_config.threshold:.1%}")
        chat_contexts[conversation_id]['needs_compaction'] = True

        # Try to compact on next request
        # We can't modify the history here, but we flag it
        # The actual compaction happens in the request filter

    return response_data


def get_conversation_id(request_data: Dict[str, Any]) -> str:
    """Extract or generate a conversation ID"""
    # Use a hash of the first message if available
    messages = request_data.get('messages', [])
    if messages:
        first_msg = str(messages[0])
        return str(hash(first_msg))
    return "default"


def get_model_context_limit(ctx, provider_name: str, model: str) -> int:
    """Get actual context window size from provider metadata"""
    try:
        # Try to get provider
        if hasattr(ctx, 'get_provider'):
            provider = ctx.get_provider(provider_name) if provider_name else None

            if provider and hasattr(provider, 'model_info'):
                model_info = provider.model_info(model)
                if model_info:
                    limit = model_info.get('limit', {})
                    context_limit = limit.get('context')
                    if context_limit:
                        logger.debug(f"Got context limit for {model}: {context_limit}")
                        return context_limit

        # If we can't get it from the provider, try to get it from all providers
        if hasattr(ctx, 'get_providers'):
            providers = ctx.get_providers()
            for prov_name, provider in providers.items():
                if hasattr(provider, 'model_info'):
                    model_info = provider.model_info(model)
                    if model_info:
                        limit = model_info.get('limit', {})
                        context_limit = limit.get('context')
                        if context_limit:
                            logger.debug(f"Got context limit for {model} from {prov_name}: {context_limit}")
                            return context_limit

    except Exception as e:
        logger.warning(f"Error getting context limit from provider: {e}")

    # Fallback to estimate if we can't get real data
    return estimate_context_limit_fallback(model)


def estimate_context_limit_fallback(model: str) -> int:
    """Fallback: Estimate context window size for common models"""
    model_lower = model.lower()

    # OpenAI models
    if 'gpt-4-turbo' in model_lower or 'gpt-4-1106' in model_lower:
        return 128000
    elif 'gpt-4-32k' in model_lower:
        return 32768
    elif 'gpt-4' in model_lower:
        return 8192
    elif 'gpt-3.5-turbo-16k' in model_lower:
        return 16384
    elif 'gpt-3.5-turbo' in model_lower:
        return 4096

    # Anthropic models
    elif 'claude-3-opus' in model_lower or 'claude-3-sonnet' in model_lower or 'claude-3-haiku' in model_lower:
        return 200000
    elif 'claude-2' in model_lower:
        return 100000
    elif 'claude' in model_lower:
        return 100000

    # Local models (conservative estimates)
    elif 'llama' in model_lower or 'mistral' in model_lower or 'mixtral' in model_lower:
        if '32k' in model_lower:
            return 32768
        elif '16k' in model_lower:
            return 16384
        return 8192

    # Default
    logger.warning(f"Unknown model {model}, using default context limit of 8192")
    return 8192


async def compact_conversation(ctx, messages: list, provider: Optional[str] = None, model: Optional[str] = None):
    """Create a summary of the conversation history"""
    # Choose prompt based on configuration
    prompt = compaction_config.simple_prompt if compaction_config.use_simple_prompt else compaction_config.summary_prompt

    # Build summary request
    summary_messages = [
        {"role": "user", "content": prompt},
        {"role": "user", "content": f"Conversation to summarize:\n\n{format_messages_for_summary(messages)}"}
    ]

    # Use configured or current provider/model
    request = {
        "messages": summary_messages,
        "model": model or compaction_config.model,
        "provider": provider or compaction_config.provider,
        "temperature": 0.3,  # Lower temperature for consistent summaries
    }

    # Remove None values
    request = {k: v for k, v in request.items() if v is not None}

    # Call the LLM to generate summary
    try:
        response = await ctx.chat_completion(request)
        summary_content = response.get('choices', [{}])[0].get('message', {}).get('content', '')

        if summary_content:
            logger.info(f"Generated summary of {len(messages)} messages")
            return summary_content
        else:
            logger.error("Failed to generate summary: empty response")
            return None
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        return None


def format_messages_for_summary(messages: list) -> str:
    """Format messages for summarization"""
    formatted = []
    for i, msg in enumerate(messages):
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        formatted.append(f"[{i+1}] {role.upper()}: {content}")
    return "\n\n".join(formatted)


def apply_compaction(messages: list, summary: str) -> list:
    """Replace message history with summary"""
    # Keep system message if present
    system_messages = [msg for msg in messages if msg.get('role') == 'system']

    # Keep last few messages for context continuity
    recent_messages = messages[-2:] if len(messages) > 2 else messages

    # Create summary message
    summary_content = f"[Context Summary]\n\n{summary}"

    # Add user notification if enabled
    if compaction_config.notify_user:
        notification = f"\n\n---\n*Note: Context compacted to save memory. {len(messages)} messages summarized into this summary.*"
        summary_content += notification

    # Create new message list
    new_messages = system_messages + [
        {"role": "assistant", "content": summary_content}
    ] + recent_messages

    return new_messages


# API Endpoints

async def get_config(request):
    """Get current compaction configuration"""
    return {
        'enabled': compaction_config.enabled,
        'threshold': compaction_config.threshold,
        'provider': compaction_config.provider,
        'model': compaction_config.model,
        'notify_user': compaction_config.notify_user,
        'use_simple_prompt': compaction_config.use_simple_prompt,
        'summary_prompt': compaction_config.summary_prompt,
        'simple_prompt': compaction_config.simple_prompt
    }


async def update_config(request):
    """Update compaction configuration"""
    global compaction_config

    data = await request.json()

    if 'enabled' in data:
        compaction_config.enabled = bool(data['enabled'])
    if 'threshold' in data:
        compaction_config.threshold = float(data['threshold'])
    if 'provider' in data:
        compaction_config.provider = data['provider']
    if 'model' in data:
        compaction_config.model = data['model']
    if 'notify_user' in data:
        compaction_config.notify_user = bool(data['notify_user'])
    if 'use_simple_prompt' in data:
        compaction_config.use_simple_prompt = bool(data['use_simple_prompt'])
    if 'summary_prompt' in data:
        compaction_config.summary_prompt = data['summary_prompt']
    if 'simple_prompt' in data:
        compaction_config.simple_prompt = data['simple_prompt']

    logger.info(f"Configuration updated: threshold={compaction_config.threshold}")

    # Save updated config
    if extension_dir:
        config_path = extension_dir / "config.json"
        save_config(compaction_config, config_path)

    return {'status': 'ok', 'config': await get_config(None)}


async def trigger_compaction(request):
    """Manually trigger compaction for a conversation"""
    data = await request.json()
    messages = data.get('messages', [])
    provider = data.get('provider')
    model = data.get('model')

    if not messages:
        return {'error': 'No messages provided'}, 400

    # This would need access to the extension context
    # For now, return a placeholder
    return {
        'status': 'not_implemented',
        'message': 'Manual compaction will be triggered on next request'
    }


async def get_status(request):
    """Get compaction status for all conversations"""
    return {
        'enabled': compaction_config.enabled,
        'conversations': {
            conv_id: {
                'usage_ratio': data['usage_ratio'],
                'needs_compaction': data['needs_compaction'],
                'message_count': data['message_count'],
                'compaction_count': data.get('compaction_count', 0)
            }
            for conv_id, data in chat_contexts.items()
        }
    }
