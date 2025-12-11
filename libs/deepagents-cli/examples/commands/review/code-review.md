---
name: code-review
description: Perform a comprehensive code review
aliases: [review, cr]
args:
  - name: target
    description: File or directory to review
    required: false
    default: "."
  - name: focus
    description: Focus area (security, performance, style, all)
    required: false
    default: "all"
---

# Code Review Request

Please perform a comprehensive code review of `{target}` with focus on **{focus}**.

## Review Checklist

### Code Quality
- [ ] Code follows project conventions and style guides
- [ ] Functions/methods have single responsibility
- [ ] No code duplication (DRY principle)
- [ ] Meaningful variable and function names

### Security (if focus includes security)
- [ ] No hardcoded credentials or secrets
- [ ] Input validation present
- [ ] No SQL injection vulnerabilities
- [ ] No XSS vulnerabilities
- [ ] Proper authentication/authorization

### Performance (if focus includes performance)
- [ ] No obvious performance bottlenecks
- [ ] Efficient algorithms used
- [ ] No unnecessary database queries
- [ ] Proper caching where applicable

### Testing
- [ ] Unit tests present and passing
- [ ] Edge cases covered
- [ ] Test coverage adequate

## Instructions

1. Read the target files thoroughly
2. Identify issues in order of severity (critical > major > minor)
3. Provide specific line references for each issue
4. Suggest concrete fixes with code examples
5. Highlight any positive patterns worth maintaining

Format your response as:
- **Critical Issues**: Must be fixed before merge
- **Major Issues**: Should be fixed soon
- **Minor Issues**: Nice to have improvements
- **Positive Notes**: Good practices to continue
