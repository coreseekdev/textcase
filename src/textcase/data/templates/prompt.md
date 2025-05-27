# {{ name }} Prompt Template

## Description
{{ description | default("A prompt template for LLM interactions") }}

## Parameters
{% if parameters %}
{% for param_name, param_desc in parameters.items() %}
- `{{ param_name }}`: {{ param_desc }}
{% endfor %}
{% else %}
- No parameters defined
{% endif %}

## Prompt Template
```
{{ content | default("Your prompt content goes here.") }}
```

## Usage Notes
{{ usage_notes | default("Add usage notes here.") }}
