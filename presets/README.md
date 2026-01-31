# Preset Configurations

This directory contains preset configurations for common use cases. Copy the appropriate preset to `~/.llms/extensions/context_compaction/config.json` to use it.

## Available Presets

### Ollama Presets

#### `ollama-4gb.json` - For 4-6GB VRAM GPUs
- **Hardware**: RTX 3050, GTX 1660, etc.
- **Settings**: Aggressive compaction (60%), fast model (phi3:mini), simple prompt
- **Use case**: Memory-constrained environments

```bash
cp presets/ollama-4gb.json ~/.llms/extensions/context_compaction/config.json
ollama pull phi3:mini
```

#### `ollama-8gb.json` - For 6-8GB VRAM GPUs
- **Hardware**: RTX 4060 Ti, RTX 3060 (8GB), etc.
- **Settings**: Balanced compaction (70%), fast model (llama3.2:3b), simple prompt
- **Use case**: Most common Ollama setups

```bash
cp presets/ollama-8gb.json ~/.llms/extensions/context_compaction/config.json
ollama pull llama3.2:3b
```

### Cloud API Presets

#### `openai.json` - For OpenAI API
- **Settings**: Standard compaction (80%), gpt-4o-mini for summaries
- **Cost**: ~$0.15 per million tokens (very cheap)
- **Use case**: Cost-effective cloud summaries

```bash
cp presets/openai.json ~/.llms/extensions/context_compaction/config.json
```

#### `anthropic.json` - For Anthropic API
- **Settings**: High threshold (85%), Claude Haiku for summaries
- **Cost**: Efficient for large contexts
- **Use case**: High-quality summaries with massive context windows

```bash
cp presets/anthropic.json ~/.llms/extensions/context_compaction/config.json
```

## Customization

After copying a preset, you can customize it:

```bash
# Edit the config file
nano ~/.llms/extensions/context_compaction/config.json

# Or update via API
curl -X POST http://localhost:8000/ext/context_compaction/config \
  -H "Content-Type: application/json" \
  -d '{"threshold": 0.75}'
```

## Creating Custom Presets

1. Start with a preset that's closest to your needs
2. Copy it to a new file
3. Adjust the settings
4. Test with your specific use case
5. Share it with the community!

## Preset Selection Guide

| Your Setup | Recommended Preset | Why |
|-----------|-------------------|-----|
| Ollama + 4GB GPU | `ollama-4gb.json` | Aggressive memory management |
| Ollama + 8GB GPU | `ollama-8gb.json` | Balanced performance |
| Ollama + 12GB+ GPU | Customize `ollama-8gb.json` | Raise threshold to 0.85, use llama3.1:8b |
| OpenAI API | `openai.json` | Cost-effective cloud option |
| Anthropic API | `anthropic.json` | Best for huge contexts |
| Mixed (Ollama + Cloud) | `openai.json` | Use cloud for summaries only |

## Need Help?

See the main README.md for detailed documentation, or OLLAMA_GUIDE.md for Ollama-specific guidance.
