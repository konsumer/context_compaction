# Ollama Setup Guide for Context Compaction

This guide is specifically for users running llms with Ollama on resource-constrained hardware.

## Why Context Compaction Matters for Ollama

Local models running on GPUs with limited VRAM (like the RTX 4060 Ti 8GB) can run out of memory during long conversations. Context compaction helps by:

- Reducing memory usage by summarizing old messages
- Enabling longer conversations without restarting
- Preventing out-of-memory errors
- Improving response times by reducing context size

## Recommended Configuration for Ollama

### Basic Setup (8GB VRAM)

```json
{
  "enabled": true,
  "threshold": 0.7,
  "provider": "ollama",
  "model": "llama3.2:3b",
  "notify_user": true,
  "use_simple_prompt": true
}
```

**Why these settings?**
- `threshold: 0.7` - Trigger earlier (70%) to avoid OOM errors
- `model: "llama3.2:3b"` - Small, fast model for summaries (uses ~2GB VRAM)
- `use_simple_prompt: true` - Simpler prompt = faster summaries

### Performance-Optimized (4-6GB VRAM)

```json
{
  "enabled": true,
  "threshold": 0.6,
  "provider": "ollama",
  "model": "phi3:mini",
  "notify_user": true,
  "use_simple_prompt": true
}
```

**For very limited memory:**
- `threshold: 0.6` - Compact earlier to stay safe
- `model: "phi3:mini"` - Tiny model (~2GB VRAM)
- Lower thresholds mean more frequent compaction but safer memory usage

### Quality-Focused (12GB+ VRAM)

```json
{
  "enabled": true,
  "threshold": 0.8,
  "provider": "ollama",
  "model": "llama3.1:8b",
  "notify_user": true,
  "use_simple_prompt": false
}
```

**For better summaries on higher-end cards:**
- `threshold: 0.8` - More context before compaction
- `model: "llama3.1:8b"` - Better quality summaries
- `use_simple_prompt: false` - Detailed summaries

## Recommended Ollama Models for Summarization

Choose based on your available VRAM:

| Model | VRAM Usage | Speed | Quality | Best For |
|-------|-----------|-------|---------|----------|
| `phi3:mini` | ~2GB | Very Fast | Good | 4-6GB cards |
| `llama3.2:3b` | ~2GB | Very Fast | Good | 6-8GB cards |
| `gemma2:2b` | ~2GB | Very Fast | Good | 4-6GB cards |
| `qwen2:1.5b` | ~1.5GB | Fastest | Fair | Ultra-limited VRAM |
| `llama3.1:8b` | ~5GB | Fast | Excellent | 12GB+ cards |
| `mistral:7b` | ~4GB | Fast | Very Good | 10GB+ cards |

**Important:** The summarization model runs **in addition to** your main conversation model, so ensure you have enough VRAM for both.

## Installation

1. Install the extension:
```bash
mkdir -p ~/.llms/extensions
cp -r /path/to/llms-extension-context_compaction ~/.llms/extensions/context_compaction
```

2. Create your config file:
```bash
mkdir -p ~/.llms/extensions/context_compaction
cat > ~/.llms/extensions/context_compaction/config.json <<'EOF'
{
  "enabled": true,
  "threshold": 0.7,
  "provider": "ollama",
  "model": "llama3.2:3b",
  "notify_user": true,
  "use_simple_prompt": true
}
EOF
```

3. Pull the summarization model:
```bash
ollama pull llama3.2:3b
```

4. Start llms:
```bash
llms serve
```

## Usage Tips

### Monitor Memory Usage

Watch your GPU memory while chatting:
```bash
# NVIDIA GPUs
watch -n 1 nvidia-smi

# Or in another terminal
nvtop
```

### Adjust Threshold Dynamically

If you're approaching VRAM limits, lower the threshold via API:
```bash
curl -X POST http://localhost:8000/ext/context_compaction/config \
  -H "Content-Type: application/json" \
  -d '{"threshold": 0.5}'
```

### Check Compaction Status

See when compaction will trigger:
```bash
curl http://localhost:8000/ext/context_compaction/status
```

### Test Different Models

Try different summarization models to find the best speed/quality trade-off:
```bash
# Pull alternatives
ollama pull phi3:mini
ollama pull gemma2:2b

# Update config to test
curl -X POST http://localhost:8000/ext/context_compaction/config \
  -H "Content-Type: application/json" \
  -d '{"model": "phi3:mini"}'
```

## Troubleshooting

### Out of Memory Errors

**Symptoms:** CUDA OOM errors, llms crashes, or Ollama errors

**Solutions:**
1. Lower the threshold: `{"threshold": 0.5}` or even `0.4`
2. Use a smaller summarization model: `phi3:mini` or `qwen2:1.5b`
3. Enable simple prompt: `{"use_simple_prompt": true}`
4. Close other GPU applications
5. Consider quantized models (Q4 or Q5 versions)

### Compaction Too Slow

**Symptoms:** Long pauses during conversation

**Solutions:**
1. Use a faster model: `llama3.2:3b`, `phi3:mini`, or `gemma2:2b`
2. Enable simple prompt: `{"use_simple_prompt": true}`
3. Use quantized versions of models
4. Increase threshold to compact less often: `{"threshold": 0.85}`

### Summaries Losing Important Context

**Symptoms:** The model "forgets" important details after compaction

**Solutions:**
1. Disable simple prompt: `{"use_simple_prompt": false}`
2. Use a better summarization model: `llama3.1:8b` or `mistral:7b`
3. Increase threshold to keep more context: `{"threshold": 0.9}`
4. Customize the prompt to emphasize what's important

### Compaction Not Triggering

**Symptoms:** Long conversations but no compaction occurs

**Check:**
1. Is compaction enabled? `curl http://localhost:8000/ext/context_compaction/config`
2. Check the status: `curl http://localhost:8000/ext/context_compaction/status`
3. Verify the model's context limit is being detected in logs
4. Try lowering the threshold: `{"threshold": 0.6}`

## Performance Comparison

Based on testing with RTX 4060 Ti 8GB:

| Configuration | Summary Time | Memory Usage | Quality |
|--------------|--------------|--------------|---------|
| phi3:mini + simple | ~2-3s | Low (~2GB) | Good |
| llama3.2:3b + simple | ~3-4s | Low (~2GB) | Very Good |
| llama3.2:3b + detailed | ~5-7s | Low (~2GB) | Excellent |
| mistral:7b + detailed | ~8-12s | Medium (~4GB) | Excellent |

## Example Workflow

**Typical session on 8GB GPU:**

1. Start conversation with main model (e.g., `llama3.1:8b` using ~5GB)
2. Chat normally until context reaches ~70% (summarization model needs ~2GB)
3. Compaction triggers automatically
4. Summary generated by `llama3.2:3b` (takes 3-4 seconds)
5. Context reduced by 60-80%
6. Continue conversation with more available memory
7. Repeat as needed

## Advanced Configuration

### Custom Prompts for Code Projects

```json
{
  "summary_prompt": "Summarize this coding conversation. Focus on:\n- Files and functions discussed\n- Code changes made\n- Current bugs or issues\n- Next steps\nKeep it under 200 tokens."
}
```

### Memory-Critical Setup

For absolute minimum VRAM usage:
```json
{
  "enabled": true,
  "threshold": 0.5,
  "provider": "ollama",
  "model": "qwen2:1.5b",
  "notify_user": true,
  "use_simple_prompt": true,
  "simple_prompt": "Briefly summarize: what was discussed, what was decided, what's next."
}
```

### Disable Notifications

If you don't want to see compaction notices:
```json
{
  "notify_user": false
}
```

## Recommended Preset by Hardware

**RTX 3060 (12GB):**
```bash
echo '{"enabled": true, "threshold": 0.8, "provider": "ollama", "model": "llama3.1:8b", "notify_user": true, "use_simple_prompt": false}' > ~/.llms/extensions/context_compaction/config.json
```

**RTX 4060 Ti (8GB):**
```bash
echo '{"enabled": true, "threshold": 0.7, "provider": "ollama", "model": "llama3.2:3b", "notify_user": true, "use_simple_prompt": true}' > ~/.llms/extensions/context_compaction/config.json
```

**RTX 3050 (4GB):**
```bash
echo '{"enabled": true, "threshold": 0.6, "provider": "ollama", "model": "phi3:mini", "notify_user": true, "use_simple_prompt": true}' > ~/.llms/extensions/context_compaction/config.json
```

**High-End (16GB+):**
```bash
echo '{"enabled": true, "threshold": 0.85, "provider": "ollama", "model": "mistral:7b", "notify_user": true, "use_simple_prompt": false}' > ~/.llms/extensions/context_compaction/config.json
```

## Contributing

Found a configuration that works well for your hardware? Share it in the GitHub issues!

## Support

- GitHub Issues: https://github.com/konsumer/llms-extension-context_compaction/issues
- Main llms Issues: https://github.com/ServiceStack/llms/issues
