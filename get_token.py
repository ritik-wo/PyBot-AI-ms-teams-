"""Module for Microsoft Graph API token acquisition using MSAL."""
import os
import msal
import logging

# NEW: load .env
try:
    from dotenv import load_dotenv
    load_dotenv()  # loads .env from current working directory
except Exception:
    # dotenv is optional if you export vars in the shell/host
    pass

def _getenv(key: str, *aliases: str) -> str | None:
    """Get an env var by key or fallback aliases; trims whitespace."""
    for k in (key, *aliases):
        v = os.getenv(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def get_graph_token_client_credentials() -> str:
    """
    Acquire a Microsoft Graph token via client credentials.
    Reads env vars: CLIENT_ID, CLIENT_SECRET, TENANT_ID, MSAL_SCOPE
    (also accepts MicrosoftAppId/MicrosoftAppPassword as fallbacks).
    """
    try:
        client_id = _getenv("CLIENT_ID", "MicrosoftAppId")
        client_secret = _getenv("CLIENT_SECRET", "MicrosoftAppPassword")
        tenant_id = _getenv("TENANT_ID")
        scope = _getenv("MSAL_SCOPE")

        if not all([client_id, client_secret, tenant_id, scope]):
            # Print which are missing without leaking secrets
            missing = [
                name for name, val in {
                    "CLIENT_ID": client_id,
                    "CLIENT_SECRET": "***" if client_secret else None,
                    "TENANT_ID": tenant_id,
                    "MSAL_SCOPE": scope,
                }.items() if val in (None, "")
            ]
            raise ValueError(f"Missing env vars: {', '.join(missing)}")

        app = msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=f"https://login.microsoftonline.com/{tenant_id}",
        )

        result = app.acquire_token_for_client(scopes=[scope])

        if not result or "access_token" not in result:
            error_description = (result or {}).get("error_description", "Unknown error")
            error_code = (result or {}).get("error", "unknown_error")
            raise RuntimeError(f"Failed to acquire token. {error_code}: {error_description}")
        print(result["access_token"])
        return result["access_token"]

    except (ValueError, RuntimeError):
        raise
    except Exception as error:
        logging.error("Token acquisition error: %s", error)
        raise RuntimeError(f"Unexpected error during token acquisition: {error}") from error


get_graph_token_client_credentials()