"""
Simple LLMS extension that registers a /compact command filter.
"""

def __install__(ctx):
    """
    Install hook - registers filters and other server enhancements.
    NOTE: This must be a synchronous function, but handlers can be async.

    Args:
        ctx: ExtensionContext providing access to registration methods
    """

    async def compact_command_filter(chat, context):
        """
        Filter that intercepts /compact command and replaces prompt.

        Args:
            chat: Dictionary containing the chat request data
            context: Dictionary containing additional context information
        """
        ctx.log(f"[context_compaction] Filter called with chat keys: {chat.keys()}")

        # Get the last user message
        if 'messages' in chat and len(chat['messages']) > 0:
            last_message = chat['messages'][-1]

            ctx.log(f"[context_compaction] Last message role: {last_message.get('role')}")
            ctx.log(f"[context_compaction] Last message content type: {type(last_message.get('content'))}")

            # Check if it's a user message
            if last_message.get('role') == 'user':
                # Get the content - it can be a string or a list of content blocks
                content = last_message.get('content', '')

                # Handle content as list of blocks (newer format)
                text_content = None
                if isinstance(content, list) and len(content) > 0:
                    if isinstance(content[0], dict):
                        text_content = content[0].get('text', '')
                    else:
                        text_content = str(content[0])
                else:
                    text_content = str(content)

                ctx.log(f"[context_compaction] Text content: {text_content}")

                # Check if message starts with /compact
                if text_content and text_content.strip().startswith('/compact'):
                    ctx.log(f"[context_compaction] ✓ Intercepted /compact command")

                    # Replace the message content with our test message
                    if isinstance(content, list) and len(content) > 0 and isinstance(content[0], dict):
                        # Modify the text field directly
                        content[0]['text'] = "testing context_compaction"
                        ctx.log(f"[context_compaction] ✓ Modified content[0]['text'] = {content[0]['text']}")
                    elif isinstance(content, list):
                        # Replace list item
                        last_message['content'][0] = "testing context_compaction"
                        ctx.log(f"[context_compaction] ✓ Modified content[0] = {last_message['content'][0]}")
                    else:
                        # Replace string content
                        last_message['content'] = "testing context_compaction"
                        ctx.log(f"[context_compaction] ✓ Modified content = {last_message['content']}")

                    ctx.log(f"[context_compaction] ✓ Final last_message content: {last_message['content']}")

    # Register the filter to run before chat requests are processed
    ctx.register_chat_request_filter(compact_command_filter)
    ctx.log("[context_compaction] Extension loaded - /compact command filter registered")
