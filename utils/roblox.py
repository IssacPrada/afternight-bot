"""
utils/roblox.py — Roblox API helpers for fetching user info, avatars, and group members.
"""
import aiohttp
import os
from typing import Optional, Dict, Any, List

ROBLOX_API        = "https://users.roblox.com/v1"
ROBLOX_THUMB_API  = "https://thumbnails.roblox.com/v1"
ROBLOX_GROUP_API  = "https://groups.roblox.com/v1"
GROUP_ID          = int(os.getenv("ROBLOX_GROUP_ID", "127271910"))

# Rank numbers → faction names
RANK_TO_FACTION = {
    10: "Sanguis Order",
    20: "Eldritch Thorn",
    30: "Silver Venom",
    40: "Sepharine Coven",
}


async def fetch_roblox_user(username: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a Roblox user by username.
    Returns dict with id, name, displayName, avatar_url — or None on failure.
    """
    try:
        async with aiohttp.ClientSession() as session:
            # Username → ID
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

            # Full profile
            async with session.get(f"{ROBLOX_API}/users/{user_id}") as resp:
                if resp.status != 200:
                    return None
                profile = await resp.json()

            # Avatar thumbnail
            async with session.get(
                f"{ROBLOX_THUMB_API}/users/avatar-headshot",
                params={"userIds": user_id, "size": "150x150", "format": "Png"}
            ) as resp:
                avatar_url = None
                if resp.status == 200:
                    thumb_data = await resp.json()
                    thumbs = thumb_data.get("data", [])
                    if thumbs:
                        avatar_url = thumbs[0].get("imageUrl")

            return {
                "id":          user_id,
                "name":        profile.get("name"),
                "displayName": profile.get("displayName"),
                "avatar_url":  avatar_url,
            }

    except Exception:
        return None


async def fetch_roblox_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a Roblox user by their ID."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{ROBLOX_API}/users/{user_id}") as resp:
                if resp.status != 200:
                    return None
                return await resp.json()
    except Exception:
        return None


async def fetch_group_members_by_rank(rank: int) -> List[Dict[str, Any]]:
    """
    Fetch all members of the group with a specific rank number.
    Handles pagination automatically.
    Returns list of dicts with userId, username, displayName.
    """
    members = []
    cursor = ""

    try:
        async with aiohttp.ClientSession() as session:
            # First get the roleId for this rank number
            async with session.get(
                f"{ROBLOX_GROUP_API}/groups/{GROUP_ID}/roles"
            ) as resp:
                if resp.status != 200:
                    return []
                roles_data = await resp.json()
                role_id = None
                for role in roles_data.get("roles", []):
                    if role["rank"] == rank:
                        role_id = role["id"]
                        break

            if not role_id:
                return []

            # Paginate through all members with this role
            while True:
                params = {"limit": 100, "sortOrder": "Asc"}
                if cursor:
                    params["cursor"] = cursor

                async with session.get(
                    f"{ROBLOX_GROUP_API}/groups/{GROUP_ID}/roles/{role_id}/users",
                    params=params
                ) as resp:
                    if resp.status != 200:
                        break
                    data = await resp.json()
                    for member in data.get("data", []):
                        members.append({
                            "userId":      member["userId"],
                            "username":    member["username"],
                            "displayName": member["displayName"],
                        })
                    cursor = data.get("nextPageCursor")
                    if not cursor:
                        break

    except Exception:
        pass

    return members


async def fetch_faction_members(faction: str) -> List[Dict[str, Any]]:
    """
    Fetch all Roblox group members for a given faction name.
    Uses RANK_TO_FACTION to find the right rank.
    """
    rank = next((r for r, f in RANK_TO_FACTION.items() if f == faction), None)
    if rank is None:
        return []
    return await fetch_group_members_by_rank(rank)


async def fetch_player_rank_in_group(user_id: int) -> Optional[int]:
    """Get a player's rank number in the group."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{ROBLOX_GROUP_API}/users/{user_id}/groups/roles"
            ) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                for group in data.get("data", []):
                    if group["group"]["id"] == GROUP_ID:
                        return group["role"]["rank"]
    except Exception:
        pass
    return None