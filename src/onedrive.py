"""
OneDrive connector using Microsoft Graph API.

Authenticates via device code flow (user logs in through browser),
then lists and downloads files from OneDrive for ingestion into
the knowledge base.
"""

import os
import json
import requests
import msal
from typing import List, Optional

from src.config import MICROSOFT_CLIENT_ID, MICROSOFT_SCOPES, DOCS_DIR

# Microsoft Graph API base URL
GRAPH_API = "https://graph.microsoft.com/v1.0"

# Token cache file for persistent auth
TOKEN_CACHE_FILE = ".ms_token_cache.json"

# Supported file types for download
SUPPORTED_EXTENSIONS = [".txt", ".pdf", ".md", ".docx", ".pptx", ".xlsx"]


def _get_token_cache() -> msal.SerializableTokenCache:
    """Load or create a persistent token cache."""
    cache = msal.SerializableTokenCache()
    if os.path.exists(TOKEN_CACHE_FILE):
        with open(TOKEN_CACHE_FILE, "r") as f:
            cache.deserialize(f.read())
    return cache


def _save_token_cache(cache: msal.SerializableTokenCache):
    """Save the token cache to disk."""
    if cache.has_state_changed:
        with open(TOKEN_CACHE_FILE, "w") as f:
            f.write(cache.serialize())


def _get_msal_app() -> msal.PublicClientApplication:
    """Create an MSAL public client application."""
    cache = _get_token_cache()
    app = msal.PublicClientApplication(
        MICROSOFT_CLIENT_ID,
        authority="https://login.microsoftonline.com/common",
        token_cache=cache,
    )
    return app


def get_access_token() -> Optional[str]:
    """
    Get a valid access token, using cached token if available.
    
    Returns None if no cached token exists (user needs to authenticate).
    """
    app = _get_msal_app()
    accounts = app.get_accounts()

    if accounts:
        result = app.acquire_token_silent(MICROSOFT_SCOPES, account=accounts[0])
        if result and "access_token" in result:
            _save_token_cache(app.token_cache)
            return result["access_token"]

    return None


def start_device_code_auth() -> dict:
    """
    Start the device code authentication flow.
    
    Returns a dict with 'user_code' and 'message' for the user
    to complete authentication in their browser.
    """
    app = _get_msal_app()
    flow = app.initiate_device_flow(scopes=MICROSOFT_SCOPES)

    if "user_code" not in flow:
        raise Exception(f"Failed to start auth flow: {flow.get('error_description', 'Unknown error')}")

    return flow


def complete_device_code_auth(flow: dict, timeout: int = 120) -> str:
    """
    Complete the device code authentication flow after user has
    entered the code in their browser.
    
    Returns the access token.
    """
    import time

    app = _get_msal_app()
    
    # Poll with proper interval as required by OAuth spec
    interval = flow.get("interval", 5)
    deadline = time.time() + timeout
    
    while time.time() < deadline:
        time.sleep(interval)
        result = app.acquire_token_by_device_flow(flow)
        
        if "access_token" in result:
            _save_token_cache(app.token_cache)
            return result["access_token"]
        
        if result.get("error") == "authorization_pending":
            continue
        
        if result.get("error"):
            raise Exception(f"Authentication failed: {result.get('error_description', result['error'])}")
    
    raise Exception("Authentication timed out. Please try again.")

def get_user_info(token: str) -> dict:
    """Get the authenticated user's profile info."""
    response = requests.get(
        f"{GRAPH_API}/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    response.raise_for_status()
    return response.json()


def list_folder(token: str, folder_path: str = "/") -> List[dict]:
    """
    List files and folders in a OneDrive directory.
    
    Args:
        token: Microsoft Graph access token.
        folder_path: Path relative to OneDrive root (e.g., "/Documents/AI Projects").
        
    Returns:
        List of dicts with file/folder info.
    """
    if folder_path == "/":
        url = f"{GRAPH_API}/me/drive/root/children"
    else:
        # Remove leading slash for API compatibility
        clean_path = folder_path.strip("/")
        url = f"{GRAPH_API}/me/drive/root:/{clean_path}:/children"

    items = []
    headers = {"Authorization": f"Bearer {token}"}

    while url:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()

        for item in data.get("value", []):
            item_info = {
                "id": item["id"],
                "name": item["name"],
                "size": item.get("size", 0),
                "is_folder": "folder" in item,
                "modified": item.get("lastModifiedDateTime", ""),
                "download_url": item.get("@microsoft.graph.downloadUrl", ""),
                "path": f"{folder_path.rstrip('/')}/{item['name']}",
            }

            if not item_info["is_folder"]:
                ext = os.path.splitext(item["name"])[1].lower()
                item_info["supported"] = ext in SUPPORTED_EXTENSIONS
                item_info["extension"] = ext
            else:
                item_info["supported"] = False
                item_info["extension"] = ""
                item_info["child_count"] = item.get("folder", {}).get("childCount", 0)

            items.append(item_info)

        # Handle pagination
        url = data.get("@odata.nextLink")

    return items


def download_file(token: str, file_id: str, filename: str, destination: str = DOCS_DIR) -> str:
    """
    Download a file from OneDrive to the local docs directory.
    
    Args:
        token: Microsoft Graph access token.
        file_id: OneDrive file ID.
        filename: Name to save the file as.
        destination: Local directory to save to.
        
    Returns:
        Local file path of the downloaded file.
    """
    os.makedirs(destination, exist_ok=True)

    # Get download URL
    response = requests.get(
        f"{GRAPH_API}/me/drive/items/{file_id}/content",
        headers={"Authorization": f"Bearer {token}"},
        allow_redirects=False,
    )

    if response.status_code == 302:
        download_url = response.headers["Location"]
        file_response = requests.get(download_url)
    else:
        file_response = response

    file_response.raise_for_status()

    file_path = os.path.join(destination, filename)
    with open(file_path, "wb") as f:
        f.write(file_response.content)

    return file_path


def download_folder(token: str, folder_path: str, destination: str = DOCS_DIR) -> List[str]:
    """
    Download all supported files from a OneDrive folder.
    
    Args:
        token: Microsoft Graph access token.
        folder_path: OneDrive folder path.
        destination: Local directory to save to.
        
    Returns:
        List of local file paths that were downloaded.
    """
    items = list_folder(token, folder_path)
    downloaded = []

    for item in items:
        if item["is_folder"]:
            continue
        if not item.get("supported", False):
            continue

        try:
            file_path = download_file(token, item["id"], item["name"], destination)
            downloaded.append(file_path)
        except Exception as e:
            print(f"Error downloading {item['name']}: {e}")

    return downloaded


def disconnect():
    """Remove cached tokens to disconnect from OneDrive."""
    if os.path.exists(TOKEN_CACHE_FILE):
        os.remove(TOKEN_CACHE_FILE)