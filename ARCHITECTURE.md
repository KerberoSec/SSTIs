# Architecture Overview

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Docker Container                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │  Non-root User: museum (UID 1000)                      │ │
│  │  Resource Limits: 0.5 CPU, 256MB RAM                   │ │
│  │  Network: Isolated (internal bridge only)              │ │
│  │  Security: No new privileges, all capabilities dropped │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────┐                │
│  │         Flask Application               │                │
│  │  ┌───────────────────────────────────┐  │                │
│  │  │  Routes:                          │  │                │
│  │  │  - /                (index)       │  │                │
│  │  │  - /register        (auth)        │  │                │
│  │  │  - /login           (auth)        │  │                │
│  │  │  - /logout          (auth)        │  │                │
│  │  │  - /preview         (SSTI vuln)   │  │                │
│  │  │  - /simulated-shells (docs)       │  │                │
│  │  └───────────────────────────────────┘  │                │
│  │                                          │                │
│  │  ┌───────────────────────────────────┐  │                │
│  │  │  RestrictedSandbox                │  │                │
│  │  │  ├─ Whitelisted Globals:          │  │                │
│  │  │  │  - get_museum_meta()           │  │                │
│  │  │  │  - get_curator_note()          │  │                │
│  │  │  ├─ Whitelisted Filters:          │  │                │
│  │  │  │  - escape                      │  │                │
│  │  │  │  - upper                       │  │                │
│  │  │  └─ Blocked Attributes:           │  │                │
│  │  │     - __class__, __mro__, etc.    │  │                │
│  │  └───────────────────────────────────┘  │                │
│  └─────────────────────────────────────────┘                │
│                                                               │
│  ┌─────────────────────────────────────────┐                │
│  │         SQLite Database                 │                │
│  │         /tmp/museum.db                  │                │
│  │  ┌───────────────────────────────────┐  │                │
│  │  │  Table: users                     │  │                │
│  │  │  - id (PRIMARY KEY)               │  │                │
│  │  │  - username (UNIQUE)              │  │                │
│  │  │  - password_hash                  │  │                │
│  │  │  - display_name (SSTI injection)  │  │                │
│  │  │  - flag (UNIQUE per user)         │  │                │
│  │  └───────────────────────────────────┘  │                │
│  └─────────────────────────────────────────┘                │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

### User Registration
```
User Input (display_name)
    ↓
Stored in SQLite (no sanitization - intentional vulnerability)
    ↓
Unique flag generated: FLAG{username_<random>}
    ↓
User created with session
```

### SSTI Exploitation Flow
```
User logs in
    ↓
Session created
    ↓
User navigates to /preview
    ↓
display_name retrieved from database
    ↓
display_name rendered as Jinja2 template
    ↓
RestrictedSandbox processes template
    ↓
├─ Whitelisted helpers: ✅ Execute
├─ Whitelisted filters:  ✅ Execute
├─ Dangerous attributes: ❌ Blocked
└─ Builtins/config:      ❌ Blocked
    ↓
Rendered HTML returned to user
```

## Security Layers

### Layer 1: Template Sandbox
- **Purpose**: Limit template engine capabilities
- **Implementation**: Custom `RestrictedSandbox` class
- **Protections**:
  - Blocks attribute access to dangerous objects
  - Only allows explicitly whitelisted helpers
  - No access to Python builtins
  - No access to Flask internals (config, request, etc.)

### Layer 2: Container Isolation
- **Purpose**: Limit system access
- **Implementation**: Docker with security options
- **Protections**:
  - Non-root user (no privilege escalation)
  - Resource limits (prevent DoS)
  - Network isolation (no external access)
  - Capability dropping (no system calls)
  - Read-only filesystem (except /tmp)

### Layer 3: Application Design
- **Purpose**: Minimize attack surface
- **Implementation**: Simulated shells, no real execution
- **Protections**:
  - No subprocess module usage
  - No file I/O (except database)
  - No socket operations
  - No real shell access
  - Pre-written transcripts for "shell" examples

## Attack Surface Analysis

### Vulnerable Components
| Component | Vulnerability | Mitigation |
|-----------|--------------|------------|
| `display_name` field | SSTI injection | Sandboxed template rendering |
| Template rendering | Code execution | Whitelisted helpers only |
| Database | SQL injection | Parameterized queries |

### Protected Components
| Component | Protection |
|-----------|------------|
| Password storage | SHA-256 hashing |
| Session management | Flask secure sessions |
| Flag storage | Database isolation |
| Network | Internal bridge only |
| Filesystem | Read-only except /tmp |

## Whitelisted Helpers

### get_museum_meta(key=None)
- **Purpose**: Return museum metadata
- **Safe because**: Returns static dictionary data only
- **Usage**: `{{ get_museum_meta('name') }}`

### get_curator_note()
- **Purpose**: Return curator's welcome message
- **Safe because**: Returns static string only
- **Usage**: `{{ get_curator_note() }}`

### escape filter
- **Purpose**: HTML escape strings
- **Safe because**: Built-in Jinja2 filter, no side effects
- **Usage**: `{{ '<script>' | escape }}`

### upper filter
- **Purpose**: Convert string to uppercase
- **Safe because**: Built-in Jinja2 filter, no side effects
- **Usage**: `{{ 'hello' | upper }}`

## Blocked Access Patterns

### Attribute Access
```python
# These are blocked by is_safe_attribute()
{{ ''.__class__ }}
{{ {}.__mro__ }}
{{ [].__subclasses__() }}
{{ obj.__globals__ }}
{{ obj.__dict__ }}
{{ obj.__builtins__ }}
```

### Global Objects
```python
# These are not available in sandbox globals
{{ config }}
{{ request }}
{{ g }}
{{ session }}  # Note: session is not exposed in templates
```

### Builtins
```python
# These are not available
{{ open() }}
{{ eval() }}
{{ exec() }}
{{ __import__() }}
{{ __builtins__ }}
```

## Testing Strategy

### Unit Tests
- Test individual components (sandbox, helpers, flag generation)
- Verify whitelisted helpers work correctly
- Verify dangerous access is blocked

### Integration Tests
- Test user registration and login flow
- Test SSTI injection with safe payloads
- Test flag isolation between users

### Security Tests
- Test sandbox restrictions
- Test that dangerous imports are not present
- Test that shells are simulated only

## Educational Value

This application demonstrates:

1. **How SSTI vulnerabilities occur**: User input rendered as template
2. **Sandbox limitations**: Even with sandboxing, whitelisted helpers can leak data
3. **Defense in depth**: Multiple security layers (sandbox + container + design)
4. **Secure container configuration**: Non-root, limits, isolation
5. **Safe demonstration**: No real system compromise possible

## Deployment Warnings

⚠️ **NEVER deploy this application in production**

This application contains intentional vulnerabilities and should only be used:
- In isolated development environments
- For security training purposes
- Behind firewalls with no public access
- With proper supervision and monitoring

The simulated shells are educational transcripts only - they do not execute real commands.
