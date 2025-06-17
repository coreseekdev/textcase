# LLM Providers

This directory contains the LLM provider implementations for the TextCase project.

## Available Providers

### 1. HumbugProvider (`humbug_provider.py`)

The original provider implementation based on the Humbug AI library.

**Features:**
- Full integration with Humbug AI library
- Advanced conversation management
- Rich metadata support
- GUI components (may cause Qt conflicts)

**Usage:**
```yaml
# In provider configuration
type: humbug
api_key: ${API_KEY}
api_base: ${API_BASE}
models:
  - gpt-4o
  - claude-3-5-sonnet
```

### 2. AIOHttpLLMProvider (`aiohttp_provider.py`)

A lightweight alternative provider using standard HTTP clients.

**Features:**
- No Qt dependencies (avoids GUI conflicts)
- Uses aiohttp for HTTP requests
- Compatible with OpenAI API format
- Supports both sync and streaming responses
- Lightweight and fast

**Usage:**
```yaml
# In provider configuration
type: aiohttp
api_key: ${API_KEY}
api_base: ${API_BASE}
models:
  gpt-4o:
    max_tokens: 4096
    context_window: 128000
  claude-3-5-sonnet-20241022:
    max_tokens: 8192
    context_window: 200000
```

## When to Use Which Provider

### Use HumbugProvider when:
- You need advanced conversation management features
- You're using Humbug-specific functionality
- Qt dependencies are not a concern
- You need the full feature set of the Humbug library

### Use AIOHttpLLMProvider when:
- You want to avoid Qt dependencies
- You need a lightweight, fast provider
- You're working in environments where GUI libraries cause conflicts
- You only need basic LLM API interactions
- You want better control over HTTP requests

## Configuration

Both providers support similar configuration formats:

```yaml
# Common configuration structure
type: humbug|aiohttp
api_key: ${API_KEY}        # Environment variable
api_base: ${API_BASE}      # API endpoint URL
api_version: v1            # Optional, defaults to 'v1'

# Models can be specified as a list or dictionary
models:
  model-name:
    max_tokens: 4096
    context_window: 128000
```

## Environment Variables

Set these environment variables for your API credentials:

```bash
# For OpenAI
export API_KEY="sk-your-openai-key"
export API_BASE="https://api.openai.com/v1"

# For Anthropic
export API_KEY="sk-ant-your-anthropic-key"
export API_BASE="https://api.anthropic.com"

# For DeepSeek
export API_KEY="sk-your-deepseek-key"
export API_BASE="https://api.deepseek.com"
```

## Factory Registration

Both providers are automatically registered in the `LLMFactory`:

```python
from textcase.core.llm import LLMFactory

factory = LLMFactory()

# Create Humbug provider
humbug_provider = factory.create_provider('humbug', config)

# Create AIOHttp provider
aiohttp_provider = factory.create_provider('aiohttp', config)
```

## Dependencies

### HumbugProvider Dependencies:
- `humbug` (from custom Git repository)
- Qt libraries (indirect dependency)

### AIOHttpLLMProvider Dependencies:
- `aiohttp` (already included in pyproject.toml)
- Standard library modules only

## Migration Guide

To migrate from HumbugProvider to AIOHttpLLMProvider:

1. Update your provider configuration:
   ```yaml
   # Change this:
   type: humbug
   
   # To this:
   type: aiohttp
   ```

2. Ensure your API endpoints are compatible with OpenAI format

3. Test your configuration with the new provider

4. Update any code that relies on Humbug-specific features

The migration should be seamless for most use cases, as both providers implement the same `LLMProvider` interface.