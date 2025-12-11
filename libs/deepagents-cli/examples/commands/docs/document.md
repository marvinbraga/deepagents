---
name: document
description: Generate documentation for code
aliases: [doc, docs]
args:
  - name: target
    description: File or function to document
    required: true
  - name: style
    description: Documentation style (docstring, markdown, jsdoc)
    required: false
    default: "docstring"
---

# Documentation Request

Please generate {style}-style documentation for `{target}`.

## Requirements

### For Functions/Methods:
- Brief description of purpose
- List all parameters with types and descriptions
- Return value type and description
- Exceptions/errors that can be raised
- Usage example

### For Classes:
- Class purpose and responsibility
- Constructor parameters
- Public methods with brief descriptions
- Class attributes
- Inheritance information if applicable
- Usage example

### For Modules/Files:
- Module purpose
- Main exports/public API
- Dependencies
- Usage examples

## Style Guidelines

- Keep descriptions concise but complete
- Use type hints where applicable
- Include edge cases in examples
- Follow project conventions

## Output Format

Please provide:
1. The documentation in the requested format ({style})
2. Suggestions for any code improvements that would make documentation clearer
3. Any missing edge cases that should be documented
