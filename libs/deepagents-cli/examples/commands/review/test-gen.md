---
name: test-gen
description: Generate unit tests for code
aliases: [tests, gentest]
args:
  - name: target
    description: File or function to generate tests for
    required: true
  - name: framework
    description: Test framework (pytest, unittest, jest)
    required: false
    default: "pytest"
---

# Test Generation Request

Please generate {framework} unit tests for `{target}`.

## Test Coverage Requirements

### Happy Path Tests
- Test normal operation with valid inputs
- Cover the main use cases

### Edge Cases
- Empty inputs
- Boundary values
- Large inputs
- Special characters (for string handling)

### Error Cases
- Invalid inputs
- Missing required parameters
- Type errors
- Resource unavailable scenarios

## Test Structure

For each test:
1. Clear, descriptive test name following `test_<function>_<scenario>` pattern
2. Arrange: Set up test data and mocks
3. Act: Call the function under test
4. Assert: Verify expected outcomes

## Framework-Specific Guidelines

### pytest ({framework})
- Use fixtures for common setup
- Use parametrize for similar tests with different inputs
- Use pytest.raises for exception testing
- Include conftest.py suggestions if needed

### unittest
- Use setUp/tearDown methods
- Use assertRaises for exceptions
- Organize in TestCase classes

### jest
- Use describe/it blocks
- Use beforeEach/afterEach
- Use expect().toThrow() for exceptions

## Output

Please provide:
1. Complete test file with all tests
2. Any fixtures or mocks needed
3. Instructions for running the tests
4. Estimated test coverage
