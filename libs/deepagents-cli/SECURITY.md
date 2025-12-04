# Security Policy

## Human-in-the-Loop (HITL) Security Model

DeepAgents CLI implements a comprehensive Human-in-the-Loop (HITL) security model to ensure safe operation while maintaining productivity. This approach balances automation with user control, requiring explicit approval for potentially destructive operations.

## Security Architecture

### 1. Operation Classification

Operations are classified into three categories based on their potential impact:

#### Safe Operations (Auto-Approved)
- Reading files and directories
- Searching content
- Viewing system information
- Listing processes or resources
- Non-destructive queries

#### Requires Approval (HITL)
- **File Operations:**
  - Creating new files
  - Modifying existing files
  - Deleting files or directories
  - Moving or renaming files

- **Shell Commands:**
  - Installing packages (`pip install`, `npm install`, etc.)
  - System modifications (`apt-get`, `brew`, etc.)
  - Network operations (`curl`, `wget`, `ssh`, etc.)
  - Process management (`kill`, `pkill`, etc.)
  - Git operations with remote effects (`git push`, `git pull`, etc.)

- **Subagent Operations:**
  - Delegating tasks to specialized subagents
  - Spawning new agent instances
  - Cross-agent communication

#### Always Denied (Safety Guardrails)
- Operations attempting to bypass approval mechanisms
- Malformed or suspicious commands
- Operations outside project scope (when configured)
- Commands with shell injection patterns

### 2. Approval Mechanism

When an operation requires approval, the system:

1. **Pauses execution** before the operation
2. **Displays details** including:
   - Operation type and target
   - Full command or file changes (with diff preview)
   - Potential impact assessment
3. **Prompts for user decision:**
   - `y` (yes) - Approve this operation
   - `n` (no) - Reject this operation
   - `a` (all) - Approve this and all subsequent operations in session
   - `q` (quit) - Terminate the current task

### 3. Diff Previews

For file modifications, the system provides:
- **Unified diff format** showing exact changes
- **Syntax highlighting** for better readability
- **Line-by-line comparison** of before/after states
- **Context lines** to understand surrounding code

Example approval prompt:
```
╭─ Approval Required ─────────────────────────────────────╮
│ Operation: Edit File                                     │
│ Target: src/config.py                                    │
│                                                          │
│ Changes:                                                 │
│ --- src/config.py                                        │
│ +++ src/config.py                                        │
│ @@ -10,7 +10,7 @@                                        │
│ -DEBUG = False                                           │
│ +DEBUG = True                                            │
│                                                          │
│ Approve? [y/n/a/q]:                                      │
╰──────────────────────────────────────────────────────────╯
```

### 4. Session State Management

The system maintains session-level state for:
- **Approval mode:** Normal vs. Auto-approve-all
- **Operation history:** Track all approved/rejected operations
- **File modifications:** Maintain complete change log
- **Rollback capability:** Enable undo of recent changes

## API Key Security

### Environment Variables

API keys are managed through environment variables:
```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=AIza...
XAI_API_KEY=xai-...
TAVILY_API_KEY=tvly-...
```

### Best Practices

1. **Never commit API keys** to version control
2. **Use .env files** for local development (add to .gitignore)
3. **Rotate keys regularly** following provider recommendations
4. **Use separate keys** for development and production
5. **Monitor key usage** through provider dashboards

### Key Storage

- Keys are read from environment variables at runtime
- Never stored in configuration files or databases
- Never logged or displayed in output
- Never passed to subagents without explicit user approval

## Network Security

### Outbound Connections

The CLI makes outbound connections to:
- **LLM Provider APIs** (OpenAI, Anthropic, Google, xAI)
- **Web Search** (Tavily API)
- **User-approved URLs** (via `fetch_url` tool with approval)

### Sandbox Integrations

When using remote sandboxes (Modal, Runloop, Daytona):
- **Isolated execution environments** separate from host machine
- **Credential passthrough** only for explicitly approved operations
- **Network isolation** prevents unauthorized access
- **Resource limits** prevent abuse

## File System Security

### Project Scope

By default, operations are scoped to:
- Current working directory and subdirectories
- User home directory (with explicit approval)
- Temporary directories (for agent workspace)

### Restricted Paths

The following paths require extra confirmation:
- System directories (`/etc`, `/usr`, `/bin`, etc.)
- User configuration (`~/.ssh`, `~/.aws`, etc.)
- Other users' directories (if accessible)

### File Operation Tracking

All file operations are tracked with:
- **Timestamp** of operation
- **User approval** status
- **Full content diff** for modifications
- **Rollback information** for undo capability

## Skill System Security

### Progressive Disclosure

Skills are loaded progressively to:
- **Minimize attack surface** by limiting available capabilities
- **Reduce context window usage** for better performance
- **Enable gradual complexity** as needed

### Skill Permissions

Each skill declares:
- **Required tools** it needs access to
- **File paths** it may read or modify
- **External services** it may contact
- **Risk level** (low/medium/high)

Users can:
- **Review skill code** before enabling
- **Disable specific skills** per project
- **Audit skill usage** through logs

## Memory Security

### Agent Memory

The system maintains two types of memory:
1. **User-level** (`~/.config/deepagents/agent.md`)
   - Personal preferences
   - Cross-project knowledge
   - Skill configurations

2. **Project-level** (`.deepagents/agent.md`)
   - Project-specific context
   - Team conventions
   - Local configurations

### Memory Isolation

- Project memory cannot access user memory
- Different projects have isolated memory spaces
- Memory files are plain text for transparency
- Users can edit or delete memory at any time

## Reporting Security Issues

If you discover a security vulnerability:

1. **DO NOT** open a public issue
2. **Email** security concerns to the maintainers (see CONTRIBUTING.md)
3. **Include:**
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact assessment
   - Suggested fix (if available)

## Security Updates

Security patches are released as soon as possible after discovery:
- **Critical issues:** Same-day patch release
- **High severity:** Within 48 hours
- **Medium/Low severity:** Next regular release

Users are notified through:
- GitHub Security Advisories
- Release notes
- Project README updates

## Compliance

DeepAgents CLI is designed to operate safely in:
- **Enterprise environments** with security policies
- **Air-gapped networks** (with appropriate configuration)
- **Multi-user systems** with proper isolation
- **CI/CD pipelines** with controlled automation

## Audit Trail

The system maintains an audit trail of:
- All file modifications with timestamps
- Shell commands executed (approved and rejected)
- Tool invocations and parameters
- Agent decisions and reasoning
- User approvals and rejections

Audit logs are stored in `.deepagents/audit.log` (when enabled).

## Threat Model

### In-Scope Threats

✅ **Mitigated:**
- Accidental destructive operations
- Unintended file modifications
- Malicious prompt injection
- Unauthorized network access
- Credential leakage

### Out-of-Scope

❌ **User Responsibility:**
- Phishing attacks against user
- Compromised API keys
- Malicious code intentionally approved by user
- Host system vulnerabilities
- Physical access to machine

## Principle of Least Privilege

DeepAgents CLI operates under least privilege:
- **No elevated permissions** required for normal operation
- **Explicit approval** for privileged operations
- **Minimal dependencies** to reduce attack surface
- **Sandboxed execution** options for untrusted code

## Secure Development

Contributors must follow:
- **Code review** for all changes
- **Security linting** via Ruff and mypy
- **Dependency scanning** for vulnerabilities
- **Test coverage** including security scenarios

See CONTRIBUTING.md for detailed secure development practices.

---

**Last Updated:** 2025-12-03
**Security Contact:** See project maintainers
**Version:** 1.0
