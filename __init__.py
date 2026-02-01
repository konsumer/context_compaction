"""
LLMS extension for context compaction via /compact command.
"""

import json
import os
from pathlib import Path
import aiohttp

def __install__(ctx):
    """
    Install hook - registers the /compact command filter.

    Args:
        ctx: ExtensionContext providing access to registration methods
    """

    # Load configuration
    config_path = Path(__file__).parent / "config.json"
    config = {}

    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)

    # Default config values
    provider = config.get('provider', 'ollama')
    model = config.get('model', 'llama3.2:3b')
    summary_prompt = config.get('summary_prompt', 'Summarize this conversation concisely.')

    async def compact_command_filter(chat, context):
        """
        Filter that intercepts /compact command and compacts conversation history.

        Args:
            chat: Dictionary containing the chat request data
            context: Dictionary containing additional context information
        """

        # Get the last user message
        if 'messages' not in chat or len(chat['messages']) == 0:
            return

        last_message = chat['messages'][-1]

        # Check if it's a user message with /compact command
        if last_message.get('role') != 'user':
            return

        content = last_message.get('content', '')

        # Handle content as list of blocks
        text_content = None
        if isinstance(content, list) and len(content) > 0:
            if isinstance(content[0], dict):
                text_content = content[0].get('text', '')
            else:
                text_content = str(content[0])
        else:
            text_content = str(content)

        # Check if message starts with /compact
        if not text_content or not text_content.strip().startswith('/compact'):
            return

        ctx.log(f"[context_compaction] ✓ Intercepted /compact command")

        # Build conversation history for summarization (exclude the /compact message)
        messages_to_summarize = chat['messages'][:-1]

        if len(messages_to_summarize) == 0:
            ctx.log(f"[context_compaction] No messages to compact")
            # Replace with a message saying nothing to compact
            if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict):
                content[0]['text'] = "No conversation history to compact."
            else:
                last_message['content'] = "No conversation history to compact."
            return

        ctx.log(f"[context_compaction] Compacting {len(messages_to_summarize)} messages")

        # Build a text representation of the conversation
        conversation_text = ""
        for msg in messages_to_summarize:
            role = msg.get('role', 'unknown')
            msg_content = msg.get('content', '')

            # Extract text from content
            if isinstance(msg_content, list):
                text_parts = []
                for part in msg_content:
                    if isinstance(part, dict):
                        text_parts.append(part.get('text', ''))
                    else:
                        text_parts.append(str(part))
                msg_text = ' '.join(text_parts)
            else:
                msg_text = str(msg_content)

            conversation_text += f"{role}: {msg_text}\n\n"

        ctx.log(f"[context_compaction] Conversation length: {len(conversation_text)} chars")

        # Call the configured model to generate summary
        summary = await generate_summary(conversation_text, provider, model, summary_prompt, ctx)

        if not summary:
            ctx.log(f"[context_compaction] Failed to generate summary")
            # Replace with error message
            if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict):
                content[0]['text'] = "Failed to generate summary."
            else:
                last_message['content'] = "Failed to generate summary."
            return

        ctx.log(f"[context_compaction] ✓ Generated summary ({len(summary)} chars)")

        # Replace the entire conversation with a single system message containing the summary
        system_message = {
            "role": "system",
            "content": f"[Previous conversation summary]\n{summary}"
        }

        # Replace messages array with just the system message
        chat['messages'] = [system_message]

        # Update the /compact message to ask LLM to acknowledge the summary
        acknowledgment_prompt = "Please respond with a brief acknowledgment that you've received the conversation summary and are ready to continue. Keep your response very short (1-2 sentences)."

        if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict):
            content[0]['text'] = acknowledgment_prompt
        else:
            last_message['content'] = acknowledgment_prompt

        # Add the modified user message back
        chat['messages'].append(last_message)

        ctx.log(f"[context_compaction] ✓ Replaced context with summary ({len(messages_to_summarize)} messages -> summary)")

    async def generate_summary(conversation_text, provider, model, prompt, ctx):
        """
        Generate a summary using the configured LLM.

        Args:
            conversation_text: The conversation history as text
            provider: Provider name (e.g., 'ollama')
            model: Model name (e.g., 'llama3.2:3b')
            prompt: Summary prompt template
            ctx: Extension context for logging

        Returns:
            Summary text or None if failed
        """
        try:
            # Build the API URL based on provider
            if provider == 'ollama':
                api_url = "http://localhost:11434/v1/chat/completions"
            else:
                ctx.log(f"[context_compaction] Unsupported provider: {provider}")
                return None

            # Build the request
            messages = [
                {"role": "system", "content": prompt},
                {"role": "user", "content": conversation_text}
            ]

            payload = {
                "model": model,
                "messages": messages,
                "stream": False
            }

            ctx.log(f"[context_compaction] Calling {provider} API: {api_url}")

            # Make the API call
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        ctx.log(f"[context_compaction] API error {response.status}: {error_text}")
                        return None

                    result = await response.json()

                    # Extract summary from response
                    if 'choices' in result and len(result['choices']) > 0:
                        summary = result['choices'][0]['message']['content']
                        return summary.strip()
                    else:
                        ctx.log(f"[context_compaction] Unexpected response format: {result}")
                        return None

        except Exception as e:
            ctx.log(f"[context_compaction] Error generating summary: {e}")
            return None

    # Register the filter
    ctx.register_chat_request_filter(compact_command_filter)
    ctx.log("[context_compaction] Extension loaded - /compact command registered")
