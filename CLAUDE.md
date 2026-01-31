# Developer Guide for AI Assistants

This document is for AI assistants (like Claude) helping to develop, debug, or enhance this llms extension.

## Project Overview

**Name:** Context Compaction Extension for llms
**Purpose:** Automatically compact conversation context when approaching token limits
**Target:** llms.py framework by ServiceStack
**Use Case:** Resource-constrained hardware (especially Ollama on 4-8GB GPUs)
**GitHub Issue:** https://github.com/ServiceStack/llms/issues/30

---

## Quick Context

This extension monitors conversation token usage and automatically summarizes the message history when a threshold is reached, enabling longer conversations without running out of memory or context window.

**Key Innovation:** Uses real model metadata from llms' provider API instead of hardcoded estimates.

---

## Architecture

### Core Files

```
llms-extension-context_compaction/
├── __init__.py                    # Main extension code
├── test_extension.py             # Unit tests
├── example_config.json           # Default config template
├── README.md                     # User documentation
├── ARCHITECTURE.md               # Technical architecture
├── OLLAMA_GUIDE.md              # Ollama-specific guide
├── CHANGELOG.md                  # Version history
├── CONTRIBUTING.md               # Contribution guidelines
├── GITHUB_ISSUE_30_RESPONSE.md  # Issue resolution summary
├── CLAUDE.md                     # This file (AI assistant guide)
└── presets/                      # Configuration presets
    ├── README.md
    ├── ollama-4gb.json
    ├── ollama-8gb.json
    ├── openai.json
    └── anthropic.json
```

### Extension Entry Points

**llms calls these hooks:**

1. `__install__(ctx)` - Called when extension loads
   - Loads config from `~/.llms/extensions/context_compaction/config.json`
   - Registers request/response filters
   - Sets up API endpoints

2. `on_request(ctx, request_data)` - Before LLM call
   - Checks if compaction is needed
   - Applies compaction if flagged
   - Returns modified request

3. `on_response(ctx, request_data, response_data)` - After LLM response
   - Monitors token usage
   - Flags conversation for compaction if threshold exceeded
   - Returns unmodified response

### Key Functions

```python
# Config Management
load_config(config_path) -> CompactionConfig
save_config(config, config_path)

# Context Limit Detection (NEW - uses real metadata)
get_model_context_limit(ctx, provider_name, model) -> int

# Fallback (only if metadata unavailable)
estimate_context_limit_fallback(model) -> int

# Conversation Management
get_conversation_id(request_data) -> str
format_messages_for_summary(messages) -> str
compact_conversation(ctx, messages, provider, model) -> str
apply_compaction(messages, summary) -> list

# API Endpoints
get_config(request) -> dict
update_config(request) -> dict
get_status(request) -> dict
trigger_compaction(request) -> dict
```

---

## llms Framework Integration

### ExtensionContext API

The `ctx` object provides:

```python
# Provider access (NEW - critical for real context limits)
ctx.get_provider(name: str) -> Provider
ctx.get_providers() -> Dict[str, Provider]

# Filter registration
ctx.register_request_filter(func)
ctx.register_response_filter(func)

# API endpoints
ctx.add_get(path, handler)
ctx.add_post(path, handler)

# LLM calls
ctx.chat_completion(request) -> response
```

### Provider API (NEW)

Each provider has:

```python
provider.models -> Dict[str, Dict[str, Any]]
provider.model_info(model: str) -> Dict[str, Any]

# Model info structure:
{
  "id": "gpt-4-turbo",
  "name": "GPT-4 Turbo",
  "limit": {
    "context": 128000,   # ← This is what we need
    "output": 4096
  },
  "cost": {...},
  "tool_call": true,
  ...
}
```

**Important:** Always use `limit.context` not `context_length` or `max_tokens`.

---

## Common Development Tasks

### Adding a New Configuration Option

1. Add field to `CompactionConfig` dataclass in `__init__.py`:
```python
@dataclass
class CompactionConfig:
    new_field: bool = False  # Add here with default
```

2. Update `get_config()` to return it:
```python
return {
    'new_field': compaction_config.new_field
}
```

3. Update `update_config()` to accept it:
```python
if 'new_field' in data:
    compaction_config.new_field = bool(data['new_field'])
```

4. Update `example_config.json` with the new field

5. Document in README.md configuration section

6. Add to CHANGELOG.md

### Adding a New Preset

1. Create `presets/your-preset.json`:
```json
{
  "enabled": true,
  "threshold": 0.8,
  "provider": "provider_name",
  "model": "model_name",
  "notify_user": true,
  "use_simple_prompt": false,
  "summary_prompt": "...",
  "simple_prompt": "..."
}
```

2. Document in `presets/README.md`:
   - Add to table
   - Provide installation command
   - Explain use case

3. Reference in main README.md if appropriate

### Debugging Context Limit Detection

**Check if provider API is working:**

```python
# In __install__ or any filter function
providers = ctx.get_providers()
logger.info(f"Available providers: {list(providers.keys())}")

for name, provider in providers.items():
    if hasattr(provider, 'models'):
        logger.info(f"{name} has {len(provider.models)} models")
```

**Check specific model:**

```python
provider = ctx.get_provider("openai")
if provider:
    info = provider.model_info("gpt-4-turbo")
    logger.info(f"Model info: {info}")
    limit = info.get('limit', {})
    logger.info(f"Context limit: {limit.get('context')}")
```

**Fallback behavior:**

If `get_model_context_limit()` returns 8192, the fallback was used (metadata unavailable).

### Testing Changes

```bash
# Run unit tests
python3 test_extension.py

# Test with llms (requires llms installed)
llms serve

# In another terminal:
curl http://localhost:8000/ext/context_compaction/config
curl http://localhost:8000/ext/context_compaction/status
```

### Adding Support for New Model Families

**Preferred:** Use provider metadata (automatic, no code changes needed)

**If fallback needed:** Update `estimate_context_limit_fallback()`:

```python
def estimate_context_limit_fallback(model: str) -> int:
    model_lower = model.lower()

    # Add new family
    if 'new-model-family' in model_lower:
        if '32k' in model_lower:
            return 32768
        return 16384

    # ... existing checks ...
```

---

## Testing Strategy

### Unit Tests (`test_extension.py`)

Tests cover:
1. Extension installation (filters and routes)
2. Configuration loading
3. Context limit retrieval (provider API + fallback)
4. Message formatting
5. Summarization
6. History compaction
7. Response filtering

**Run tests:**
```bash
python3 test_extension.py
```

**Expected output:**
- All checkmarks (✓) for registration
- Real context limits from mock providers
- Fallback for unknown models
- Successful compaction simulation

### Integration Testing

**Manual testing with llms:**

1. Start llms with extension:
```bash
llms serve
```

2. Have a long conversation (or simulate with API):
```bash
for i in {1..50}; do
  echo "Message $i"
  curl -X POST http://localhost:8000/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model": "...", "messages": [...]}'
done
```

3. Check compaction status:
```bash
curl http://localhost:8000/ext/context_compaction/status
```

4. Verify logs show compaction occurring

---

## Common Issues & Solutions

### Issue: "Could not determine context limit for model X"

**Cause:** Provider metadata not available or model not found

**Debug:**
1. Check if provider exists: `ctx.get_provider(provider_name)`
2. Check if model exists in provider: `provider.models`
3. Check model name spelling/case
4. Verify llms version has model in database

**Solution:** Either fix provider/model name or rely on fallback

### Issue: Compaction not triggering

**Possible causes:**
1. `enabled: false` in config
2. Threshold set too high
3. Context limit detection failed (returns 0)
4. Conversation ID not consistent

**Debug:**
```bash
# Check config
curl http://localhost:8000/ext/context_compaction/config

# Check status
curl http://localhost:8000/ext/context_compaction/status

# Check logs for warnings
```

### Issue: Summaries losing important context

**Solutions:**
1. Disable `use_simple_prompt`: `{"use_simple_prompt": false}`
2. Customize `summary_prompt` to emphasize important aspects
3. Use a better summarization model
4. Increase threshold to preserve more context

### Issue: Out of memory on Ollama

**Cause:** Summarization model + main model exceeds VRAM

**Solutions:**
1. Lower threshold (e.g., 0.6 or 0.5)
2. Use smaller summarization model (phi3:mini, qwen2:1.5b)
3. Enable `use_simple_prompt: true`
4. Close other GPU applications

---

## Code Style & Conventions

### Python Style

- Follow PEP 8
- Use type hints where helpful
- Use descriptive variable names
- Add docstrings to functions
- Log important events with appropriate levels:
  - `logger.info()` - Normal operations
  - `logger.warning()` - Recoverable issues
  - `logger.error()` - Errors that skip functionality
  - `logger.debug()` - Detailed debugging info

### Configuration

- Use JSON for config files (not YAML or TOML)
- Provide sensible defaults
- Document all fields
- Validate input in `update_config()`

### Documentation

- Keep README.md user-focused
- Keep ARCHITECTURE.md developer-focused
- Keep OLLAMA_GUIDE.md hardware-specific
- Update CHANGELOG.md for all changes
- Keep examples up-to-date

---

## Extension Points for Future Work

### Easy Enhancements

1. **More presets** - Add configs for:
   - Google Gemini
   - Groq
   - Cohere
   - Local models (Mistral, Mixtral)
   - Memory-specific scenarios

2. **Custom prompts** - Add preset prompts for:
   - Code-focused conversations
   - General chat
   - Technical documentation
   - Q&A sessions

3. **Better notifications** - Enhance user feedback:
   - Show tokens saved
   - Show compaction time
   - Add optional sound/visual indicator

4. **Metrics** - Track and report:
   - Total compactions
   - Tokens saved
   - Time spent on summaries
   - Effectiveness metrics

### Medium Complexity

1. **Summary caching** - Cache summaries to avoid regeneration:
   - Hash message history
   - Store summary in cache
   - Reuse if history matches

2. **Async summarization** - Don't block on summary generation:
   - Queue summarization task
   - Continue conversation
   - Apply summary on next request

3. **Progressive summarization** - Multi-level summaries:
   - Keep recent detailed summaries
   - Compact old summaries further
   - Hierarchical context preservation

4. **Per-conversation config** - Allow different settings per chat:
   - Store in conversation metadata
   - Override global config
   - Useful for different contexts

### Complex Enhancements

1. **UI Dashboard** - Visual monitoring and control:
   - Show compaction history
   - Adjust settings in UI
   - Preview summaries
   - Manual compaction trigger

2. **Persistent state** - Remember across restarts:
   - Use SQLite or Redis
   - Store conversation state
   - Preserve compaction history
   - Enable recovery

3. **Smart compaction** - ML-based timing:
   - Learn optimal compaction points
   - Detect topic changes
   - Preserve important messages
   - Adaptive thresholds

4. **Distributed state** - Multi-server support:
   - Shared state via Redis
   - Consistent conversation tracking
   - Load balancer friendly

---

## Performance Considerations

### Latency

**Summarization adds 2-10 seconds per compaction:**
- Fast models (phi3:mini): 2-3s
- Balanced (llama3.2:3b): 3-5s
- Quality (llama3.1:8b): 5-10s
- Cloud APIs: 1-3s

**Mitigation:**
- Use faster models for summarization
- Enable simple prompt mode
- Consider async (future enhancement)

### Memory

**Extension overhead is minimal:**
- Config: < 1KB
- Per-conversation state: < 1KB
- No message buffering
- Total: < 100KB for 100 conversations

**Summarization memory:**
- Depends on model choice
- 2GB for small models (phi3:mini, llama3.2:3b)
- 4-5GB for larger models (llama3.1:8b, mistral:7b)

### Token Usage (API Costs)

**Per compaction:**
- Input: ~1000-5000 tokens (conversation history)
- Output: ~200-500 tokens (summary)
- Total: ~1200-5500 tokens

**Cost examples:**
- OpenAI GPT-4o-mini: $0.0015 - $0.008 per compaction
- Anthropic Claude Haiku: $0.003 - $0.014 per compaction
- Ollama (local): Free

---

## Security Considerations

### API Endpoints

**Current state:** No authentication

**Risk:** Anyone can modify config or view status

**If adding auth:**
```python
async def update_config(request):
    # Add authentication check
    if not await ctx.check_auth(request):
        return {'error': 'Unauthorized'}, 401

    # ... rest of function
```

### Privacy

**Summary generation:**
- Conversation content sent to summarization model
- Could leak sensitive information
- Consider local models for privacy

**Recommendations:**
- Document in README
- Allow excluding certain messages from summary
- Support local-only summarization

### Input Validation

**Already implemented:**
```python
if 'threshold' in data:
    compaction_config.threshold = float(data['threshold'])
```

**Could enhance:**
```python
if 'threshold' in data:
    threshold = float(data['threshold'])
    if not 0.0 <= threshold <= 1.0:
        return {'error': 'Threshold must be 0.0-1.0'}, 400
    compaction_config.threshold = threshold
```

---

## Working with the Repository

### Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes
edit __init__.py
edit README.md
edit CHANGELOG.md

# Test
python3 test_extension.py

# Commit
git add .
git commit -m "feat: add your feature

- Detail 1
- Detail 2
"

# Push
git push origin feature/your-feature
```

### Commit Messages

Follow conventional commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation only
- `test:` - Testing
- `refactor:` - Code refactoring
- `perf:` - Performance improvement

### Before Submitting PR

1. ✅ Run tests: `python3 test_extension.py`
2. ✅ Update README.md if user-facing changes
3. ✅ Update CHANGELOG.md with changes
4. ✅ Update ARCHITECTURE.md if implementation changes
5. ✅ Test with actual llms if possible
6. ✅ Check code style (PEP 8)

---

## Useful Resources

### llms Framework

- GitHub: https://github.com/ServiceStack/llms
- Docs: https://llmspy.org/docs/extensions
- Models DB: Updated daily from models.dev

### Related Issue

- Issue #30: https://github.com/ServiceStack/llms/issues/30
- Response: See `GITHUB_ISSUE_30_RESPONSE.md`

### Dependencies

- Python 3.8+
- llms framework
- dataclasses (built-in)
- json (built-in)
- logging (built-in)
- pathlib (built-in)

**No external dependencies** - works with base Python + llms

---

## Quick Reference

### File Locations (Runtime)

```bash
# Extension installation
~/.llms/extensions/context_compaction/

# Configuration file
~/.llms/extensions/context_compaction/config.json

# llms main config (to disable extension)
~/.llms/llms.json
```

### API Endpoints

```bash
# All endpoints prefixed with /ext/context_compaction

GET  /config     # Get current configuration
POST /config     # Update configuration
GET  /status     # Get compaction status for all conversations
POST /compact    # Manually trigger compaction (not fully implemented)
```

### Key Environment Variables

```bash
# llms may set these
LLMS_DISABLE=context_compaction  # Disable this extension
```

### Logging

```bash
# Extension logs to llms' logger
# View with llms serve --verbose or --debug
```

---

## Questions to Ask User

When helping users, consider asking:

1. **Hardware:** What GPU/VRAM do you have?
2. **Setup:** Using Ollama, cloud API, or mixed?
3. **Model:** What main model are you using?
4. **Goal:** Long conversations, cost reduction, or OOM prevention?
5. **Constraints:** Latency sensitive? Privacy concerns?

This helps recommend appropriate configuration.

---

## Contributing

See `CONTRIBUTING.md` for detailed contribution guidelines.

**Quick tips:**
- Start with issues labeled "good first issue"
- Ask questions before major changes
- Keep PRs focused and small
- Update docs with code changes

---

## Contact & Support

- **Repository:** https://github.com/konsumer/llms-extension-context_compaction
- **Issues:** https://github.com/konsumer/llms-extension-context_compaction/issues
- **Main llms:** https://github.com/ServiceStack/llms

---

## Version Info

Current version: 0.2.0 (unreleased)

See `CHANGELOG.md` for detailed version history.

---

*This guide was created to help AI assistants (like Claude, GPT, etc.) quickly understand the project and provide better assistance. Feel free to update as the project evolves!*
