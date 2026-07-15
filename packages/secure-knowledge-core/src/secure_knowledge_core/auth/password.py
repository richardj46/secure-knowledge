from pwdlib import PasswordHash

_password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Convert a plaintext password into a secure one-way hash."""
    return _password_hash.hash(password)


def verify_password(
    plaintext_password: str,
    stored_password_hash: str,
) -> bool:
    """Return True when the plaintext password matches the stored hash."""
    return _password_hash.verify(
        plaintext_password,
        stored_password_hash,
    )