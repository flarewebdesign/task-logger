"""Operating-system backed storage for dashboard credentials."""

import os

try:
    import keyring
    from keyring.errors import KeyringError, PasswordDeleteError
except ImportError:  # pragma: no cover - exercised when optional migration is unavailable
    keyring = None

    class KeyringError(Exception):
        pass

    class PasswordDeleteError(KeyringError):
        pass


SERVICE_NAME = os.environ.get("TASK_LOGGER_SECRET_SERVICE", "Task Logger Dashboard")
DASHBOARD_TOKEN_ACCOUNT = os.environ.get("TASK_LOGGER_SECRET_ACCOUNT", "dashboard-api-token")


class SecretStoreError(RuntimeError):
    """Raised when the operating-system credential store cannot be used."""


def load_dashboard_token():
    if keyring is None:
        return ""
    try:
        return keyring.get_password(SERVICE_NAME, DASHBOARD_TOKEN_ACCOUNT) or ""
    except KeyringError as exc:
        raise SecretStoreError("Could not read the dashboard token from the system credential store.") from exc


def save_dashboard_token(token):
    if keyring is None:
        raise SecretStoreError("Install the keyring package to store the dashboard token securely.")

    normalized = str(token or "").strip()
    try:
        if normalized:
            keyring.set_password(SERVICE_NAME, DASHBOARD_TOKEN_ACCOUNT, normalized)
        else:
            try:
                keyring.delete_password(SERVICE_NAME, DASHBOARD_TOKEN_ACCOUNT)
            except PasswordDeleteError:
                pass
    except KeyringError as exc:
        raise SecretStoreError("Could not update the dashboard token in the system credential store.") from exc
