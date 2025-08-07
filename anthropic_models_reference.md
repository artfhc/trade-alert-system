# Anthropic Claude Models Reference

## Available Models for ANTHROPIC_MODEL Configuration

### **Claude 3.5 Sonnet (Recommended for Trading)**
```bash
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022  # Latest version (default)
ANTHROPIC_MODEL=claude-3-5-sonnet-20240620  # Previous version
```
- **Best for**: Structured data extraction, JSON parsing, financial analysis
- **Strengths**: High accuracy, consistent output, good at following schemas
- **Cost**: Mid-tier pricing
- **Speed**: Fast (~2-3 seconds)

### **Claude 3 Opus (Highest Quality)**
```bash
ANTHROPIC_MODEL=claude-3-opus-20240229
```
- **Best for**: Complex reasoning, edge case handling
- **Strengths**: Highest accuracy and reasoning capability
- **Cost**: Most expensive
- **Speed**: Slower (~5-8 seconds)

### **Claude 3 Haiku (Fastest & Cheapest)**
```bash
ANTHROPIC_MODEL=claude-3-haiku-20240307
```
- **Best for**: Simple classification, high-volume processing
- **Strengths**: Very fast and cheap
- **Cost**: Lowest cost
- **Speed**: Fastest (~1-2 seconds)

## Configuration Examples

### **For Production Trading (Recommended)**
```bash
ANTHROPIC_MODEL=claude-3-5-sonnet-20241022
ANTHROPIC_MAX_TOKENS=1000
ANTHROPIC_TEMPERATURE=0.1  # Low for consistent parsing
```

### **For High-Volume Processing**
```bash
ANTHROPIC_MODEL=claude-3-haiku-20240307
ANTHROPIC_MAX_TOKENS=800
ANTHROPIC_TEMPERATURE=0.0  # Deterministic
```

### **For Complex Trading Logic**
```bash
ANTHROPIC_MODEL=claude-3-opus-20240229
ANTHROPIC_MAX_TOKENS=1500
ANTHROPIC_TEMPERATURE=0.1
```

## Parameter Guidelines

### **ANTHROPIC_MAX_TOKENS**
- **500-800**: Simple classification
- **1000**: Standard trade extraction (default)
- **1500+**: Complex multi-trade emails

### **ANTHROPIC_TEMPERATURE**
- **0.0**: Completely deterministic (same input → same output)
- **0.1**: Very consistent with slight variation (default for trading)
- **0.3**: More creative but less predictable
- **1.0**: Maximum creativity (not recommended for financial data)

## Model Selection for Trading

**For Email Trade Classification:**
- ✅ **claude-3-5-sonnet-20241022** (best balance)
- ✅ **claude-3-haiku-20240307** (if cost is a concern)
- ⚠️ **claude-3-opus-20240229** (overkill but highest accuracy)

**Temperature for Financial Data:**
- ✅ **0.0-0.2** (recommended for trading)
- ⚠️ **0.3+** (too unpredictable for financial decisions)