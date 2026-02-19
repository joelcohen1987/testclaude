"""OneNote integration via Microsoft Graph API.

Uses MSAL device-code flow so you sign in once via browser,
then the token is cached locally for future use.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

from readlater.config import DEFAULT_CONFIG_DIR, get_config, save_config

TOKEN_CACHE_FILE = DEFAULT_CONFIG_DIR / "onenote_token_cache.json"

# Microsoft Graph scopes needed for OneNote
SCOPES = ["Notes.ReadWrite", "Notes.Create"]

# Graph API base
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _get_msal():
    """Import msal, giving a helpful error if not installed."""
    try:
        import msal
        return msal
    except ImportError:
        print(
            "Error: The 'msal' package is required for OneNote integration.\n"
            "Install it with:  pip install msal requests"
        )
        sys.exit(1)


def _get_requests():
    try:
        import requests
        return requests
    except ImportError:
        print(
            "Error: The 'requests' package is required for OneNote integration.\n"
            "Install it with:  pip install requests"
        )
        sys.exit(1)


def _load_token_cache():
    """Load MSAL token cache from disk."""
    msal = _get_msal()
    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE_FILE.exists():
        cache.deserialize(TOKEN_CACHE_FILE.read_text())
    return cache


def _save_token_cache(cache):
    """Persist MSAL token cache to disk."""
    DEFAULT_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_CACHE_FILE.write_text(cache.serialize())


def _get_client_id():
    """Get the Azure AD client ID from config."""
    config = get_config()
    client_id = config.get("onenote", {}).get("client_id")
    if not client_id:
        print(
            "Error: OneNote not configured yet.\n"
            "Run:  readlater config-onenote --client-id <YOUR_CLIENT_ID>\n\n"
            "See setup instructions below to get your client ID."
        )
        _print_setup_instructions()
        sys.exit(1)
    return client_id


def _print_setup_instructions():
    """Print Azure AD app registration instructions."""
    print(
        "\n"
        "=== OneNote Setup (one-time, ~3 minutes) ===\n"
        "\n"
        "1. Go to: https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade\n"
        "   (Sign in with your Microsoft account)\n"
        "\n"
        "2. Click '+ New registration'\n"
        "   - Name: ReadLater\n"
        "   - Supported account types: 'Personal Microsoft accounts only'\n"
        "     (or 'Accounts in any org + personal' if you use work OneNote)\n"
        "   - Redirect URI: select 'Public client/native' and enter:\n"
        "     https://login.microsoftonline.com/common/oauth2/nativeclient\n"
        "   - Click 'Register'\n"
        "\n"
        "3. Copy the 'Application (client) ID' from the overview page\n"
        "\n"
        "4. Go to 'API permissions' (left sidebar) → 'Add a permission'\n"
        "   → 'Microsoft Graph' → 'Delegated permissions'\n"
        "   → Search and add: Notes.ReadWrite, Notes.Create\n"
        "   → Click 'Add permissions'\n"
        "\n"
        "5. Run:\n"
        "   readlater config-onenote --client-id <paste-your-client-id>\n"
    )


def authenticate():
    """Authenticate with Microsoft Graph using device code flow.

    Returns an access token string, or exits on failure.
    """
    msal_lib = _get_msal()
    client_id = _get_client_id()
    cache = _load_token_cache()

    app = msal_lib.PublicClientApplication(
        client_id,
        authority="https://login.microsoftonline.com/consumers",
        token_cache=cache,
    )

    # Try silent auth first (cached token)
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _save_token_cache(cache)
            return result["access_token"]

    # Fall back to device code flow
    flow = app.initiate_device_flow(scopes=SCOPES)
    if "user_code" not in flow:
        print(f"Error starting authentication: {flow.get('error_description', 'Unknown error')}")
        sys.exit(1)

    print(f"\nTo sign in, open a browser to: {flow['verification_uri']}")
    print(f"Enter code: {flow['user_code']}\n")
    print("Waiting for you to sign in...")

    result = app.acquire_token_by_device_flow(flow)
    if "access_token" not in result:
        print(f"Authentication failed: {result.get('error_description', 'Unknown error')}")
        sys.exit(1)

    _save_token_cache(cache)
    print("Signed in successfully!\n")
    return result["access_token"]


def _graph_get(token: str, endpoint: str) -> dict:
    """Make a GET request to Microsoft Graph."""
    requests = _get_requests()
    resp = requests.get(
        f"{GRAPH_BASE}{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _graph_post(token: str, endpoint: str, data=None, content_type="application/json") -> dict:
    """Make a POST request to Microsoft Graph."""
    requests = _get_requests()
    headers = {"Authorization": f"Bearer {token}"}
    if content_type == "application/json":
        headers["Content-Type"] = "application/json"
        resp = requests.post(
            f"{GRAPH_BASE}{endpoint}",
            headers=headers,
            json=data,
            timeout=30,
        )
    else:
        headers["Content-Type"] = content_type
        resp = requests.post(
            f"{GRAPH_BASE}{endpoint}",
            headers=headers,
            data=data,
            timeout=30,
        )
    resp.raise_for_status()
    return resp.json()


def _ensure_section(token: str) -> str:
    """Get or create the 'Reading List' section. Returns section ID."""
    config = get_config()
    section_id = config.get("onenote", {}).get("section_id")

    # If we have a cached section ID, verify it still exists
    if section_id:
        try:
            _graph_get(token, f"/me/onenote/sections/{section_id}")
            return section_id
        except Exception:
            pass  # Section was deleted, recreate it

    # Look for existing 'Reading List' section across all notebooks
    sections = _graph_get(token, "/me/onenote/sections?$filter=displayName eq 'Reading List'")
    if sections.get("value"):
        section_id = sections["value"][0]["id"]
    else:
        # Need a notebook first — use default or create one
        notebooks = _graph_get(token, "/me/onenote/notebooks")
        if notebooks.get("value"):
            notebook_id = notebooks["value"][0]["id"]
        else:
            nb = _graph_post(token, "/me/onenote/notebooks", {"displayName": "ReadLater"})
            notebook_id = nb["id"]

        # Create the section
        section = _graph_post(
            token,
            f"/me/onenote/notebooks/{notebook_id}/sections",
            {"displayName": "Reading List"},
        )
        section_id = section["id"]

    # Cache the section ID
    config.setdefault("onenote", {})["section_id"] = section_id
    save_config(config)
    return section_id


def _build_page_html(item: dict) -> str:
    """Build OneNote page HTML for a library item."""
    title = item.get("title", "Untitled")
    content_type = item.get("type", "pdf")
    source_url = item.get("source_url", "")
    tags = item.get("tags", [])
    added = item.get("added", "")

    type_badges = {
        "pdf": '<span style="background:#2563eb;color:white;padding:3px 10px;border-radius:12px;font-size:13px;">PDF</span>',
        "audio": '<span style="background:#16a34a;color:white;padding:3px 10px;border-radius:12px;font-size:13px;">AUDIO</span>',
        "link": '<span style="background:#9333ea;color:white;padding:3px 10px;border-radius:12px;font-size:13px;">LINK</span>',
    }
    badge = type_badges.get(content_type, "")

    # Build the action link
    if source_url:
        action_link = f'<p><a href="{source_url}">Open source</a></p>'
    else:
        action_link = ""

    # For PDFs with local files, add note about OneDrive location
    local_note = ""
    if item.get("local_file"):
        local_note = f'<p style="color:#6b7280;font-size:12px;">File: {item["local_file"]}</p>'

    tag_str = ""
    if tags:
        tag_str = f'<p style="color:#6b7280;">Tags: {", ".join(tags)}</p>'

    # Format date
    date_str = ""
    if added:
        try:
            dt = datetime.fromisoformat(added)
            date_str = dt.strftime("%b %d, %Y")
        except (ValueError, TypeError):
            date_str = str(added)

    # OneNote requires this exact HTML structure
    html = (
        '<!DOCTYPE html>\n'
        '<html>\n'
        '<head>\n'
        f'  <title>{title}</title>\n'
        '</head>\n'
        '<body>\n'
        f'  <p>{badge}</p>\n'
        f'  {action_link}\n'
        f'  {local_note}\n'
        f'  {tag_str}\n'
        f'  <p style="color:#9ca3af;font-size:11px;">Added {date_str}</p>\n'
        '</body>\n'
        '</html>'
    )
    return html


def create_page(token: str, section_id: str, item: dict) -> str | None:
    """Create a OneNote page for a library item. Returns page ID or None."""
    requests = _get_requests()

    html = _build_page_html(item)

    try:
        resp = requests.post(
            f"{GRAPH_BASE}/me/onenote/sections/{section_id}/pages",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "text/html",
            },
            data=html.encode("utf-8"),
            timeout=30,
        )
        resp.raise_for_status()
        page_data = resp.json()
        return page_data.get("id")
    except Exception as e:
        print(f"  Error creating OneNote page for '{item.get('title')}': {e}")
        return None


def sync_to_onenote(items: list[dict] | None = None):
    """Sync library items to OneNote. Only syncs items not yet synced.

    Args:
        items: Items to sync. If None, syncs all unsynced items from library.

    Returns:
        Number of items synced.
    """
    from readlater.library import _load_library, _save_library

    token = authenticate()
    section_id = _ensure_section(token)

    library = _load_library()
    synced_ids = {i.get("onenote_page_id") for i in library if i.get("onenote_page_id")}

    # Determine which items to sync
    if items is not None:
        to_sync = items
    else:
        to_sync = [i for i in library if not i.get("onenote_page_id")]

    if not to_sync:
        print("Everything is already synced to OneNote.")
        return 0

    print(f"Syncing {len(to_sync)} item(s) to OneNote...")
    count = 0
    for item in to_sync:
        page_id = create_page(token, section_id, item)
        if page_id:
            # Update the item in the library with the OneNote page ID
            for lib_item in library:
                if lib_item["id"] == item["id"]:
                    lib_item["onenote_page_id"] = page_id
                    break
            count += 1
            print(f"  + {item.get('title', 'Untitled')}")

    _save_library(library)
    print(f"\nSynced {count} item(s) to OneNote 'Reading List' section.")
    return count


def configure_onenote(client_id: str):
    """Store the Azure AD client ID in config."""
    config = get_config()
    config.setdefault("onenote", {})["client_id"] = client_id
    save_config(config)
    print(f"OneNote client ID saved.\n")
    print("Now authenticate by running:")
    print("  readlater sync-onenote")
    print("\nThis will open a browser sign-in the first time.")
