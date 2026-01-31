"""Session data encryption using Fernet (AES-256).

This module provides encryption/decryption for sensitive session data
to protect user information and conversation history at rest.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from loguru import logger


class EncryptionManager:
    """Manages encryption/decryption of session data using Fernet.

    Fernet uses AES-256 in CBC mode with HMAC for authentication.
    Keys are 32 URL-safe base64-encoded bytes.
    """

    def __init__(self, master_key: str | None = None, key_file: str | Path | None = None):
        """Initialize encryption manager.

        Args:
            master_key: Base64-encoded Fernet key (32 bytes). If None, loads from key_file.
            key_file: Path to file containing the encryption key. If None and master_key
                      is None, generates a new key.

        Example:
            # From environment variable
            manager = EncryptionManager(master_key=os.getenv('LURKBOT_ENCRYPTION_KEY'))

            # From key file
            manager = EncryptionManager(key_file='~/.lurkbot/encryption.key')

            # Auto-generate (for testing)
            manager = EncryptionManager()
        """
        self.key_file = Path(key_file).expanduser() if key_file else None

        # Load or generate key
        if master_key:
            self.key = master_key.encode() if isinstance(master_key, str) else master_key
        elif self.key_file and self.key_file.exists():
            with open(self.key_file, "rb") as f:
                self.key = f.read().strip()
                logger.info(f"Loaded encryption key from {self.key_file}")
        else:
            # Generate new key
            self.key = Fernet.generate_key()
            logger.warning("Generated new encryption key (consider persisting to file)")
            if self.key_file:
                self._save_key()

        # Validate key format
        try:
            self.fernet = Fernet(self.key)
        except Exception as e:
            raise ValueError(f"Invalid encryption key: {e}") from e

    def _save_key(self) -> None:
        """Save encryption key to file."""
        if not self.key_file:
            return

        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.key_file, "wb") as f:
            f.write(self.key)
        # Set restrictive permissions (owner only)
        self.key_file.chmod(0o600)
        logger.info(f"Saved encryption key to {self.key_file}")

    def encrypt(self, data: str | bytes) -> str:
        """Encrypt data.

        Args:
            data: Plain text string or bytes to encrypt

        Returns:
            Base64-encoded encrypted token as string

        Example:
            encrypted = manager.encrypt("sensitive data")
        """
        if isinstance(data, str):
            data = data.encode("utf-8")

        try:
            token = self.fernet.encrypt(data)
            return token.decode("utf-8")
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise EncryptionError("Failed to encrypt data") from e

    def decrypt(self, token: str | bytes, ttl: int | None = None) -> str:
        """Decrypt data.

        Args:
            token: Base64-encoded encrypted token
            ttl: Optional time-to-live in seconds. If provided, decryption will
                 fail if token is older than ttl seconds.

        Returns:
            Decrypted plain text as string

        Raises:
            DecryptionError: If decryption fails or token expired

        Example:
            plaintext = manager.decrypt(encrypted_token)
            plaintext = manager.decrypt(encrypted_token, ttl=3600)  # 1 hour
        """
        if isinstance(token, str):
            token = token.encode("utf-8")

        try:
            data = self.fernet.decrypt(token, ttl=ttl)
            return data.decode("utf-8")
        except InvalidToken as e:
            if ttl:
                logger.warning(f"Decryption failed: token expired (ttl={ttl}s)")
                raise DecryptionError("Token expired or invalid") from e
            else:
                logger.error("Decryption failed: invalid token or key")
                raise DecryptionError("Invalid token or encryption key") from e
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise DecryptionError("Failed to decrypt data") from e

    def encrypt_dict(self, data: dict) -> dict:
        """Encrypt selected fields in a dictionary.

        This is useful for encrypting specific sensitive fields while leaving
        other fields (like IDs, timestamps) unencrypted for indexing.

        Args:
            data: Dictionary with plain text values

        Returns:
            Dictionary with encrypted values (marked with __encrypted__ prefix)

        Example:
            original = {"message": "sensitive", "timestamp": 123456}
            encrypted = manager.encrypt_dict(original)
            # {"message__encrypted__": "gAAAAAB...", "timestamp": 123456}
        """
        import json

        result = {}
        for key, value in data.items():
            if isinstance(value, (str, dict, list)):
                # Encrypt complex types as JSON
                json_str = json.dumps(value) if not isinstance(value, str) else value
                result[f"{key}__encrypted__"] = self.encrypt(json_str)
            else:
                # Keep simple types unencrypted
                result[key] = value
        return result

    def decrypt_dict(self, data: dict, ttl: int | None = None) -> dict:
        """Decrypt fields in a dictionary.

        Args:
            data: Dictionary with encrypted values (marked with __encrypted__ prefix)
            ttl: Optional time-to-live in seconds

        Returns:
            Dictionary with decrypted values

        Example:
            decrypted = manager.decrypt_dict(encrypted_dict)
        """
        import json

        result = {}
        for key, value in data.items():
            if key.endswith("__encrypted__"):
                # Decrypt and restore original key name
                original_key = key.replace("__encrypted__", "")
                decrypted = self.decrypt(value, ttl=ttl)
                # Try to parse as JSON (for complex types)
                try:
                    result[original_key] = json.loads(decrypted)
                except json.JSONDecodeError:
                    result[original_key] = decrypted
            else:
                result[key] = value
        return result

    def rotate_key(self, new_key: str | bytes | None = None) -> bytes:
        """Rotate encryption key.

        Warning: This does NOT re-encrypt existing data. You must manually
        re-encrypt all existing encrypted data with the new key.

        Args:
            new_key: New encryption key. If None, generates a new key.

        Returns:
            The new key (for backup purposes)

        Example:
            new_key = manager.rotate_key()
            # Now re-encrypt all existing data...
        """
        old_key = self.key

        if new_key:
            self.key = new_key.encode() if isinstance(new_key, str) else new_key
        else:
            self.key = Fernet.generate_key()

        try:
            self.fernet = Fernet(self.key)
            if self.key_file:
                self._save_key()
            logger.info("Encryption key rotated successfully")
            return self.key
        except Exception as e:
            # Restore old key on failure
            self.key = old_key
            self.fernet = Fernet(self.key)
            logger.error(f"Key rotation failed, restored old key: {e}")
            raise EncryptionError("Failed to rotate encryption key") from e

    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet encryption key.

        Returns:
            Base64-encoded encryption key as string

        Example:
            key = EncryptionManager.generate_key()
            print(f"New key: {key}")
            # Store securely in environment or key file
        """
        return Fernet.generate_key().decode("utf-8")


class EncryptionError(Exception):
    """Raised when encryption fails."""


class DecryptionError(Exception):
    """Raised when decryption fails."""


# Global encryption manager instance
_encryption_manager: EncryptionManager | None = None


def get_encryption_manager(
    master_key: str | None = None,
    key_file: str | Path | None = None,
    auto_create: bool = True,
) -> EncryptionManager | None:
    """Get or create global encryption manager.

    Args:
        master_key: Encryption key (overrides environment and key_file)
        key_file: Path to key file
        auto_create: If True, create manager if encryption is enabled

    Returns:
        EncryptionManager instance or None if encryption is disabled

    Example:
        # From environment variable
        manager = get_encryption_manager(master_key=os.getenv('LURKBOT_ENCRYPTION_KEY'))

        # From key file
        manager = get_encryption_manager(key_file='~/.lurkbot/encryption.key')

        # Check if encryption is enabled
        manager = get_encryption_manager(auto_create=False)
        if manager:
            encrypted = manager.encrypt("data")
    """
    global _encryption_manager

    if _encryption_manager is None:
        # Check environment variable
        env_key = os.getenv("LURKBOT_ENCRYPTION_KEY")
        if master_key or env_key:
            _encryption_manager = EncryptionManager(master_key=master_key or env_key)
        elif key_file:
            _encryption_manager = EncryptionManager(key_file=key_file)
        elif auto_create:
            # Default key file location
            default_key_file = Path.home() / ".lurkbot" / "encryption.key"
            if default_key_file.exists():
                _encryption_manager = EncryptionManager(key_file=default_key_file)
            else:
                logger.info("Encryption not configured (set LURKBOT_ENCRYPTION_KEY or create key file)")
                return None
        else:
            return None

    return _encryption_manager


def is_encryption_enabled() -> bool:
    """Check if encryption is enabled.

    Returns:
        True if encryption manager is available

    Example:
        if is_encryption_enabled():
            encrypted = get_encryption_manager().encrypt("data")
    """
    return get_encryption_manager(auto_create=False) is not None
