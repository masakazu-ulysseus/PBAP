import os
import sys
import pytest

# Ensure the src directory is on PYTHONPATH for relative imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils import supabase_client

def test_get_supabase_client_success(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_KEY', 'anon-key-123')
    client = supabase_client.get_supabase_client()
    assert hasattr(client, 'storage')
    assert hasattr(client, 'table')

def test_get_supabase_client_missing_env(monkeypatch):
    monkeypatch.delenv('SUPABASE_URL', raising=False)
    monkeypatch.delenv('SUPABASE_KEY', raising=False)
    with pytest.raises(ValueError) as exc:
        supabase_client.get_supabase_client()
    assert 'Supabase URL and Key must be set' in str(exc.value)
