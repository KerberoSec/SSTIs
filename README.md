# Template Museum Authed - SSTI Demonstration

A Dockerized Flask application demonstrating Server-Side Template Injection (SSTI) vulnerabilities in a controlled, sandboxed environment for educational purposes.

## ⚠️ IMPORTANT SECURITY NOTICE

**This application contains intentional security vulnerabilities for educational purposes.**

### Simulated Shells Only

This application uses **SIMULATED shell transcripts** for demonstration purposes:
- ❌ **NO real subprocess execution**
- ❌ **NO real file I/O operations** (except database)
- ❌ **NO real socket connections**
- ❌ **NO real OS command execution**

All "shell" interactions shown are pre-written transcripts to demonstrate what SSTI vulnerabilities could potentially do in unsafe environments, without actually compromising the system.

## Features

### Application Features
- **User Registration & Login**: SQLite-based authentication system
- **Unique Flag Generation**: Each user receives a unique flag stored in the database
- **SSTI Vulnerability**: Template injection via user's `display_name` field during registration
- **Sandboxed Template Rendering**: Jinja2 sandbox with strictly whitelisted helpers only

### Security Features (Containerized)
- **Non-root Container**: Runs as unprivileged user (UID 1000)
- **Resource Limits**: CPU and memory constraints via Docker
- **Network Isolation**: No external network access (internal network only)
- **Capability Dropping**: All Linux capabilities dropped
- **Read-only Where Possible**: Only /tmp is writable

### Whitelisted Template Helpers
The sandbox only allows these specific helpers:
1. `get_museum_meta(key)` - Returns museum metadata
2. `get_curator_note()` - Returns curator's welcome message
3. `escape` filter - HTML escaping
4. `upper` filter - Uppercase conversion

All other template features (attribute access, builtins, etc.) are blocked.

## Installation

### Prerequisites
- Docker
- Docker Compose

### Build and Run

```bash
# Build the container
docker-compose build

# Run the application
docker-compose up

# Access at http://localhost:5000
```

### Run Tests

```bash
# Install dependencies locally (optional)
pip install -r requirements.txt

# Run tests
pytest test_app.py -v

# Run with coverage
pytest test_app.py --cov=app --cov-report=html
```

## Usage

1. **Register**: Create a new account at `/register`
   - Provide username, password, and display_name
   - The display_name field is vulnerable to SSTI
   - Each user gets a unique flag: `FLAG{username_<random>}`

2. **Login**: Authenticate at `/login`

3. **Preview**: View your profile at `/preview`
   - Your display_name is rendered as a Jinja2 template
   - Try injecting: `{{ get_museum_meta('name') }}`
   - Try injecting: `{{ get_curator_note() }}`
   - Try injecting: `{{ 'test' | upper }}`

4. **Simulated Shells**: View educational transcripts at `/simulated-shells`
   - See examples of what SSTI payloads might attempt
   - All examples are simulated - no real execution

## SSTI Examples

### Safe Injections (Whitelisted)
```jinja2
{{ get_museum_meta('name') }}
{{ get_curator_note() }}
{{ 'hello' | upper }}
{{ '<script>alert(1)</script>' | escape }}
```

### Blocked Injections (Sandboxed)
These will fail or return empty due to sandbox restrictions:
```jinja2
{{ ''.__class__ }}
{{ config }}
{{ self }}
{{ request }}
{{ __builtins__ }}
{{ lipsum.__globals__ }}
```

## Architecture

### Directory Structure
```
.
├── app.py                 # Main Flask application
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container image definition
├── docker-compose.yml    # Container orchestration
├── test_app.py           # Test suite
└── README.md             # This file
```

### Database Schema
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name TEXT NOT NULL,
    flag TEXT UNIQUE NOT NULL
);
```

### Security Controls

#### Sandbox Implementation
- Custom `RestrictedSandbox` class extending Jinja2's `SandboxedEnvironment`
- Explicitly whitelisted globals and filters
- Blocks attribute access to dangerous objects (`__class__`, `__mro__`, etc.)
- No access to builtins, config, or request objects

#### Container Security
- Runs as non-root user (museum:1000)
- Resource limits: 0.5 CPU, 256MB RAM
- Network isolation: internal bridge only
- Security options: no-new-privileges, all capabilities dropped
- Temporary filesystem for database

#### Flag Isolation
- Each user's flag is unique and stored in the database
- Users can only access their own flag through authenticated session
- No cross-user information leakage

## Testing

The test suite (`test_app.py`) validates:

### Sandbox Safety Tests
- ✅ Whitelisted helpers are accessible
- ✅ Dangerous attribute access is blocked (`__class__`, `__mro__`, etc.)
- ✅ Builtins are not accessible (`eval`, `exec`, `open`, etc.)
- ✅ Internal objects are not exposed (`config`, `request`, `self`)

### Flag Isolation Tests
- ✅ Each user gets a unique flag
- ✅ Users can only see their own flags
- ✅ Flag format is correct: `FLAG{username_<random>}`

### Functional Tests
- ✅ Registration and login work
- ✅ Authentication is required for preview
- ✅ SSTI injection works with whitelisted helpers
- ✅ Simulated shells page exists and is clearly marked

### Code Safety Tests
- ✅ No subprocess imports
- ✅ No dangerous module usage
- ✅ No real system execution

## Educational Purpose

This application demonstrates:
1. How SSTI vulnerabilities occur in web applications
2. How template sandboxing can mitigate (but not eliminate) SSTI risks
3. The importance of input validation and output encoding
4. How to build secure, isolated containers for running vulnerable applications

## Limitations

- This is a demonstration only - not for production use
- The sandbox is restrictive but may not catch all edge cases
- Real-world SSTI attacks are more complex
- The simulated shells do not represent actual exploitation

## License

Educational use only. Not licensed for production deployment.