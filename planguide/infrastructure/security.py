"""密码与会话 token 安全工具。"""

import hashlib
import hmac
import secrets


class PasswordHasher:
    def hash_password(self, password: str) -> tuple[str, str]:
        salt = secrets.token_hex(16)
        return salt, self._derive(password, salt)

    def verify(self, password: str, salt: str, password_hash: str) -> bool:
        return hmac.compare_digest(self._derive(password, salt), password_hash)

    def hash_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _derive(self, password: str, salt: str) -> str:
        raw = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            120_000,
        )
        return raw.hex()
