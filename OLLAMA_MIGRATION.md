# Migration from Anthropic to Ollama

This document explains the changes made to replace the Anthropic Claude API with a local LLM using Ollama.

## Why This Change?

### Benefits of Local LLM via Ollama

1. **Privacy**: All AI processing happens locally on your machine. No data is sent to external APIs.
2. **Cost**: Zero API costs. Unlimited usage without any charges.
3. **Speed**: Once the model is cached, inference is typically faster than API calls.
4. **Reliability**: No internet dependency required for AI features.
5. **Flexibility**: Easy to switch between different models based on your needs.
6. **Transparency**: You have full control and visibility into the AI model being used.

## What Changed?

### Code Changes

**`eduguard/daemon/ai_classifier.py`**
- Replaced Anthropic client with Ollama client
- Updated API calls to use Ollama's chat interface
- Improved JSON parsing with fallback to simple text parsing
- Added connection testing on initialization

### Configuration Changes

**`eduguard/config/eduguard.yaml`**
```yaml
# Before
ai:
  api_key: ""
  model: claude-sonnet-4-6

# After
ai:
  model: llama3.2:3b
  ollama_host: http://localhost:11434
```

**`eduguard.service`**
- Removed `ANTHROPIC_API_KEY` environment variable

### Dependencies

**requirements.txt / setup.py**
```diff
- anthropic>=0.18.0
+ ollama>=0.3.0
```

## Installation

### 1. Install Ollama

```bash
curl -fsSL https://ollama.ai/install.sh | sh
```

### 2. Download a Model

Choose one of these models:

**Llama 3.2 3B** (Recommended for most users)
```bash
ollama pull llama3.2:3b
```

**Mistral 7B** (For better accuracy, requires more resources)
```bash
ollama pull mistral:7b
```

**TinyLlama 1.1B** (For very limited hardware)
```bash
ollama pull tinyllama:1.1b
```

### 3. Update EduGuard

```bash
cd /opt/eduguard
sudo ./venv/bin/pip install -e .
sudo systemctl restart eduguard
```

## Model Comparison

| Model | Size | Speed | Accuracy | Best For |
|-------|------|-------|----------|----------|
| **Llama 3.2 3B** | 2GB | Very Fast | Good | General use (recommended) |
| **Mistral 7B** | 4.1GB | Moderate | Excellent | Maximum accuracy |
| **Qwen2.5 3B** | 2GB | Very Fast | Good | Alternative to Llama |
| **TinyLlama 1.1B** | 637MB | Fastest | Basic | Limited hardware |

## Switching Models

1. Download the new model:
   ```bash
   ollama pull mistral:7b
   ```

2. Update configuration:
   ```bash
   sudo nano /etc/eduguard/eduguard.yaml
   ```

   Change the model line:
   ```yaml
   ai:
     model: mistral:7b
   ```

3. Reload the daemon:
   ```bash
   sudo systemctl reload eduguard
   ```

## Troubleshooting

### Check Ollama is Running

```bash
sudo systemctl status ollama
curl http://localhost:11434/api/tags
```

### Test AI Classification

```bash
# Test Ollama directly
ollama run llama3.2:3b "Is example.com appropriate for children?"

# Check EduGuard logs
sudo grep -i "ollama" /var/log/eduguard/eduguard.log
```

### Common Issues

**"Could not connect to Ollama"**
```bash
sudo systemctl start ollama
sudo systemctl enable ollama
```

**"Model not found"**
```bash
ollama list  # Check installed models
ollama pull llama3.2:3b  # Download if missing
```

**Performance issues**
- Switch to a smaller model (tinyllama:1.1b)
- Ensure sufficient RAM (at least 4GB free)
- Check CPU usage during classification

## API Differences

### Before (Anthropic)

```python
message = self.client.messages.create(
    model=self.model,
    max_tokens=256,
    messages=[{"role": "user", "content": prompt}]
)
response_text = message.content[0].text
```

### After (Ollama)

```python
response = self.client.chat(
    model=self.model,
    messages=[{'role': 'user', 'content': prompt}],
    options={
        'temperature': 0.3,
        'num_predict': 256,
    }
)
response_text = response['message']['content']
```

## Backward Compatibility

This change is **not backward compatible** with the Anthropic implementation. If you need to revert:

1. Restore the old `ai_classifier.py` file
2. Update dependencies back to `anthropic>=0.18.0`
3. Set `ANTHROPIC_API_KEY` environment variable
4. Update config to use `claude-sonnet-4-6` model

## Performance Notes

- First classification request may be slower as the model loads into memory
- Subsequent requests are typically very fast (< 1 second)
- Memory usage: Model size + ~500MB overhead
- CPU usage: Varies by model size and hardware

## Security Considerations

- All AI processing happens locally
- No data leaves your machine
- No API keys to secure (except Flask secret)
- Same privacy guarantees as the rest of EduGuard

## Support

For issues related to:
- **Ollama**: Visit https://github.com/ollama/ollama
- **EduGuard**: File an issue in the EduGuard repository
- **Models**: Check model-specific documentation at https://ollama.ai/library
