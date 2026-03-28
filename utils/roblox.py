"""
utils/roblox.py — Roblox API helpers for fetching user info & avatars.
"""
import aiohttp
from typing import Optional, Dict, Any

ROBLOX_API = "https://users.roblox.com/v1"
ROBLOX_THUMBNAIL_API = "https://thumbnails.roblox.com/v1"


async def fetch_roblox_user(username: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a Roblox user by username.
    Returns a dict with id, name, displayName, avatar_url — or None on failure.
    """
    try:
        async with aiohttp.ClientSession() as session:
            # Username → ID lookup
            async with session.post(
                f"{ROBLOX_API}/usernames/users",
                json={"usernames": [username], "excludeBannedUsers": False}
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                users = data.get("data", [])
                if not users:
                    return None
                user = users[0]

            user_id = user["id"]

            # Fetch full profile
            async with session.get(f"{ROBLOX_API}/users/{user_id}") as resp:
                if resp.status != 200:
                    return None
                profile = await resp.json()

            # Fetch avatar thumbnail
            async with session.get(
                f"{ROBLOX_THUMBNAIL_API}/users/avatar-headshot",
                params={"userIds": user_id, "size": "150x150", "format": "Png"}
            ) as resp:
                avatar_url = None
                if resp.status == 200:
                    thumb_data = await resp.json()
                    thumbs = thumb_data.get("data", [])
                    if thumbs:
                        avatar_url = thumbs[0].get("imageUrl")

            return {
                "id": user_id,
                "name": profile.get("name"),
                "displayName": profile.get("displayName"),
                "avatar_url": avatar_url,
            }

    except Exception:
        return None
