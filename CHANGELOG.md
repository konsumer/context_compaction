# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- **BREAKING**: Removed CLI arguments in favor of config file
- Configuration now loaded from `~/.llms/extensions/context_compaction/config.json`
- Config file is automatically created with defaults if it doesn't exist
- API config updates are now persisted to the config file
- Better integration with llms' extension system
- **Context limit detection now uses real provider metadata** instead of hardcoded estimates

### Added
- Configuration file support with automatic persistence
- `load_config()` and `save_config()` functions for config management
- `get_model_context_limit()` - retrieves actual context limits from llms provider API
- Integration with llms' provider metadata system via `ctx.get_provider()` and `provider.model_info()`
- Support for all 530+ models across 24 providers with accurate context limits
- Automatic updates as llms' model database is refreshed (daily from models.dev)
- **User notifications** - Optional in-conversation notices when compaction occurs (`notify_user` config)
- **Simple prompt mode** - Fast, brief summarization for resource-constrained environments (`use_simple_prompt` config)
- **Preset configurations** - Ready-to-use configs in `presets/` directory:
  - `ollama-4gb.json` - For 4-6GB VRAM GPUs (aggressive compaction)
  - `ollama-8gb.json` - For 6-8GB VRAM GPUs (balanced)
  - `openai.json` - For OpenAI API users
  - `anthropic.json` - For Anthropic API users
- **Ollama guide** - Comprehensive documentation in `OLLAMA_GUIDE.md` including:
  - Hardware-specific recommendations
  - Model suggestions by VRAM capacity
  - Performance comparisons
  - Troubleshooting for OOM errors
  - Configuration examples

### Improved
- Context limit accuracy - now uses real data from `providers.json` instead of guessing
- Fallback estimates only used when provider metadata is unavailable
- Better logging for context limit retrieval
- User experience - notifications keep users informed about compaction
- Performance for local models - simple prompt mode reduces latency
- Documentation - specific guidance for resource-constrained hardware

### Removed
- `__parser__` hook and all CLI arguments (use config file instead)
- `estimate_context_limit()` - replaced with `get_model_context_limit()` using real data

### Planned
- Persistent conversation state
- UI dashboard for monitoring
- Actual tokenization instead of estimates
- Summary caching
- Per-conversation configuration
- Metrics and analytics

## [0.1.0] - 2026-01-31

### Added
- Initial release
- Automatic context monitoring via response filters
- Configurable compaction threshold (default 80%)
- Request filter for automatic history compaction
- Summarization using any configured provider/model
- CLI arguments for configuration
- RESTful API endpoints:
  - GET /ext/context_compaction/config
  - POST /ext/context_compaction/config
  - GET /ext/context_compaction/status
  - POST /ext/context_compaction/compact
- Context limit estimation for common models:
  - OpenAI (GPT-4, GPT-3.5)
  - Anthropic (Claude 2, Claude 3)
  - Local models (Llama, Mistral)
- Conversation tracking and state management
- Smart history replacement:
  - Preserves system messages
  - Keeps recent messages for continuity
  - Inserts summary in conversation flow
- Comprehensive documentation:
  - README with usage examples
  - ARCHITECTURE document
  - CONTRIBUTING guidelines
- Test script for development
- MIT License

### Features
- Monitor token usage in real-time
- Automatic compaction when threshold is reached
- Customizable summary prompt
- Support for any LLM provider/model
- No external dependencies beyond llms
- Session-scoped conversation tracking

### Known Limitations
- Context limits are estimates, not exact
- Conversation state is in-memory only (not persistent)
- Conversation IDs are session-scoped
- No authentication on API endpoints
- Summary generation is synchronous (adds latency)
- No UI dashboard yet

[Unreleased]: https://github.com/konsumer/llms-extension-context_compaction/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/konsumer/llms-extension-context_compaction/releases/tag/v0.1.0
