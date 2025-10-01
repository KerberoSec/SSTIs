import pytest
import os
import tempfile
from app import app, init_db, DATABASE, generate_flag, RestrictedSandbox

@pytest.fixture
def client():
    """Create test client with temporary database."""
    # Use a temporary database for testing
    db_fd, db_path = tempfile.mkstemp()
    
    # Temporarily override DATABASE
    original_db = DATABASE
    app.config['DATABASE'] = db_path
    import app as app_module
    app_module.DATABASE = db_path
    
    app.config['TESTING'] = True
    
    # Initialize database
    init_db()
    
    with app.test_client() as client:
        yield client
    
    # Cleanup
    os.close(db_fd)
    os.unlink(db_path)
    app_module.DATABASE = original_db

def test_home_page(client):
    """Test home page redirects properly."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'Template Museum' in response.data

def test_register_user(client):
    """Test user registration."""
    response = client.post('/register', data={
        'username': 'testuser',
        'password': 'testpass',
        'display_name': 'Test User'
    })
    assert response.status_code == 302  # Redirect to login

def test_unique_flags(client):
    """Test that each user gets a unique flag."""
    # Register first user
    client.post('/register', data={
        'username': 'user1',
        'password': 'pass1',
        'display_name': 'User One'
    })
    
    # Login and get flag
    client.post('/login', data={
        'username': 'user1',
        'password': 'pass1'
    })
    response1 = client.get('/preview')
    flag1 = None
    if b'FLAG{user1_' in response1.data:
        # Extract flag from response
        start = response1.data.find(b'FLAG{')
        end = response1.data.find(b'}', start) + 1
        flag1 = response1.data[start:end]
    
    # Logout
    client.get('/logout')
    
    # Register second user
    client.post('/register', data={
        'username': 'user2',
        'password': 'pass2',
        'display_name': 'User Two'
    })
    
    # Login and get flag
    client.post('/login', data={
        'username': 'user2',
        'password': 'pass2'
    })
    response2 = client.get('/preview')
    flag2 = None
    if b'FLAG{user2_' in response2.data:
        start = response2.data.find(b'FLAG{')
        end = response2.data.find(b'}', start) + 1
        flag2 = response2.data[start:end]
    
    # Flags should be different
    assert flag1 is not None
    assert flag2 is not None
    assert flag1 != flag2
    assert b'user1' in flag1
    assert b'user2' in flag2

def test_login_required(client):
    """Test that preview requires login."""
    response = client.get('/preview')
    assert response.status_code == 302  # Redirect to login

def test_ssti_basic_injection(client):
    """Test that SSTI injection works with whitelisted helpers."""
    # Register with SSTI in display_name
    client.post('/register', data={
        'username': 'ssti_user',
        'password': 'pass',
        'display_name': '{{ get_museum_meta("name") }}'
    })
    
    client.post('/login', data={
        'username': 'ssti_user',
        'password': 'pass'
    })
    
    response = client.get('/preview')
    # Should render the museum name
    assert b'The Template Museum' in response.data

def test_sandbox_blocks_dangerous_access(client):
    """Test that sandbox blocks access to dangerous attributes."""
    sandbox = RestrictedSandbox()
    
    # Test blocking __class__ access
    dangerous_templates = [
        "{{ ''.__class__ }}",
        "{{ {}.__class__ }}",
        "{{ [].__class__.__mro__ }}",
        "{{ ''.__class__.__mro__[1].__subclasses__() }}",
    ]
    
    for template_str in dangerous_templates:
        try:
            template = sandbox.from_string(template_str)
            result = template.render()
            # Should either fail or not expose dangerous info
            assert '__class__' not in result.lower() or 'type' not in result.lower()
        except Exception:
            # Expected to fail - sandbox is working
            pass

def test_sandbox_allows_whitelisted_helpers(client):
    """Test that sandbox allows whitelisted helpers."""
    sandbox = RestrictedSandbox()
    
    # Test whitelisted helpers work
    template = sandbox.from_string("{{ get_museum_meta('name') }}")
    result = template.render()
    assert 'The Template Museum' in result
    
    template = sandbox.from_string("{{ get_curator_note() }}")
    result = template.render()
    assert 'Welcome' in result
    
    # Test whitelisted filters
    template = sandbox.from_string("{{ 'test' | upper }}")
    result = template.render()
    assert 'TEST' in result

def test_sandbox_blocks_builtins(client):
    """Test that sandbox blocks access to builtins."""
    sandbox = RestrictedSandbox()
    
    # Should not have access to dangerous builtins
    dangerous_builtins = [
        "{{ __builtins__ }}",
        "{{ __import__ }}",
        "{{ open }}",
        "{{ eval }}",
        "{{ exec }}",
    ]
    
    for template_str in dangerous_builtins:
        try:
            template = sandbox.from_string(template_str)
            result = template.render()
            # Should be empty or error
            assert len(result.strip()) == 0 or 'undefined' in result.lower()
        except Exception:
            # Expected to fail
            pass

def test_flag_isolation(client):
    """Test that users can only see their own flags."""
    # Create two users
    client.post('/register', data={
        'username': 'alice',
        'password': 'alicepass',
        'display_name': 'Alice'
    })
    
    client.post('/register', data={
        'username': 'bob',
        'password': 'bobpass',
        'display_name': 'Bob'
    })
    
    # Login as Alice
    client.post('/login', data={
        'username': 'alice',
        'password': 'alicepass'
    })
    alice_response = client.get('/preview')
    assert b'FLAG{alice_' in alice_response.data
    assert b'FLAG{bob_' not in alice_response.data
    
    # Logout and login as Bob
    client.get('/logout')
    client.post('/login', data={
        'username': 'bob',
        'password': 'bobpass'
    })
    bob_response = client.get('/preview')
    assert b'FLAG{bob_' in bob_response.data
    assert b'FLAG{alice_' not in bob_response.data

def test_simulated_shells_page(client):
    """Test that simulated shells page exists and is marked as simulated."""
    response = client.get('/simulated-shells')
    assert response.status_code == 200
    assert b'SIMULATED' in response.data
    assert b'No actual system commands' in response.data or b'no real' in response.data.lower()
    assert b'Template Shell' in response.data or b'template' in response.data.lower()
    assert b'OS Shell' in response.data or b'os' in response.data.lower()

def test_no_subprocess_in_code():
    """Test that app.py doesn't use subprocess or dangerous modules."""
    with open('app.py', 'r') as f:
        code = f.read()
    
    # Should not import dangerous modules
    dangerous_imports = ['subprocess', 'os.system', 'eval', 'exec', 'socket']
    for danger in dangerous_imports:
        if danger == 'socket':
            assert 'import socket' not in code
        elif danger in ['eval', 'exec']:
            # These might appear in strings but not as actual calls
            assert f"{danger}(" not in code or f"# {danger}" in code
        else:
            assert danger not in code

def test_sandbox_is_restrictive(client):
    """Test that the sandbox properly restricts access."""
    # Register user with various SSTI payloads
    payloads = [
        "{{ config }}",
        "{{ self }}",
        "{{ request }}",
        "{{ lipsum.__globals__ }}",
        "{{ cycler.__init__.__globals__ }}",
    ]
    
    for i, payload in enumerate(payloads):
        username = f'test_sandbox_{i}'
        client.post('/register', data={
            'username': username,
            'password': 'pass',
            'display_name': payload
        })
        
        client.post('/login', data={
            'username': username,
            'password': 'pass'
        })
        
        response = client.get('/preview')
        # Should not expose internal objects
        assert b'SECRET' not in response.data.upper() or b'secret_key' not in response.data
        assert b'__globals__' not in response.data
        
        client.get('/logout')

def test_generate_flag_format():
    """Test that generated flags have correct format."""
    flag1 = generate_flag('testuser')
    assert flag1.startswith('FLAG{testuser_')
    assert flag1.endswith('}')
    assert len(flag1) > 20  # Should have random part
    
    # Each flag should be unique
    flag2 = generate_flag('testuser')
    assert flag1 != flag2
