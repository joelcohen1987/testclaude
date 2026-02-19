"""Monday.com integration via their GraphQL API.

Creates items on a Monday.com board to track your reading list.
Setup is simple — just an API token from your Monday.com account.
"""

import json
import sys
import urllib.request
import urllib.error
from datetime import datetime

from readlater.config import get_config, save_config

MONDAY_API_URL = "https://api.monday.com/v2"


def _get_monday_config():
    """Get Monday.com config, exit with instructions if not set up."""
    config = get_config()
    monday = config.get("monday", {})
    if not monday.get("api_token"):
        print(
            "Error: Monday.com not configured yet.\n"
            "Run:  readlater config-monday --api-token <YOUR_TOKEN>\n"
        )
        _print_setup_instructions()
        sys.exit(1)
    return monday


def _print_setup_instructions():
    """Print Monday.com setup instructions."""
    print(
        "\n"
        "=== Monday.com Setup (one-time, ~2 minutes) ===\n"
        "\n"
        "1. Log in to monday.com\n"
        "\n"
        "2. Click your avatar (bottom-left) → Administration\n"
        "   → Connections → API\n"
        "   Or go directly to: your-domain.monday.com/admin/integrations/api\n"
        "\n"
        "3. Under 'Personal API Token', click 'Show' and copy it\n"
        "\n"
        "4. Run:\n"
        "   readlater config-monday --api-token <paste-your-token>\n"
        "\n"
        "That's it! The first sync will create a 'Reading List' board\n"
        "automatically.\n"
    )


def _monday_query(api_token: str, query: str, variables: dict | None = None) -> dict:
    """Execute a Monday.com GraphQL query."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        MONDAY_API_URL,
        data=data,
        headers={
            "Authorization": api_token,
            "Content-Type": "application/json",
            "API-Version": "2024-10",
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"Monday.com API error ({e.code}): {body}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Monday.com connection error: {e.reason}")
        sys.exit(1)

    if "errors" in result:
        msgs = [err.get("message", str(err)) for err in result["errors"]]
        print(f"Monday.com API error: {'; '.join(msgs)}")
        sys.exit(1)

    return result.get("data", {})


def _ensure_board(api_token: str) -> str:
    """Get or create the 'Reading List' board. Returns board ID."""
    config = get_config()
    board_id = config.get("monday", {}).get("board_id")

    # If cached, verify it still exists
    if board_id:
        data = _monday_query(api_token, """
            query ($ids: [ID!]) {
                boards(ids: $ids) { id }
            }
        """, {"ids": [board_id]})
        if data.get("boards"):
            return board_id

    # Search for existing board by name
    data = _monday_query(api_token, """
        query {
            boards(limit: 200) {
                id
                name
            }
        }
    """)
    for board in data.get("boards", []):
        if board["name"] == "Reading List":
            board_id = board["id"]
            config.setdefault("monday", {})["board_id"] = board_id
            save_config(config)
            return board_id

    # Create a new board with the right columns
    data = _monday_query(api_token, """
        mutation ($name: String!) {
            create_board(
                board_name: $name,
                board_kind: public
            ) {
                id
            }
        }
    """, {"name": "Reading List"})
    board_id = data["create_board"]["id"]

    # Add custom columns: Type, Source URL, Date Added, Status
    for col_title, col_type in [
        ("Type", "text"),
        ("Source URL", "link"),
        ("Date Added", "date"),
    ]:
        _monday_query(api_token, """
            mutation ($boardId: ID!, $title: String!, $colType: ColumnType!) {
                create_column(
                    board_id: $boardId,
                    title: $title,
                    column_type: $colType
                ) {
                    id
                }
            }
        """, {"boardId": board_id, "title": col_title, "colType": col_type})

    config.setdefault("monday", {})["board_id"] = board_id
    save_config(config)
    print(f"Created 'Reading List' board on Monday.com.\n")
    return board_id


def _get_column_ids(api_token: str, board_id: str) -> dict:
    """Get column IDs for the board. Returns mapping of title -> id."""
    data = _monday_query(api_token, """
        query ($boardId: [ID!]) {
            boards(ids: $boardId) {
                columns {
                    id
                    title
                }
            }
        }
    """, {"boardId": [board_id]})

    columns = {}
    for col in data.get("boards", [{}])[0].get("columns", []):
        columns[col["title"]] = col["id"]
    return columns


def create_item(api_token: str, board_id: str, item: dict) -> str | None:
    """Create a Monday.com item for a library item. Returns item ID or None."""
    title = item.get("title", "Untitled")
    content_type = item.get("type", "pdf").upper()
    source_url = item.get("source_url", "")
    added = item.get("added", "")

    # Get column IDs
    columns = _get_column_ids(api_token, board_id)

    # Build column values
    col_values = {}

    if "Type" in columns:
        col_values[columns["Type"]] = content_type

    if "Source URL" in columns and source_url:
        col_values[columns["Source URL"]] = {"url": source_url, "text": source_url}

    if "Date Added" in columns and added:
        try:
            dt = datetime.fromisoformat(added)
            col_values[columns["Date Added"]] = {"date": dt.strftime("%Y-%m-%d")}
        except (ValueError, TypeError):
            pass

    try:
        data = _monday_query(api_token, """
            mutation ($boardId: ID!, $itemName: String!, $colValues: JSON!) {
                create_item(
                    board_id: $boardId,
                    item_name: $itemName,
                    column_values: $colValues
                ) {
                    id
                }
            }
        """, {
            "boardId": board_id,
            "itemName": title,
            "colValues": json.dumps(col_values),
        })
        return data["create_item"]["id"]
    except Exception as e:
        print(f"  Error creating Monday.com item for '{title}': {e}")
        return None


def sync_to_monday(items: list[dict] | None = None):
    """Sync library items to Monday.com. Only syncs items not yet synced.

    Args:
        items: Items to sync. If None, syncs all unsynced items from library.

    Returns:
        Number of items synced.
    """
    from readlater.library import _load_library, _save_library

    monday_config = _get_monday_config()
    api_token = monday_config["api_token"]
    board_id = _ensure_board(api_token)

    library = _load_library()

    # Determine which items to sync
    if items is not None:
        to_sync = items
    else:
        to_sync = [i for i in library if not i.get("monday_item_id")]

    if not to_sync:
        print("Everything is already synced to Monday.com.")
        return 0

    print(f"Syncing {len(to_sync)} item(s) to Monday.com...")
    count = 0
    for item in to_sync:
        monday_id = create_item(api_token, board_id, item)
        if monday_id:
            # Update the item in the library with the Monday.com item ID
            for lib_item in library:
                if lib_item["id"] == item["id"]:
                    lib_item["monday_item_id"] = monday_id
                    break
            count += 1
            print(f"  + {item.get('title', 'Untitled')}")

    _save_library(library)
    print(f"\nSynced {count} item(s) to Monday.com 'Reading List' board.")
    return count


def configure_monday(api_token: str):
    """Store the Monday.com API token in config."""
    config = get_config()
    config.setdefault("monday", {})["api_token"] = api_token
    save_config(config)

    # Verify the token works
    print("Verifying API token...")
    data = _monday_query(api_token, "query { me { name email } }")
    me = data.get("me", {})
    name = me.get("name", "Unknown")
    email = me.get("email", "")

    print(f"Authenticated as: {name} ({email})")
    print(f"\nMonday.com configured. Run 'readlater sync-monday' to sync your list.")
