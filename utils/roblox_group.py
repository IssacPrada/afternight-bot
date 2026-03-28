"""
utils/roblox_group.py — Roblox group management via .ROBLOSECURITY cookie
"""
import aiohttp
import os

COOKIE   = os.getenv("ROBLOX_SECURITY_COOKIE")
GROUP_ID = int(os.getenv("ROBLOX_GROUP_ID", "127271910"))

HEADERS = {
    "Cookie": f".ROBLOSECURITY={COOKIE}",
    "Content-Type": "application/json",
}


async def get_xcsrf_token() -> str:
    """Get a fresh XCSRF token required for POST/DELETE requests."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://auth.roblox.com/v2/logout",
            headers=HEADERS
        ) as resp:
            return resp.headers.get("x-csrf-token", "")


async def get_roblox_user_id(username: str) -> int | None:
    """Look up a Roblox user ID by username."""
    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://users.roblox.com/v1/usernames/users",
            json={"usernames": [username], "excludeBannedUsers": False},
            headers=HEADERS
        ) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            users = data.get("data", [])
            return users[0]["id"] if users else None


async def exile_from_group(roblox_username: str) -> tuple[bool, str]:
    """
    Exile (kick) a user from the Roblox group.
    Returns (success, message).
    """
    if not COOKIE:
        return False, "ROBLOX_SECURITY_COOKIE is not set in .env"

    user_id = await get_roblox_user_id(roblox_username)
    if not user_id:
        return False, f"Could not find Roblox user: `{roblox_username}`"

    try:
        token = await get_xcsrf_token()
        headers = {**HEADERS, "x-csrf-token": token}

        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"https://groups.roblox.com/v1/groups/{GROUP_ID}/users/{user_id}",
                headers=headers
            ) as resp:
                if resp.status == 200:
                    return True, f"✅ `{roblox_username}` has been exiled from the group."
                else:
                    error = await resp.json()
                    msg = error.get("errors", [{}])[0].get("message", "Unknown error")
                    return False, f"❌ Roblox API error: {msg}"

    except Exception as e:
        return False, f"❌ Exception: {str(e)}"