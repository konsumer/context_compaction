# Architecture Documentation

This document describes the internal architecture of the context compaction extension.

## Overview

The extension uses llms' filter system to intercept requests and responses, monitoring token usage and applying compaction when needed.

## Components

### 1. Configuration Management

**CompactionConfig**
- Dataclass storing all configuration
- Loaded from JSON file on startup
- Updated via API calls (persisted to file)
- Global state accessible to all components

**Configuration Sources** (priority order):
1. API updates (runtime, saved to file)
2. Config file (`~/.llms/extensions/context_compaction/config.json`)
3. Defaults (fallback)

**Configuration Persistence**
- Config loaded from `~/.llms/extensions/context_compaction/config.json` on startup
- If file doesn't exist, defaults are used and file is created
- API updates are automatically saved to the config file
- Changes persist across server restarts

### 2. Conversation Tracking

**chat_contexts**: Dictionary mapping conversation IDs to state
- `usage_ratio`: Current token usage percentage
- `needs_compaction`: Flag indicating compaction should occur
- `message_count`: Number of messages in history
- `compaction_count`: Times this conversation has been compacted

**Conversation ID Generation**
- Hash of first message content
- Ensures consistent tracking across requests
- Session-scoped (not persistent)

### 3. Filter Pipeline

#### Request Filter (`on_request`)

**Purpose**: Apply compaction before sending to LLM

**Flow**:
1. Check if compaction is enabled
2. Look up conversation state
3. If `needs_compaction` is true:
   - Generate summary of message history
   - Replace history with summary
   - Reset compaction flag
   - Update statistics
4. Return modified request

**Key Decisions**:
- Only summarizes messages before the current one
- Preserves system messages
- Keeps last 2 messages for context continuity

#### Response Filter (`on_response`)

**Purpose**: Monitor token usage and flag conversations for compaction

**Flow**:
1. Extract usage data from response
2. Estimate context limit for model
3. Calculate usage ratio
4. Update conversation state
5. If ratio exceeds threshold, set `needs_compaction` flag
6. Return unmodified response

**Key Decisions**:
- Uses estimates for context limits (no tokenizer dependency)
- Flags for future compaction (doesn't block response)
- Tracks usage across conversation lifetime

### 4. Summarization Engine

**compact_conversation()**

**Purpose**: Generate conversation summary using LLM

**Process**:
1. Format messages for summarization
2. Build summary request with custom prompt
3. Send to configured (or current) provider/model
4. Extract summary from response
5. Handle errors gracefully

**Configuration**:
- Uses separate provider/model if specified
- Falls back to current conversation's provider/model
- Lower temperature (0.3) for consistency

**Error Handling**:
- Logs errors but doesn't crash
- Returns None on failure
- Compaction skipped if summary fails

### 5. History Management

**apply_compaction()**

**Purpose**: Replace message history with summary

**Strategy**:
1. Extract and preserve system messages
2. Extract last N messages (default: 2)
3. Create new message list:
   - System messages (if any)
   - Summary as assistant message
   - Recent messages for continuity
4. Return new message list

**Rationale**:
- System messages define model behavior
- Recent messages provide immediate context
- Summary captures historical context
- Reduced token count while preserving functionality

### 6. Context Limit Retrieval

**get_model_context_limit()**

**Purpose**: Retrieve actual model context window from provider metadata

**Method**:
1. Access provider via `ctx.get_provider(provider_name)`
2. Call `provider.model_info(model)` to get metadata
3. Extract `limit.context` field from model info
4. Fall back to `estimate_context_limit_fallback()` if unavailable

**API Integration**:
```python
# Get provider
provider = ctx.get_provider("openai")

# Get model metadata
model_info = provider.model_info("gpt-4-turbo")

# Extract context limit
limit = model_info.get("limit", {})
context_tokens = limit.get("context")  # 128000
output_tokens = limit.get("output")    # 4096
```

**Data Source**:
- llms maintains a comprehensive model database in `providers.json`
- Updated daily from models.dev
- Contains accurate limits for 530+ models across 24 providers

**Fallback Estimation**:
Only used when provider metadata is unavailable:
- Pattern matching on model name
- Conservative estimates for common model families
- Default: 8K tokens

**Advantages**:
- Always accurate for supported models
- Automatically updated as llms' database updates
- No maintenance needed for new models
- Includes output token limits

### 7. API Endpoints

#### GET /ext/context_compaction/config
- Returns current configuration
- No authentication required

#### POST /ext/context_compaction/config
- Updates configuration
- Accepts partial updates
- Returns new configuration

#### GET /ext/context_compaction/status
- Shows all tracked conversations
- Includes usage stats and compaction flags
- Useful for monitoring

#### POST /ext/context_compaction/compact
- Manual compaction trigger
- Not fully implemented (requires request context)
- Placeholder for future enhancement

## Data Flow

### Normal Request (No Compaction)

```
User Request
    ↓
Request Filter (on_request)
    • Check conversation state
    • No compaction needed
    • Pass through unchanged
    ↓
LLM Processing
    ↓
Response Filter (on_response)
    • Extract usage data
    • Calculate ratio: 65%
    • Update conversation state
    • Pass through unchanged
    ↓
User Response
```

### Request with Compaction

```
User Request
    ↓
Request Filter (on_request)
    • Check conversation state
    • needs_compaction = true
    • Generate summary
    • Replace history
        - 50 messages → 3 messages
        - Keep: system, summary, last message
    • Reset compaction flag
    ↓
LLM Processing (with reduced context)
    ↓
Response Filter (on_response)
    • Extract usage data
    • Calculate ratio: 30% (reduced)
    • Update conversation state
    • Pass through unchanged
    ↓
User Response
```

## Extension Points

### Custom Summarization Strategies

To add custom summarization:

1. Modify `compact_conversation()` to support strategy parameter
2. Add strategy-specific prompt templates
3. Update configuration to include strategy selection

Example strategies:
- **Extractive**: Extract key messages verbatim
- **Abstractive**: Generate new summary text (current)
- **Hierarchical**: Create multi-level summaries
- **Selective**: Only summarize specific message types

### Custom Token Counting

To improve token usage accuracy (beyond context limits):

1. Add tokenizer dependencies (e.g., tiktoken for OpenAI)
2. Count actual tokens in messages before sending
3. Account for model-specific special tokens
4. Track actual vs counted usage for validation

Note: Context limits are already accurate via provider metadata

### Persistent State

To persist conversation state:

1. Add database dependency (SQLite, Redis, etc.)
2. Replace in-memory `chat_contexts` dict
3. Serialize/deserialize conversation state
4. Add cleanup for old conversations

### Advanced Compaction Triggers

Beyond simple threshold:

1. Time-based: Compact after X hours
2. Message-based: Compact after Y messages
3. Topic-based: Compact when topic changes
4. Hybrid: Combine multiple triggers

## Performance Considerations

### Latency

**Summarization adds latency**:
- Extra LLM call during compaction
- Typically 1-5 seconds depending on model
- Can be mitigated by:
  - Using faster model for summaries
  - Async processing (future enhancement)
  - Caching summaries

### Memory

**Minimal memory overhead**:
- Small configuration object
- Conversation state is lightweight
- No message buffering

### Scalability

**Current limitations**:
- In-memory state per server instance
- No distributed state sharing
- Conversation tracking not persistent

**Future improvements**:
- Shared state via Redis
- Conversation state persistence
- Load balancing considerations

## Security

### API Endpoints

**Current state**: No authentication
- All endpoints are public
- Anyone can update configuration
- Status exposes conversation IDs

**Recommendations**:
- Use `ctx.check_auth()` for protected endpoints
- Validate configuration inputs
- Sanitize conversation IDs in responses

### Summary Generation

**Potential risks**:
- Summaries may leak sensitive information
- Model provider sees conversation content
- Summary prompt could be manipulated

**Mitigations**:
- Allow custom summary prompts with validation
- Support local models for privacy
- Add option to exclude sensitive messages

## Testing Strategy

### Unit Tests

**Coverage needed**:
- Configuration management
- Context limit estimation
- Message formatting
- History replacement

### Integration Tests

**Scenarios to test**:
- Normal conversation flow
- Compaction trigger and application
- Multiple concurrent conversations
- Configuration updates
- Error handling

### Load Tests

**Metrics to measure**:
- Compaction latency
- Memory usage over time
- Accuracy of context estimation
- Summary quality

## Future Enhancements

### High Priority

1. **Persistent state**: Survive server restarts
2. **Better conversation IDs**: More robust tracking
3. **UI dashboard**: Visual monitoring and control
4. **Token-accurate counting**: Use tokenizers for precise usage tracking (context limits are already accurate)

### Medium Priority

1. **Caching**: Cache summaries to avoid regeneration
2. **Smart strategies**: Context-aware compaction
3. **Metrics**: Track effectiveness over time
4. **Custom filters**: User-defined rules

### Low Priority

1. **A/B testing**: Compare compaction strategies
2. **ML-based triggers**: Learn optimal compaction timing
3. **Compression**: Beyond simple summarization
4. **Multi-model**: Different models for different types

## Questions & Answers

**Q: Why use filters instead of middleware?**
A: Filters are the llms extension mechanism. They provide hooks at the right points in the request lifecycle.

**Q: Why not compact every N messages?**
A: Token-based triggers are more accurate since message length varies. Future enhancement could support message-based triggers.

**Q: How does this handle streaming responses?**
A: Current implementation doesn't specifically handle streaming. The response filter processes the final response with usage data.

**Q: Can I use different models for different conversations?**
A: The extension uses per-request provider/model settings, so yes. Configuration applies globally but can be overridden per request.

**Q: What happens if summarization fails?**
A: Compaction is skipped, error is logged, and the conversation continues with full history. The compaction flag remains set for retry on next request.

**Q: How are system messages handled?**
A: System messages are preserved during compaction since they define the model's behavior. They're never included in the summarized portion.
