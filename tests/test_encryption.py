"""Tests for encryption system."""

import os
import tempfile
from pathlib import Path

import pytest

from lurkbot.security.encryption import (
    DecryptionError,
    EncryptionError,
    EncryptionManager,
    get_encryption_manager,
    is_encryption_enabled,
)


class TestEncryptionManager:
    """Test encryption manager functionality."""

    def test_generate_key(self):
        """Test key generation."""
        key = EncryptionManager.generate_key()
        assert isinstance(key, str)
        assert len(key) > 0
        # Fernet keys are 44 characters (32 bytes base64-encoded)
        assert len(key) == 44

    def test_encrypt_decrypt_string(self):
        """Test encrypting and decrypting strings."""
        manager = EncryptionManager()
        original = "sensitive data"

        encrypted = manager.encrypt(original)
        assert encrypted != original
        assert isinstance(encrypted, str)

        decrypted = manager.decrypt(encrypted)
        assert decrypted == original

    def test_encrypt_decrypt_bytes(self):
        """Test encrypting and decrypting bytes."""
        manager = EncryptionManager()
        original = b"binary data"

        encrypted = manager.encrypt(original)
        decrypted_str = manager.decrypt(encrypted)
        assert decrypted_str == original.decode("utf-8")

    def test_encrypt_decrypt_unicode(self):
        """Test encrypting and decrypting Unicode strings."""
        manager = EncryptionManager()
        original = "中文测试 🔒"

        encrypted = manager.encrypt(original)
        decrypted = manager.decrypt(encrypted)
        assert decrypted == original

    def test_invalid_key_raises_error(self):
        """Test that invalid key raises error."""
        with pytest.raises(ValueError, match="Invalid encryption key"):
            EncryptionManager(master_key="invalid_key")

    def test_decrypt_with_wrong_key(self):
        """Test that decryption fails with wrong key."""
        manager1 = EncryptionManager()
        manager2 = EncryptionManager()  # Different key

        encrypted = manager1.encrypt("data")

        with pytest.raises(DecryptionError):
            manager2.decrypt(encrypted)

    def test_decrypt_invalid_token(self):
        """Test that decryption fails with invalid token."""
        manager = EncryptionManager()

        with pytest.raises(DecryptionError):
            manager.decrypt("not_a_valid_token")

    def test_key_file_persistence(self):
        """Test key persistence to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test.key"

            # Create manager with key file
            manager1 = EncryptionManager(key_file=key_file)
            assert key_file.exists()

            original = "test data"
            encrypted = manager1.encrypt(original)

            # Load key from file
            manager2 = EncryptionManager(key_file=key_file)
            decrypted = manager2.decrypt(encrypted)

            assert decrypted == original

    def test_key_file_permissions(self):
        """Test that key file has secure permissions."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test.key"
            manager = EncryptionManager(key_file=key_file)

            # Check file permissions (should be 0o600 - owner read/write only)
            stat = key_file.stat()
            mode = stat.st_mode & 0o777
            assert mode == 0o600

    def test_encrypt_dict(self):
        """Test encrypting dictionary fields."""
        manager = EncryptionManager()
        original = {
            "message": "sensitive",
            "data": {"nested": "value"},
            "timestamp": 123456,
            "count": 42,
        }

        encrypted = manager.encrypt_dict(original)

        # Check encrypted fields
        assert "message__encrypted__" in encrypted
        assert "data__encrypted__" in encrypted
        # Non-sensitive fields should remain unencrypted
        assert encrypted["timestamp"] == 123456
        assert encrypted["count"] == 42

    def test_decrypt_dict(self):
        """Test decrypting dictionary fields."""
        manager = EncryptionManager()
        original = {
            "message": "sensitive",
            "data": {"nested": "value"},
            "timestamp": 123456,
        }

        encrypted = manager.encrypt_dict(original)
        decrypted = manager.decrypt_dict(encrypted)

        assert decrypted["message"] == original["message"]
        assert decrypted["data"] == original["data"]
        assert decrypted["timestamp"] == original["timestamp"]

    def test_ttl_encryption(self):
        """Test time-to-live encryption."""
        import time

        manager = EncryptionManager()
        data = "time sensitive"

        encrypted = manager.encrypt(data)

        # Should decrypt immediately
        decrypted = manager.decrypt(encrypted, ttl=1)
        assert decrypted == data

        # Wait and try again (should fail)
        time.sleep(2)
        with pytest.raises(DecryptionError, match="expired"):
            manager.decrypt(encrypted, ttl=1)

    def test_key_rotation(self):
        """Test key rotation."""
        manager = EncryptionManager()

        # Encrypt with old key
        original = "data"
        old_key = manager.key
        old_encrypted = manager.encrypt(original)

        # Rotate key
        new_key = manager.rotate_key()
        assert new_key != old_key
        assert manager.key == new_key

        # Old encrypted data should NOT decrypt with new key
        with pytest.raises(DecryptionError):
            manager.decrypt(old_encrypted)

        # New data should encrypt with new key
        new_encrypted = manager.encrypt(original)
        new_decrypted = manager.decrypt(new_encrypted)
        assert new_decrypted == original

    def test_key_rotation_with_file(self):
        """Test key rotation with file persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test.key"

            manager = EncryptionManager(key_file=key_file)
            old_key_content = key_file.read_bytes()

            # Rotate key
            manager.rotate_key()
            new_key_content = key_file.read_bytes()

            assert old_key_content != new_key_content


class TestGlobalEncryptionManager:
    """Test global encryption manager functionality."""

    def test_get_encryption_manager_with_master_key(self):
        """Test getting manager with master key."""
        key = EncryptionManager.generate_key()
        manager = get_encryption_manager(master_key=key)
        assert manager is not None
        assert isinstance(manager, EncryptionManager)

    def test_get_encryption_manager_with_env(self, monkeypatch):
        """Test getting manager from environment variable."""
        key = EncryptionManager.generate_key()
        monkeypatch.setenv("LURKBOT_ENCRYPTION_KEY", key)

        # Clear global instance
        import lurkbot.security.encryption

        lurkbot.security.encryption._encryption_manager = None

        manager = get_encryption_manager()
        assert manager is not None

    def test_get_encryption_manager_without_config(self):
        """Test getting manager without configuration."""
        # Clear environment and global instance
        os.environ.pop("LURKBOT_ENCRYPTION_KEY", None)
        import lurkbot.security.encryption

        lurkbot.security.encryption._encryption_manager = None

        manager = get_encryption_manager(auto_create=False)
        assert manager is None

    def test_is_encryption_enabled(self, monkeypatch):
        """Test checking if encryption is enabled."""
        # Clear environment and global instance
        os.environ.pop("LURKBOT_ENCRYPTION_KEY", None)
        import lurkbot.security.encryption

        lurkbot.security.encryption._encryption_manager = None

        assert is_encryption_enabled() is False

        # Enable encryption
        key = EncryptionManager.generate_key()
        monkeypatch.setenv("LURKBOT_ENCRYPTION_KEY", key)
        lurkbot.security.encryption._encryption_manager = None

        assert is_encryption_enabled() is True


class TestEncryptionPerformance:
    """Test encryption performance characteristics."""

    def test_encryption_overhead(self):
        """Test encryption overhead is reasonable."""
        import time

        manager = EncryptionManager()
        data = "x" * 1000  # 1KB of data

        start = time.time()
        for _ in range(100):
            encrypted = manager.encrypt(data)
            manager.decrypt(encrypted)
        elapsed = time.time() - start

        # Should be able to do 100 encrypt/decrypt cycles in < 100ms
        assert elapsed < 0.1, f"Encryption too slow: {elapsed:.3f}s for 100 cycles"

    def test_large_data_encryption(self):
        """Test encrypting large data."""
        manager = EncryptionManager()
        large_data = "x" * 1_000_000  # 1MB

        encrypted = manager.encrypt(large_data)
        decrypted = manager.decrypt(encrypted)

        assert decrypted == large_data
