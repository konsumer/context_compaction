# Contributing to Context Compaction Extension

Thank you for your interest in contributing! This document provides guidelines and information for contributors.

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/konsumer/llms-extension-context_compaction.git
   cd llms-extension-context_compaction
   ```

2. **Install for development**
   ```bash
   # Link to llms extensions directory
   ln -s $(pwd) ~/.llms/extensions/context_compaction
   ```

3. **Test your changes**
   ```bash
   python test_extension.py
   ```

## Testing

### Unit Tests
Run the test script to verify basic functionality:
```bash
python test_extension.py
```

### Integration Tests
Test with a real llms server:
```bash
# Start llms with the extension
llms serve --context-compaction-threshold 0.7

# In another terminal, test the API
curl http://localhost:8000/ext/context_compaction/status
```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where appropriate
- Add docstrings to functions and classes
- Keep functions focused and single-purpose

## Making Changes

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write clear, focused commits
   - Add tests if applicable
   - Update documentation

3. **Test thoroughly**
   - Run the test script
   - Test with real llms server
   - Check different models and providers

4. **Submit a pull request**
   - Describe what your changes do
   - Reference any related issues
   - Include test results

## Areas for Contribution

### High Priority

- **Configuration File Support**: Load config from `~/.llms/extensions/context_compaction/config.json`
- **Better Context Tracking**: Improve conversation ID generation for better tracking
- **Token Counting**: Use actual tokenizers instead of estimating context limits
- **Summary Caching**: Cache summaries to avoid regenerating
- **UI Dashboard**: Add a web UI to monitor and control compaction

### Medium Priority

- **Smart Summarization**: Use different strategies based on conversation type
- **Partial Compaction**: Keep recent messages, only summarize older ones
- **Multi-Stage Summaries**: Create hierarchical summaries for very long conversations
- **Custom Filters**: Allow users to filter what gets summarized
- **Metrics**: Track compaction efficiency and quality

### Low Priority

- **Compression Strategies**: Experiment with different history replacement strategies
- **Model-Specific Tuning**: Optimize for different model families
- **Performance Optimization**: Reduce latency during compaction
- **Advanced Configuration**: Per-conversation settings, rules, etc.

## Architecture

### Core Components

1. **Configuration** (`CompactionConfig`)
   - Stores extension settings
   - Updated via CLI args and API

2. **Request Filter** (`on_request`)
   - Checks if compaction is needed
   - Applies compaction before sending to LLM
   - Modifies message history

3. **Response Filter** (`on_response`)
   - Monitors token usage
   - Flags conversations for compaction
   - Updates conversation state

4. **Compaction Logic** (`compact_conversation`)
   - Generates summaries using LLM
   - Formats conversation for summarization
   - Handles errors gracefully

5. **API Endpoints**
   - `/config`: Get/update configuration
   - `/status`: Monitor conversation state
   - `/compact`: Manually trigger compaction

### Data Flow

```
Incoming Request
    ↓
on_request() → Check if compaction needed
    ↓
[Compact if needed]
    ↓
Send to LLM
    ↓
Response
    ↓
on_response() → Monitor usage
    ↓
[Flag for compaction if threshold exceeded]
    ↓
Return Response
```

## Common Issues

### "Summary generation failed"
- Check that the summarization provider/model is accessible
- Verify API keys are configured
- Try a different model

### "Compaction not triggering"
- Verify usage is actually exceeding threshold
- Check logs for context calculations
- Ensure extension is enabled

### "Conversation state not persisting"
- Conversation IDs are session-based
- State resets on server restart
- Consider implementing persistence

## Questions?

- Open an issue for questions
- Tag issues with `question` label
- Check existing issues first

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
