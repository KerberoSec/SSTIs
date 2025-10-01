# Quick Start Guide

## Running Locally (Without Docker)

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py

# Access at http://localhost:5000
```

## Running with Docker Compose (Recommended)

```bash
# Build and start the container
docker compose up --build

# Access at http://localhost:5000

# Stop the container
docker compose down
```

## Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run all tests
pytest test_app.py -v

# Run with coverage
pytest test_app.py --cov=app --cov-report=html
```

## Try the SSTI Vulnerability

1. Navigate to http://localhost:5000
2. Click "Register"
3. Create a user with:
   - Username: `alice`
   - Password: `password123`
   - Display Name: `{{ get_museum_meta('name') }}`
4. Login with your credentials
5. View the preview page - your display name will be rendered as "The Template Museum"

### Safe SSTI Payloads (Whitelisted)

Try these in the Display Name field:

```jinja2
{{ get_museum_meta('name') }}
{{ get_museum_meta('founded') }}
{{ get_curator_note() }}
{{ 'hello world' | upper }}
{{ '<script>alert(1)</script>' | escape }}
```

### Blocked SSTI Payloads (Sandboxed)

These will fail due to sandbox restrictions:

```jinja2
{{ ''.__class__ }}
{{ config }}
{{ self }}
{{ request }}
{{ lipsum.__globals__ }}
```

## View Simulated Shells

Navigate to http://localhost:5000/simulated-shells to see educational transcripts demonstrating what SSTI vulnerabilities might attempt in unsafe environments.

**Important**: All shell examples are simulated - no actual commands are executed.

## Security Notes

- Each user gets a unique flag: `FLAG{username_<random_hex>}`
- Flags are isolated - users can only see their own flag
- The sandbox blocks access to dangerous Python internals
- Container runs as non-root user with resource limits
- Network is isolated (no external access)
- No real subprocess, file I/O, or socket operations

## Troubleshooting

### Docker Build Issues

If Docker build fails due to SSL certificate errors, you can:

1. Build without Docker:
   ```bash
   pip install -r requirements.txt
   python app.py
   ```

2. Or configure Docker to use a different registry mirror

### Database Issues

The application creates `/tmp/museum.db` automatically. If you encounter database errors:

```bash
# Clean up and restart
rm /tmp/museum.db
python app.py
```

## Educational Use

This application is designed for educational purposes to demonstrate:
- How SSTI vulnerabilities work
- How template sandboxing provides some protection
- The importance of input validation
- Secure container configuration

**Do not deploy this application in production or on public networks.**
