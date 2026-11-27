"""
cogs/faction_apps.py — Complete multi-faction DM application, review, and passer confirmation system.
"""
import asyncio
import datetime
import json
import re
from typing import Any, Optional

import discord
from discord import app_commands
from discord.ext import commands

import constants


def _const(name: str, default: Any = None) -> Any:
    return getattr(constants, name, default)


# ── Role Helpers ──────────────────────────────────────────────────────────────

MEMBERS_ROLE_ID: Optional[int] = _const("MEMBERS_ROLE_ID") or _const("MEMBER_ROLE_ID")

HIGH_STAFF_ROLE_IDS: set[int] = {
    rid
    for rid in (
        _const("OWNER_ROLE_ID"),
        _const("CO_OWNER_ROLE_ID"),
        _const("COMMUNITY_MANAGER_ROLE_ID"),
        _const("CM_ROLE_ID"),
    )
    if isinstance(rid, int)
}

HIGH_STAFF_ROLE_NAMES = {
    "[o] owner.",
    "[co-o] co-owner.",
    "[cm] community manager",
    "owner",
    "co-owner",
    "community manager",
}

FACTION_LEADER_ROLE_MAP: dict[str, set[int]] = {
    "Eldritch Thorn": {
        rid
        for rid in (
            _const("ELDRITCH_LEADER_ROLE_ID"),
            _const("ELDRITCH_OVERSEER_ROLE_ID"),
            (_const("FACTION_LEADERS") or {}).get("Eldritch Thorn"),
            (_const("FACTION_OVERSEERS") or {}).get("Eldritch Thorn"),
        )
        if isinstance(rid, int)
    },
    "Sanguis Order": {
        rid
        for rid in (
            _const("SANGUIS_LEADER_ROLE_ID"),
            _const("SANGUIS_OVERSEER_ROLE_ID"),
            (_const("FACTION_LEADERS") or {}).get("Sanguis Order"),
            (_const("FACTION_OVERSEERS") or {}).get("Sanguis Order"),
        )
        if isinstance(rid, int)
    },
    "SilverVenom": {
        rid
        for rid in (
            _const("SILVERVENOM_LEADER_ROLE_ID"),
            _const("SILVERVENOM_OVERSEER_ROLE_ID"),
            (_const("FACTION_LEADERS") or {}).get("SilverVenom"),
            (_const("FACTION_OVERSEERS") or {}).get("SilverVenom"),
        )
        if isinstance(rid, int)
    },
    "Sepharine Coven": {
        rid
        for rid in (
            _const("SEPHARINE_LEADER_ROLE_ID"),
            _const("SEPHARINE_OVERSEER_ROLE_ID"),
            (_const("FACTION_LEADERS") or {}).get("Sepharine Coven"),
            (_const("FACTION_OVERSEERS") or {}).get("Sepharine Coven"),
        )
        if isinstance(rid, int)
    },
}

FACTION_ROLE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Eldritch Thorn": ("eldritch",),
    "Sanguis Order": ("sanguis",),
    "SilverVenom": ("silvervenom", "silver venom"),
    "Sepharine Coven": ("sephar", "seraph"),
}


def has_high_staff(member: discord.Member) -> bool:
    for role in member.roles:
        if role.id in HIGH_STAFF_ROLE_IDS:
            return True
        if role.name.strip().lower() in HIGH_STAFF_ROLE_NAMES:
            return True
    return member.guild_permissions.administrator


def can_manage_faction_apps(member: discord.Member, faction: str) -> bool:
    if has_high_staff(member):
        return True

    allowed_ids = FACTION_LEADER_ROLE_MAP.get(faction, set())
    keywords = FACTION_ROLE_KEYWORDS.get(faction, ())
    for role in member.roles:
        if role.id in allowed_ids:
            return True
        rname = role.name.lower()
        if any(kw in rname for kw in keywords) and ("leader" in rname or "overseer" in rname):
            return True
    return False


def get_manageable_factions(member: discord.Member) -> list[str]:
    return [f for f in FACTIONS_CONFIG if can_manage_faction_apps(member, f)]


# ── Faction Configurations, Questions & Announcements ─────────────────────────

FACTIONS_CONFIG: dict[str, dict[str, Any]] = {
    "Eldritch Thorn": {
        "key": "eldritch",
        "color": 0x4B0082,
        "emoji": "🕯️",
        "announce_channel_id": 1575221439005466716,
        "review_channel_id": 1575754174849618111,
        "max_warnings": 3,
        "intro": (
            "**Eldritch Thorn Faction Applications**\n"
            "Hello fellow newbie witch! This application will go through and test your inner strength "
            "and worthy to the witch coven. If you are able to complete each question with true honesty "
            "about yourself you will be considered into the faction! Please read all the requirements "
            "before you have proceeded to the next section.\n\n"
            "• **Level 10** in the server.\n"
            "• **No more than 3 warnings.**\n"
            "• **Not engaged in drama** within the server and game.\n\n"
            "⚠️ *If you appear to be trolling in the sacred applications you will be blacklisted.*"
        ),
        "outro": (
            "**End of The Trials!**\n"
            "CONGRATULATIONS YOU HAVE COMPLETED THE QUESTION TRIALS! If you have any question don't be "
            "afraid to dm or ping the leader of the faction! You can now submit your application and I wish you luck!"
        ),
        "announcement_template": (
            "{ping}\n"
            "𖤐 THE WAIT IS OVER… APPLICATIONS ARE NOW OPEN. 𖤐\n"
            "╭・🕯️・━━━━━━━━━━━━━━・🕯️・╮\n"
            "༺ 𝐄𝐋𝐃𝐑𝐈𝐓𝐂𝐇 𝐓𝐇𝐎𝐑𝐍 ༻\n"
            "The whispers have grown louder, the shadows have begun to stir, and the gates of the coven have finally opened.\n"
            "We are pleased to announce that applications for Eldritch Thorn Coven are officially OPEN!\n"
            "Are you ready to step into a world of magic, and enchantment? Whether you're drawn to the witchcraft, "
            "the unknown, or simply wish to find your place among us, this may be your calling.\n"
            "𖤐 WHAT WE'RE LOOKING FOR:\n"
            "- Dedicated and active members.\n"
            "- Respectful and welcoming individuals.\n"
            "- Those willing to participate in coven activities.\n"
            "- Creative souls ready to contribute to our community.\n"
            "𖤐 HOW TO APPLY:\n"
            "Click the **Apply to Eldritch Thorn** button below (or use `/factionapply`) to begin your DM trials! "
            "You will have **30 minutes** per question.\n"
            "Remember, not everyone who knocks will be invited inside…\n"
            "Will you answer the call?\n"
            "╰・🕯️・━━━━━━━━━━━━━━・🕯️・╯\n"
            "𖤐 The thorns await. The coven calls. It is up to you weary one."
        ),
        "questions": [
            {
                "id": "roblox_username",
                "section": "Basic Information",
                "section_note": None,
                "prompt": "1. What is your Roblox username?",
                "type": "short",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "timezone",
                "section": "Basic Information",
                "section_note": None,
                "prompt": "2. What is your time zone?",
                "type": "short",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "why_join",
                "section": "Trial of Character",
                "section_note": (
                    "We will now be moving onto the **Trial of Character** part of the application. "
                    "Please answer this to your best ability and **use 0 AI** on these questions or you will be blacklisted from our applications."
                ),
                "prompt": "1. Why do you want to join the Eldritch Thorn Coven?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "provide",
                "section": "Trial of Character",
                "section_note": None,
                "prompt": "2. What will you provide for the coven?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "strengths_weaknesses",
                "section": "Trial of Character",
                "section_note": None,
                "prompt": "3. What are your weaknesses and strengths?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "stand_out",
                "section": "Trial of Character",
                "section_note": None,
                "prompt": "4. What makes your application stand out from other witches wanting to join this coven?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "prior_experience",
                "section": "Trial of Character",
                "section_note": None,
                "prompt": "5. Have you applied for a faction before? If so tell me the experience you had! If you haven't then leave it blank.",
                "type": "text",
                "max_sentences": None,
                "optional": True,
            },
            {
                "id": "abuse_power",
                "section": "Trial of Consciousness",
                "section_note": (
                    "**Trial of Consciousness**\n"
                    "Well done! You have made it through the Trial of Character. Now for this section you will need to answer "
                    "about how you will be aware of everything and your surroundings!"
                ),
                "prompt": "1. If you saw a fellow brother/sister of the coven abusing their power, what will you do?",
                "type": "text",
                "max_sentences": 2,
                "optional": False,
            },
            {
                "id": "starting_problems",
                "section": "Trial of Consciousness",
                "section_note": None,
                "prompt": "2. If a sister/brother of the coven was starting problems or issues, what will you do?",
                "type": "text",
                "max_sentences": 2,
                "optional": False,
            },
            {
                "id": "breaking_rules",
                "section": "Trial of Consciousness",
                "section_note": None,
                "prompt": "3. If a sister/brother was breaking rules of the coven and breaking the rules in game, what will you do?",
                "type": "text",
                "max_sentences": 2,
                "optional": False,
            },
            {
                "id": "roblox_activity",
                "section": "Trial of Perfection (Last Trial)",
                "section_note": (
                    "**Trial of Perfection (Last Trial)**\n"
                    "You have made it to the last trial my friend. Now for this trial you will just need to answer "
                    "a few scale/final questions and you will be done making your application for the sacred coven."
                ),
                "prompt": "1. How active are you on Roblox? (Scale out of 1–10)",
                "type": "scale",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "discord_activity",
                "section": "Trial of Perfection (Last Trial)",
                "section_note": None,
                "prompt": "2. How active are you on Discord? (Scale out of 1–10)",
                "type": "scale",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "extra_questions",
                "section": "Trial of Perfection (Last Trial)",
                "section_note": None,
                "prompt": "3. Do you have any questions? If not leave it blank!",
                "type": "text",
                "max_sentences": None,
                "optional": True,
            },
        ],
    },
    "Sanguis Order": {
        "key": "sanguis",
        "color": 0x8B0000,
        "emoji": "🩸",
        "announce_channel_id": 1575221806137344010,
        "review_channel_id": 1575754290662866974,
        "max_warnings": 3,
        "intro": (
            "**Sanguis Order Faction Application**\n"
            "Hello fellow fledgling vampire! In this application you will be asked questions regarding your activity, "
            "strength, and dedication. **Please do not use any AI resource** as you will be blacklisted from ever applying "
            "to this faction and other applications. In Sanguis Order we offer the classiest family — a family of talented "
            "vampires that have lived on for centuries. You will find your time used valuably here at Sanguis Order! "
            "We wish you the best of luck applying to this faction!\n\n"
            "• **Level 10** in the server.\n"
            "• **No more than 3 warnings.**\n"
            "• **Not engaged in drama** within the server and game.\n\n"
            "⚠️ *If you appear to be trolling in the sacred applications you will be blacklisted.*"
        ),
        "outro": (
            "**THE END!**\n"
            "Congrats! You have come to the end of the application. If you have any questions or anything, "
            "don't be afraid to reach out to the house leader! We wish you good luck and hope for the best for you in the Sanguis Order faction!"
        ),
        "announcement_template": (
            "{ping}\n"
            "𖤍 THE BLOODLINE AWAKENS — APPLICATIONS ARE NOW OPEN. 🩸\n"
            "╭・🥀・━━━━━━━━━━━━━━・🥀・╮\n"
            "༺ 𝐒𝐀𝐍𝐆𝐔𝐈𝐒 𝐎𝐑𝐃𝐄𝐑 ༻\n"
            "“Blood is not merely what runs through our veins. It is our legacy, our power, and our eternal oath.”\n"
            "The night has arrived, and the crimson gates have been opened.\n"
            "The Sanguis Order is officially welcoming new applicants into its ranks. We seek those who possess loyalty, "
            "discipline, ambition, and the strength to uphold the traditions of our bloodline.\n"
            "To walk among us is to embrace the darkness, honor the blood, and pledge allegiance to something greater than yourself.\n"
            "🩸 WHAT WE SEEK:\n"
            "- Loyal and dedicated individuals.\n"
            "- Active and respectful members.\n"
            "- Those willing to uphold the Order's rules and traditions.\n"
            "- Individuals prepared to represent the faction with pride.\n"
            "- Those who understand the importance of unity and discipline.\n"
            "🥀 HOW TO JOIN:\n"
            "Click the **Apply to Sanguis Order** button below (or use `/factionapply`) to begin your DM application! "
            "You will have **30 minutes** per question.\n"
            "Choose your words carefully. Your application is your first impression.\n"
            "╰・🥀・━━━━━━━━━━━━━━・🥀・╯\n"
            "🩸 REMEMBER: Blood binds us. Loyalty defines us. Eternity remembers us.\n"
            "The Sanguis Order awaits its next generation."
        ),
        "questions": [
            {
                "id": "roblox_username",
                "section": "Basic Information",
                "section_note": None,
                "prompt": "1. What is your Roblox username?",
                "type": "short",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "why_join",
                "section": "Question Section 1",
                "section_note": (
                    "**Question Section 1**\n"
                    "⚠️ Please do not use any AI resource as you will be blacklisted from ever applying to this faction and other applications."
                ),
                "prompt": "1. Why do you want to join the Sanguis Order family?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "provide",
                "section": "Question Section 1",
                "section_note": None,
                "prompt": "2. What will you provide for our family?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "strengths_weaknesses",
                "section": "Question Section 1",
                "section_note": None,
                "prompt": "3. What are your strengths and weaknesses?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "stand_out",
                "section": "Question Section 1",
                "section_note": None,
                "prompt": "4. What makes your application better than other vampires that are willing to join our family?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "prior_experience",
                "section": "Question Section 1",
                "section_note": None,
                "prompt": "5. Have you joined a faction before? If so please tell us the experience!",
                "type": "text",
                "max_sentences": None,
                "optional": True,
            },
            {
                "id": "abuse_power",
                "section": "Section 3",
                "section_note": (
                    "**Section 3**\n"
                    "⚠️ Please do not use any AI resource as you will be blacklisted from ever applying to this faction and other applications."
                ),
                "prompt": "1. If you saw a family member abusing their power, what will you do?",
                "type": "text",
                "max_sentences": 2,
                "optional": False,
            },
            {
                "id": "disrespectful",
                "section": "Section 3",
                "section_note": None,
                "prompt": "2. If you see a family member being disrespectful, what will you do?",
                "type": "text",
                "max_sentences": 2,
                "optional": False,
            },
            {
                "id": "breaking_rules",
                "section": "Section 3",
                "section_note": None,
                "prompt": "3. If you see a family member breaking the rules of the game and breaking regulations of the faction, what will you do?",
                "type": "text",
                "max_sentences": 2,
                "optional": False,
            },
            {
                "id": "discord_activity",
                "section": "Section 4",
                "section_note": (
                    "**Section 4**\n"
                    "⚠️ Please do not use any AI resource as you will be blacklisted from ever applying to this faction and other applications."
                ),
                "prompt": "1. How active are you on Discord? (1–10 scale)",
                "type": "scale",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "roblox_activity",
                "section": "Section 4",
                "section_note": None,
                "prompt": "2. How active are you on Roblox? (1–10 scale)",
                "type": "scale",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "positivity",
                "section": "Section 4",
                "section_note": None,
                "prompt": "3. How positive are you about applying? (1–10 scale)",
                "type": "scale",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "extra_questions",
                "section": "Section 4",
                "section_note": None,
                "prompt": "4. Do you have any questions for us? If you don't then leave it blank!",
                "type": "text",
                "max_sentences": None,
                "optional": True,
            },
        ],
    },
    "SilverVenom": {
        "key": "silvervenom",
        "color": 0x708090,
        "emoji": "🐺",
        "announce_channel_id": 1575221885376139364,
        "review_channel_id": 1575754239295357049,
        "max_warnings": 3,
        "intro": (
            "**SilverVenom Faction Application**\n"
            "Hello fellow omega wolf! In this application you will be asked questions regarding your activity, strength, "
            "and dedication. **Please do not use any AI resource** as you will be blacklisted from ever applying to this "
            "faction and other applications. In SilverVenom we offer a lot of regulations in the pack — one of them is "
            "being peaceful with other factions. You will find a lot of fun and engagement within the SilverVenom pack! "
            "We do wish you good luck applying for this faction!\n\n"
            "• **Level 10** in the server.\n"
            "• **No more than 3 warnings.**\n"
            "• **Not engaged in drama** within the server and game.\n\n"
            "⚠️ *If you appear to be trolling in the sacred applications you will be blacklisted.*"
        ),
        "outro": (
            "**End of The Application!**\n"
            "Congrats! You have come to the end of the application. If you have any questions or anything, "
            "don't be afraid to reach out to the pack leader! We do wish you good luck and hope for the best for you in the SilverVenom faction!"
        ),
        "announcement_template": (
            "{ping}\n"
            "𖤐 THE HOWL HAS BEEN HEARD — APPLICATIONS ARE NOW OPEN. 🌙\n"
            "╭・🐺・━━━━━━━━━━━━━━・🐺・╮\n"
            "༺ 𝐒𝐈𝐋𝐕𝐄𝐑𝐕𝐄𝐍𝐎𝐌 ༻\n"
            "“We do not fear the darkness. We were born beneath its moon.”\n"
            "Under the silver glow of the moon, a new chapter begins. The forests stir, the winds carry our call, "
            "and the pack is ready to welcome new blood.\n"
            "SilverVenom is officially opening its applications to those willing to prove their loyalty, strength, and devotion to the pack.\n"
            "We are not simply a faction. We are a family bound by instinct, trust, and an unbreakable bond. "
            "To stand with us is to stand with your pack, through every hunt, every challenge, and every storm.\n"
            "🐺 WHAT WE SEEK:\n"
            "- Loyal and dedicated individuals.\n"
            "- Active and respectful pack members.\n"
            "- Those willing to follow pack rules and traditions.\n"
            "- Individuals with strong teamwork and communication.\n"
            "- Those ready to represent SilverVenom with pride.\n"
            "🌙 HOW TO APPLY:\n"
            "Click the **Apply to SilverVenom** button below (or use `/factionapply`) to begin your DM application! "
            "You will have **30 minutes** per question.\n"
            "Remember, strength may earn you a place at our side, but loyalty is what makes you one of us.\n"
            "╰・🐺・━━━━━━━━━━━━━━・🐺・╯\n"
            "𖤐 THE PACK STANDS UNITED.\n"
            "One moon. One pack. One unbreakable bond."
        ),
        "questions": [
            {
                "id": "roblox_username",
                "section": "Basic Information",
                "section_note": None,
                "prompt": "1. What is your Roblox username?",
                "type": "short",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "why_join",
                "section": "Section 2",
                "section_note": (
                    "**Section 2**\n"
                    "⚠️ If you appear to be trolling in the sacred applications you will be blacklisted."
                ),
                "prompt": "1. Why do you want to join the SilverVenom pack?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "provide",
                "section": "Section 2",
                "section_note": None,
                "prompt": "2. What will you provide for the pack?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "strengths_weaknesses",
                "section": "Section 2",
                "section_note": None,
                "prompt": "3. What are your weaknesses and strengths?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "stand_out",
                "section": "Section 2",
                "section_note": None,
                "prompt": "4. What makes your application stand out from other wolves wanting to join this pack?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "prior_experience",
                "section": "Section 2",
                "section_note": None,
                "prompt": "5. Do you have experience in a wolf pack or faction? If so tell us how it was!",
                "type": "text",
                "max_sentences": None,
                "optional": True,
            },
            {
                "id": "abuse_power",
                "section": "Section 3",
                "section_note": (
                    "**Section 3**\n"
                    "⚠️ If you appear to be trolling in the sacred applications you will be blacklisted."
                ),
                "prompt": "1. If you saw a fellow member of the pack abusing their power, what will you do?",
                "type": "text",
                "max_sentences": 2,
                "optional": False,
            },
            {
                "id": "disrespectful",
                "section": "Section 3",
                "section_note": None,
                "prompt": "2. If you saw a fellow member of the pack being disrespectful to other pack members, what will you do?",
                "type": "text",
                "max_sentences": 2,
                "optional": False,
            },
            {
                "id": "breaking_rules",
                "section": "Section 3",
                "section_note": None,
                "prompt": "3. If a member was breaking rules of the pack and breaking the rules in game, what will you do?",
                "type": "text",
                "max_sentences": 2,
                "optional": False,
            },
            {
                "id": "discord_activity",
                "section": "Section 4",
                "section_note": (
                    "**Section 4**\n"
                    "⚠️ If you appear to be trolling in the sacred applications you will be blacklisted."
                ),
                "prompt": "1. How active are you on Discord? (1–10 scale)",
                "type": "scale",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "roblox_activity",
                "section": "Section 4",
                "section_note": None,
                "prompt": "2. How active are you on Roblox? (1–10 scale)",
                "type": "scale",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "positivity",
                "section": "Section 4",
                "section_note": None,
                "prompt": "3. How positive are you about applying? (1–10 scale)",
                "type": "scale",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "extra_questions",
                "section": "Section 4",
                "section_note": None,
                "prompt": "4. Do you have any questions? If not leave it blank!",
                "type": "text",
                "max_sentences": None,
                "optional": True,
            },
        ],
    },
    "Sepharine Coven": {
        "key": "sephar",
        "color": 0xC0C0C0,
        "emoji": "🌙",
        "announce_channel_id": 1575221971661365501,
        "review_channel_id": 1575754120508211200,
        "max_warnings": 2,
        "intro": (
            "**Sepharine Faction Applications**\n"
            "Hello fellow vengeance seeker! This application will go through and test your inner strength "
            "and worthiness to the were-witch coven. If you are able to complete each question with true honesty "
            "about yourself you will be considered into the faction! Please read all the requirements before you "
            "proceed to the next section.\n\n"
            "• **Level 10** in the server.\n"
            "• **No more than 2 warnings.**\n"
            "• **Not engaged in drama** within the server and game.\n\n"
            "⚠️ *If you appear to be trolling in the sacred applications you will be blacklisted.*"
        ),
        "outro": (
            "**End of The Trials!**\n"
            "CONGRATULATIONS YOU HAVE COMPLETED THE QUESTION TRIALS! If you have any question don't be afraid "
            "to dm or ping the leader of the faction! You can now submit your application and I wish you luck!"
        ),
        "announcement_template": (
            "{ping}\n"
            "𖤐 THE MOON CALLS, THE MAGIC AWAKENS — APPLICATIONS ARE NOW OPEN. 🌙\n"
            "╭・🕯️・━━━━━━━━━━━━━━・🕯️・╮\n"
            "༺ 𝐒𝐄𝐏𝐇𝐀𝐑𝐈𝐍𝐄 𝐂𝐎𝐕𝐄𝐍 ༻\n"
            "“Born of ancient magic, bound by the moon, and blessed with the strength of the wild.”\n"
            "Beneath the silver moonlight, where ancient spells intertwine with primal instincts, the gates of Sepharine Coven have finally opened.\n"
            "We are delighted to announce that Sepharine Coven is officially accepting applications!\n"
            "A unique union of witchcraft and wolf-born nature, our coven seeks individuals who embody loyalty, wisdom, strength, and an unwavering devotion to their kin.\n"
            "We are more than magic and fangs. We are a bond forged through power, trust, and sisterhood. Every member carries a purpose, and every soul has a place beneath our moon.\n"
            "🌙 WHAT WE SEEK:\n"
            "- Loyal and dedicated individuals.\n"
            "- Active and respectful members.\n"
            "- Those willing to uphold our coven's traditions.\n"
            "- Individuals with a passion for magic and the supernatural.\n"
            "- Those who value unity, teamwork, and devotion.\n"
            "- Members ready to represent Sepharine Coven with pride.\n"
            "🕯️ HOW TO APPLY:\n"
            "Click the **Apply to Sepharine Coven** button below (or use `/factionapply`) to begin your DM trials! "
            "You will have **30 minutes** per question.\n"
            "Not all who possess magic are worthy of the coven. It takes more than power to belong.\n"
            "╰・🕯️・━━━━━━━━━━━━━━・🕯️・╯\n"
            "𖤐 OUR MAGIC IS ANCIENT. OUR BOND IS ETERNAL. OUR HOWL IS UNFORGETTABLE.\n"
            "Bound by blood, guided by magic, united beneath the moon."
        ),
        "questions": [
            {
                "id": "roblox_username",
                "section": "Basic Information",
                "section_note": None,
                "prompt": "1. What is your Roblox username?",
                "type": "short",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "timezone",
                "section": "Basic Information",
                "section_note": None,
                "prompt": "2. What is your time zone?",
                "type": "short",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "why_join",
                "section": "Trial of Character",
                "section_note": "**Trial of Character**\nPlease answer with true honesty.",
                "prompt": "1. Why do you want to join the Sepharine Coven?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "provide",
                "section": "Trial of Character",
                "section_note": None,
                "prompt": "2. What will you provide for the coven?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "strengths_weaknesses",
                "section": "Trial of Character",
                "section_note": None,
                "prompt": "3. What are your weaknesses and strengths?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "stand_out",
                "section": "Trial of Character",
                "section_note": None,
                "prompt": "4. What makes your application stand out from other applicants wanting to join this coven?",
                "type": "text",
                "max_sentences": 3,
                "optional": False,
            },
            {
                "id": "prior_experience",
                "section": "Trial of Character",
                "section_note": None,
                "prompt": "5. Have you applied for a faction before? If so tell me the experience you had! If you haven't then leave it blank.",
                "type": "text",
                "max_sentences": None,
                "optional": True,
            },
            {
                "id": "abuse_power",
                "section": "Trial of Consciousness",
                "section_note": (
                    "**Trial of Consciousness**\n"
                    "Well done! You have made it through the Trial of Character. Now for this section you will need to answer "
                    "about how you will be aware of everything and your surroundings!"
                ),
                "prompt": "1. If you saw a fellow brother/sister of the coven abusing their power, what will you do?",
                "type": "text",
                "max_sentences": 2,
                "optional": False,
            },
            {
                "id": "starting_problems",
                "section": "Trial of Consciousness",
                "section_note": None,
                "prompt": "2. If a sister/brother of the coven was starting problems or issues, what will you do?",
                "type": "text",
                "max_sentences": 2,
                "optional": False,
            },
            {
                "id": "breaking_rules",
                "section": "Trial of Consciousness",
                "section_note": None,
                "prompt": "3. If a sister/brother was breaking rules of the coven and breaking the rules in game, what will you do?",
                "type": "text",
                "max_sentences": 2,
                "optional": False,
            },
            {
                "id": "roblox_activity",
                "section": "Trial of Perfection (Last Trial)",
                "section_note": (
                    "**Trial of Perfection (Last Trial)**\n"
                    "You have made it to the last trial my friend. Now for this trial you will just need to answer "
                    "a few scale/final questions and you will be done making your application for the sacred coven."
                ),
                "prompt": "1. How active are you on Roblox? (1–10 scale)",
                "type": "scale",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "discord_activity",
                "section": "Trial of Perfection (Last Trial)",
                "section_note": None,
                "prompt": "2. How active are you on Discord? (1–10 scale)",
                "type": "scale",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "positivity",
                "section": "Trial of Perfection (Last Trial)",
                "section_note": None,
                "prompt": "3. How positive are you about applying? (1–10 scale)",
                "type": "scale",
                "max_sentences": None,
                "optional": False,
            },
            {
                "id": "extra_questions",
                "section": "Trial of Perfection (Last Trial)",
                "section_note": None,
                "prompt": "4. Do you have any questions? If not leave it blank!",
                "type": "text",
                "max_sentences": None,
                "optional": True,
            },
        ],
    },
}

FACTION_BY_KEY: dict[str, str] = {cfg["key"]: name for name, cfg in FACTIONS_CONFIG.items()}

SENTENCE_SPLIT_RE = re.compile(r"[.!?]+(?:\s+|$)")


def count_sentences(text: str) -> int:
    cleaned = text.strip()
    if not cleaned:
        return 0
    parts = [p.strip() for p in SENTENCE_SPLIT_RE.split(cleaned) if p.strip()]
    return max(1, len(parts))


# ── Persistent Storage (JSON file + DB-safe) ──────────────────────────────────
# Uses a local/volume JSON store so it works out-of-the-box regardless of SQLite/Postgres setup.
import os

STATE_FILE = os.getenv("FACTION_APPS_STATE_FILE", "faction_apps_state.json")


def _default_state() -> dict[str, Any]:
    return {
        "open_status": {f: False for f in FACTIONS_CONFIG},
        "announcement_messages": {},  # faction -> {"channel_id": int, "message_id": int}
        "roster_messages": {},        # faction -> {"channel_id": int, "message_id": int}
        "accepted_passers": {f: [] for f in FACTIONS_CONFIG},
        "blacklisted_users": {},      # str(user_id) -> {"reason": str, "by": int}
    }


def load_state() -> dict[str, Any]:
    if not os.path.exists(STATE_FILE):
        return _default_state()
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as fh:
            raw = json.load(fh)
        base = _default_state()
        for k, v in raw.items():
            if isinstance(v, dict) and isinstance(base.get(k), dict):
                base[k].update(v)
            else:
                base[k] = v
        return base
    except Exception:
        return _default_state()


def save_state(state: dict[str, Any]) -> None:
    tmp = f"{STATE_FILE}.tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2)
    os.replace(tmp, STATE_FILE)


# ── Persistent Views ──────────────────────────────────────────────────────────

class FactionApplyButton(discord.ui.Button):
    def __init__(self, faction: str, disabled: bool = False):
        cfg = FACTIONS_CONFIG[faction]
        super().__init__(
            label=f"Apply to {faction}" if not disabled else f"{faction} Applications Closed",
            emoji=cfg["emoji"],
            style=discord.ButtonStyle.success if not disabled else discord.ButtonStyle.secondary,
            custom_id=f"faction_apply:{cfg['key']}",
            disabled=disabled,
        )
        self.faction = faction

    async def callback(self, interaction: discord.Interaction):
        cog: Optional[FactionAppsCog] = interaction.client.get_cog("FactionAppsCog")
        if not cog:
            return await interaction.response.send_message(
                "❌ Faction application module is still loading.", ephemeral=True
            )
        await cog.start_dm_application(interaction, self.faction)


class FactionAnnouncementView(discord.ui.View):
    def __init__(self, faction: str, disabled: bool = False):
        super().__init__(timeout=None)
        self.add_item(FactionApplyButton(faction, disabled=disabled))


class ApplicationReviewView(discord.ui.View):
    """Attached to each submitted application embed in the faction's private review channel."""

    def __init__(self, faction: str, applicant_id: int, roblox_username: str):
        super().__init__(timeout=None)
        cfg = FACTIONS_CONFIG[faction]
        self.faction = faction
        self.applicant_id = applicant_id
        self.roblox_username = roblox_username

        accept_btn = discord.ui.Button(
            label="Accept",
            style=discord.ButtonStyle.success,
            emoji="✅",
            custom_id=f"fapp_accept:{cfg['key']}:{applicant_id}:{roblox_username[:40]}",
        )
        accept_btn.callback = self._on_accept

        deny_btn = discord.ui.Button(
            label="Deny",
            style=discord.ButtonStyle.danger,
            emoji="✖️",
            custom_id=f"fapp_deny:{cfg['key']}:{applicant_id}:{roblox_username[:40]}",
        )
        deny_btn.callback = self._on_deny

        self.add_item(accept_btn)
        self.add_item(deny_btn)

    async def _check_reviewer(self, interaction: discord.Interaction) -> bool:
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ Server context required.", ephemeral=True)
            return False
        if not can_manage_faction_apps(interaction.user, self.faction):
            await interaction.response.send_message(
                f"❌ Only **{self.faction}** Leaders/Overseers or High Staff can review this application.",
                ephemeral=True,
            )
            return False
        return True

    async def _on_accept(self, interaction: discord.Interaction):
        if not await self._check_reviewer(interaction):
            return
        cog: Optional[FactionAppsCog] = interaction.client.get_cog("FactionAppsCog")
        if not cog:
            return
        await cog.handle_accept_application(
            interaction=interaction,
            faction=self.faction,
            applicant_id=self.applicant_id,
            roblox_username=self.roblox_username,
        )

    async def _on_deny(self, interaction: discord.Interaction):
        if not await self._check_reviewer(interaction):
            return
        await interaction.response.defer(ephemeral=True)
        try:
            await interaction.message.delete()
        except discord.HTTPException:
            pass
        await interaction.followup.send(
            f"🗑️ Denied and deleted application from <@{self.applicant_id}> (`{self.roblox_username}`).",
            ephemeral=True,
        )


class RemovePasserSelect(discord.ui.Select):
    def __init__(self, faction: str, passers: list[dict[str, Any]]):
        cfg = FACTIONS_CONFIG[faction]
        options = [
            discord.SelectOption(
                label=f"{idx}. {p.get('display_name', p['user_id'])} ({p['roblox_username']})"[:100],
                value=str(p["user_id"]),
                description=f"Discord ID: {p['user_id']}"[:100],
            )
            for idx, p in enumerate(passers[:25], start=1)
        ]
        super().__init__(
            placeholder="Remove an accepted applicant (if clicked by mistake)...",
            min_values=1,
            max_values=1,
            options=options,
            custom_id=f"fapp_remove_passer:{cfg['key']}",
        )
        self.faction = faction

    async def callback(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not can_manage_faction_apps(
            interaction.user, self.faction
        ):
            return await interaction.response.send_message(
                "❌ Only faction leaders/overseers or High Staff can edit the accepted roster.",
                ephemeral=True,
            )
        cog: Optional[FactionAppsCog] = interaction.client.get_cog("FactionAppsCog")
        if not cog:
            return
        target_id = int(self.values[0])
        await interaction.response.defer(ephemeral=True)
        await cog.remove_passer_from_roster(interaction.guild, self.faction, target_id)
        await interaction.followup.send(
            f"✅ Removed <@{target_id}> from **{self.faction}**'s pending accepted list.",
            ephemeral=True,
        )


class ConfirmApplicantsView(discord.ui.View):
    """Attached to the running 'Your accepted applications:' message in the review channel."""

    def __init__(self, faction: str, passers: list[dict[str, Any]]):
        super().__init__(timeout=None)
        cfg = FACTIONS_CONFIG[faction]
        self.faction = faction

        confirm_btn = discord.ui.Button(
            label="Confirm Applicants & Close Applications",
            style=discord.ButtonStyle.primary,
            emoji="📣",
            custom_id=f"fapp_confirm_all:{cfg['key']}",
        )
        confirm_btn.callback = self._on_confirm
        self.add_item(confirm_btn)

        if passers:
            self.add_item(RemovePasserSelect(faction, passers))

    async def _on_confirm(self, interaction: discord.Interaction):
        if not isinstance(interaction.user, discord.Member) or not can_manage_faction_apps(
            interaction.user, self.faction
        ):
            return await interaction.response.send_message(
                f"❌ Only **{self.faction}** Leaders/Overseers or High Staff can confirm applicants.",
                ephemeral=True,
            )
        cog: Optional[FactionAppsCog] = interaction.client.get_cog("FactionAppsCog")
        if not cog:
            return
        await cog.confirm_and_announce_passers(interaction, self.faction)


# ── Interactive DM Helpers ────────────────────────────────────────────────────

class StartTrialView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=1800)
        self.user_id = user_id
        self.action: Optional[str] = None

    @discord.ui.button(label="Begin Trials", style=discord.ButtonStyle.success, emoji="🕯️")
    async def begin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        self.action = "start"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        self.action = "cancel"
        await interaction.response.defer()
        self.stop()


class SkipOptionalView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=1800)
        self.user_id = user_id
        self.skipped = False
        self.cancelled = False

    @discord.ui.button(label="Skip (Leave Blank)", style=discord.ButtonStyle.secondary, emoji="⏭️")
    async def skip_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        self.skipped = True
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancel Application", style=discord.ButtonStyle.danger)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        self.cancelled = True
        await interaction.response.defer()
        self.stop()


class ScaleSelectView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=1800)
        self.user_id = user_id
        self.selected_value: Optional[str] = None
        self.cancelled = False

        for num in range(1, 11):
            btn = discord.ui.Button(
                label=str(num),
                style=discord.ButtonStyle.primary,
                row=0 if num <= 5 else 1,
            )
            btn.callback = self._make_callback(str(num))
            self.add_item(btn)

        cancel_btn = discord.ui.Button(label="Cancel Application", style=discord.ButtonStyle.danger, row=2)
        cancel_btn.callback = self._on_cancel
        self.add_item(cancel_btn)

    def _make_callback(self, val: str):
        async def _cb(interaction: discord.Interaction):
            if interaction.user.id != self.user_id:
                return
            self.selected_value = val
            await interaction.response.defer()
            self.stop()

        return _cb

    async def _on_cancel(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            return
        self.cancelled = True
        await interaction.response.defer()
        self.stop()


class EditQuestionSelect(discord.ui.Select):
    def __init__(self, questions: list[dict[str, Any]]):
        options = [
            discord.SelectOption(
                label=f"Q{idx + 1}: {q['prompt'][:85]}",
                value=str(idx),
                description=q["section"][:100],
            )
            for idx, q in enumerate(questions[:25])
        ]
        super().__init__(placeholder="Select a question to edit...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        view: ReviewSubmissionView = self.view  # type: ignore
        if interaction.user.id != view.user_id:
            return
        view.action = "edit"
        view.edit_index = int(self.values[0])
        await interaction.response.defer()
        view.stop()


class ReviewSubmissionView(discord.ui.View):
    def __init__(self, user_id: int, questions: list[dict[str, Any]]):
        super().__init__(timeout=1800)
        self.user_id = user_id
        self.action: Optional[str] = None
        self.edit_index: Optional[int] = None
        self.add_item(EditQuestionSelect(questions))

    @discord.ui.button(label="Submit Application", style=discord.ButtonStyle.success, emoji="📨", row=1)
    async def submit_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        self.action = "submit"
        await interaction.response.defer()
        self.stop()

    @discord.ui.button(label="Cancel & Discard", style=discord.ButtonStyle.danger, row=1)
    async def cancel_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            return
        self.action = "cancel"
        await interaction.response.defer()
        self.stop()


# ── Main Cog ──────────────────────────────────────────────────────────────────

class FactionAppsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_applicants: set[int] = set()

    async def cog_load(self):
        state = load_state()
        for faction, cfg in FACTIONS_CONFIG.items():
            is_open = state["open_status"].get(faction, False)
            self.bot.add_view(FactionAnnouncementView(faction, disabled=not is_open))
            passers = state["accepted_passers"].get(faction, [])
            self.bot.add_view(ConfirmApplicantsView(faction, passers))

    # ── Slash Command Group ───────────────────────────────────────────────────

    factionapp_group = app_commands.Group(
        name="factionapp",
        description="Manage faction application releases, status, and blacklists.",
    )

    @factionapp_group.command(name="open", description="Release and open applications for a faction.")
    @app_commands.describe(faction="Choose which faction's applications to open")
    @app_commands.choices(
        faction=[
            app_commands.Choice(name="Eldritch Thorn", value="Eldritch Thorn"),
            app_commands.Choice(name="Sanguis Order", value="Sanguis Order"),
            app_commands.Choice(name="SilverVenom", value="SilverVenom"),
            app_commands.Choice(name="Sepharine Coven", value="Sepharine Coven"),
        ]
    )
    async def open_apps(self, interaction: discord.Interaction, faction: str):
        if not isinstance(interaction.user, discord.Member) or not can_manage_faction_apps(
            interaction.user, faction
        ):
            return await interaction.response.send_message(
                f"❌ Only **{faction}** Leaders/Overseers or Owner / Co-Owner / Community Manager can release these applications.",
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)
        cfg = FACTIONS_CONFIG[faction]
        announce_channel = interaction.guild.get_channel(cfg["announce_channel_id"])
        if not isinstance(announce_channel, discord.TextChannel):
            return await interaction.followup.send(
                f"❌ Could not find announcement channel `<#{cfg['announce_channel_id']}>`.",
                ephemeral=True,
            )

        # Resolve [M] Members ping
        ping_text = "@everyone"
        if MEMBERS_ROLE_ID:
            role = interaction.guild.get_role(MEMBERS_ROLE_ID)
            if role:
                ping_text = role.mention
        else:
            for r in interaction.guild.roles:
                if "member" in r.name.lower() and "[m]" in r.name.lower():
                    ping_text = r.mention
                    break

        content = cfg["announcement_template"].format(ping=ping_text)
        view = FactionAnnouncementView(faction, disabled=False)
        msg = await announce_channel.send(
            content=content,
            view=view,
            allowed_mentions=discord.AllowedMentions(roles=True, everyone=True),
        )

        state = load_state()
        state["open_status"][faction] = True
        state["announcement_messages"][faction] = {
            "channel_id": announce_channel.id,
            "message_id": msg.id,
        }
        save_state(state)

        await interaction.followup.send(
            f"✅ **{faction}** applications are now **OPEN**! Announcement posted in {announce_channel.mention}.",
            ephemeral=True,
        )

    @factionapp_group.command(name="close", description="Manually close applications for a faction without posting passers.")
    @app_commands.describe(faction="Choose which faction's applications to close")
    @app_commands.choices(
        faction=[
            app_commands.Choice(name="Eldritch Thorn", value="Eldritch Thorn"),
            app_commands.Choice(name="Sanguis Order", value="Sanguis Order"),
            app_commands.Choice(name="SilverVenom", value="SilverVenom"),
            app_commands.Choice(name="Sepharine Coven", value="Sepharine Coven"),
        ]
    )
    async def close_apps(self, interaction: discord.Interaction, faction: str):
        if not isinstance(interaction.user, discord.Member) or not can_manage_faction_apps(
            interaction.user, faction
        ):
            return await interaction.response.send_message(
                f"❌ You do not have permission to close **{faction}** applications.",
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)
        await self._disable_announcement_button(interaction.guild, faction)
        state = load_state()
        state["open_status"][faction] = False
        save_state(state)

        await interaction.followup.send(
            f"🔒 **{faction}** applications have been **CLOSED**.",
            ephemeral=True,
        )

    @factionapp_group.command(name="status", description="Check which faction applications are open and pending passer counts.")
    async def status_apps(self, interaction: discord.Interaction):
        state = load_state()
        embed = discord.Embed(
            title="📜 Faction Applications Status",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        for faction, cfg in FACTIONS_CONFIG.items():
            is_open = state["open_status"].get(faction, False)
            passers = state["accepted_passers"].get(faction, [])
            status_str = "🟢 **OPEN**" if is_open else "🔴 **CLOSED**"
            embed.add_field(
                name=f"{cfg['emoji']} {faction}",
                value=(
                    f"Status: {status_str}\n"
                    f"Pending Accepted: **{len(passers)}**\n"
                    f"Review Channel: <#{cfg['review_channel_id']}>"
                ),
                inline=True,
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @factionapp_group.command(name="blacklist", description="Blacklist a member from faction applications (AI usage / trolling).")
    @app_commands.describe(user="Member to blacklist", reason="Reason for blacklist")
    async def blacklist_user(self, interaction: discord.Interaction, user: discord.Member, reason: str):
        if not isinstance(interaction.user, discord.Member) or not get_manageable_factions(interaction.user):
            return await interaction.response.send_message(
                "❌ Only Faction Leaders/Overseers or High Staff can blacklist applicants.",
                ephemeral=True,
            )
        state = load_state()
        state["blacklisted_users"][str(user.id)] = {
            "reason": reason,
            "by": interaction.user.id,
        }
        save_state(state)
        await interaction.response.send_message(
            f"🚫 {user.mention} (`{user.id}`) has been blacklisted from faction applications.\n**Reason:** {reason}",
            ephemeral=True,
        )

    @factionapp_group.command(name="unblacklist", description="Remove a member from the faction application blacklist.")
    @app_commands.describe(user="Member to unblacklist")
    async def unblacklist_user(self, interaction: discord.Interaction, user: discord.Member):
        if not isinstance(interaction.user, discord.Member) or not get_manageable_factions(interaction.user):
            return await interaction.response.send_message(
                "❌ Only Faction Leaders/Overseers or High Staff can manage the blacklist.",
                ephemeral=True,
            )
        state = load_state()
        removed = state["blacklisted_users"].pop(str(user.id), None)
        save_state(state)
        if not removed:
            return await interaction.response.send_message(
                f"ℹ️ {user.mention} is not currently blacklisted.",
                ephemeral=True,
            )
        await interaction.response.send_message(
            f"✅ Removed {user.mention} from the faction application blacklist.",
            ephemeral=True,
        )

    @app_commands.command(name="factionapply", description="Apply to an open faction via DM.")
    @app_commands.describe(faction="Select which faction you want to apply to")
    @app_commands.choices(
        faction=[
            app_commands.Choice(name="Eldritch Thorn", value="Eldritch Thorn"),
            app_commands.Choice(name="Sanguis Order", value="Sanguis Order"),
            app_commands.Choice(name="SilverVenom", value="SilverVenom"),
            app_commands.Choice(name="Sepharine Coven", value="Sepharine Coven"),
        ]
    )
    async def factionapply(self, interaction: discord.Interaction, faction: str):
        await self.start_dm_application(interaction, faction)

    # ── Eligibility & DM Session Launcher ─────────────────────────────────────

    async def _get_active_warning_count(self, user_id: int) -> int:
        db = getattr(self.bot, "db", None)
        if not db:
            return 0
        try:
            if hasattr(db, "get_active_warnings"):
                warns = await db.get_active_warnings(user_id)
                return len(warns)
            if hasattr(db, "get_warnings"):
                warns = await db.get_warnings(user_id)
                return len(warns)
        except Exception:
            pass
        return 0

    async def start_dm_application(self, interaction: discord.Interaction, faction: str):
        state = load_state()
        if not state["open_status"].get(faction, False):
            return await interaction.response.send_message(
                f"🔒 Applications for **{faction}** are currently closed.",
                ephemeral=True,
            )

        bl_entry = state["blacklisted_users"].get(str(interaction.user.id))
        if bl_entry:
            return await interaction.response.send_message(
                f"🚫 You are blacklisted from faction applications.\n**Reason:** {bl_entry.get('reason', 'No reason given')}",
                ephemeral=True,
            )

        if interaction.user.id in self.active_applicants:
            return await interaction.response.send_message(
                "⚠️ You already have an active faction application open in your DMs! Complete or cancel it first.",
                ephemeral=True,
            )

        cfg = FACTIONS_CONFIG[faction]
        warn_count = await self._get_active_warning_count(interaction.user.id)
        if warn_count > cfg["max_warnings"]:
            return await interaction.response.send_message(
                f"❌ You currently have **{warn_count}** warnings. **{faction}** requires no more than **{cfg['max_warnings']}** warnings.",
                ephemeral=True,
            )

        await interaction.response.defer(ephemeral=True)

        # Send Intro DM first to verify DMs are open
        intro_embed = discord.Embed(
            title=f"{cfg['emoji']} {faction} — Application",
            description=cfg["intro"],
            color=cfg["color"],
        )
        intro_embed.set_footer(text="You have 30 minutes per question • Type 'cancel' at any time to quit")
        start_view = StartTrialView(interaction.user.id)

        try:
            dm_channel = await interaction.user.create_dm()
            await dm_channel.send(embed=intro_embed, view=start_view)
        except discord.Forbidden:
            return await interaction.followup.send(
                "❌ I couldn't DM you! Please enable **Direct Messages from Server Members** in your Privacy Settings and try again.",
                ephemeral=True,
            )

        await interaction.followup.send(
            f"📩 Check your DMs! Your **{faction}** application has been sent.",
            ephemeral=True,
        )

        self.active_applicants.add(interaction.user.id)
        try:
            await start_view.wait()
            if start_view.action != "start":
                await dm_channel.send("❌ Application cancelled or timed out.")
                return

            await self._run_dm_questionnaire(
                guild=interaction.guild,
                applicant=interaction.user,
                dm_channel=dm_channel,
                faction=faction,
            )
        finally:
            self.active_applicants.discard(interaction.user.id)

    # ── Single Question Prompt Helper ─────────────────────────────────────────

    async def _ask_single_question(
        self,
        applicant: discord.User | discord.Member,
        dm_channel: discord.DMChannel,
        faction: str,
        index: int,
        total: int,
        q: dict[str, Any],
        show_section_note: bool = True,
    ) -> Optional[str]:
        """Returns the validated answer string, or None if cancelled/timed out."""
        cfg = FACTIONS_CONFIG[faction]
        if show_section_note and q.get("section_note"):
            note_embed = discord.Embed(description=q["section_note"], color=cfg["color"])
            await dm_channel.send(embed=note_embed)

        rules: list[str] = ["⏱️ **30 minutes** to answer"]
        if q.get("max_sentences"):
            rules.append(f"✍️ **Max {q['max_sentences']} full sentences**")
        if q.get("optional"):
            rules.append("⏭️ **Optional** (click Skip or type `skip` to leave blank)")
        if q["type"] == "scale":
            rules.append("📊 **Pick 1–10** using the buttons below or by typing a number")

        q_embed = discord.Embed(
            title=f"{cfg['emoji']} {q['section']} — Question {index + 1}/{total}",
            description=f"**{q['prompt']}**\n\n" + " • ".join(rules),
            color=cfg["color"],
        )
        q_embed.set_footer(text="Type 'cancel' anytime to abort this application.")

        # Scale questions use interactive 1-10 buttons (also accepts typed 1-10)
        if q["type"] == "scale":
            view = ScaleSelectView(applicant.id)
            await dm_channel.send(embed=q_embed, view=view)

            def check_scale_msg(m: discord.Message) -> bool:
                return m.author.id == applicant.id and m.channel.id == dm_channel.id

            wait_view = asyncio.create_task(view.wait())
            wait_msg = asyncio.create_task(self.bot.wait_for("message", timeout=1800, check=check_scale_msg))

            try:
                done, pending = await asyncio.wait(
                    {wait_view, wait_msg},
                    timeout=1800,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()

                if not done:
                    await dm_channel.send("⌛ **Timed out** after 30 minutes. Your application has been cancelled.")
                    return None

                if view.cancelled:
                    await dm_channel.send("❌ Application cancelled.")
                    return None

                if view.selected_value:
                    return f"{view.selected_value}/10"

                if wait_msg in done:
                    msg = wait_msg.result()
                    raw = msg.content.strip()
                    if raw.lower() == "cancel":
                        await dm_channel.send("❌ Application cancelled.")
                        return None
                    if raw.isdigit() and 1 <= int(raw) <= 10:
                        return f"{int(raw)}/10"
                    await dm_channel.send("⚠️ Please enter a whole number from **1 to 10** (or click a button).")
                    return await self._ask_single_question(
                        applicant, dm_channel, faction, index, total, q, show_section_note=False
                    )
            except asyncio.TimeoutError:
                await dm_channel.send("⌛ **Timed out** after 30 minutes. Your application has been cancelled.")
                return None

        # Optional text questions include a Skip button
        if q.get("optional"):
            view = SkipOptionalView(applicant.id)
            await dm_channel.send(embed=q_embed, view=view)

            def check_opt_msg(m: discord.Message) -> bool:
                return m.author.id == applicant.id and m.channel.id == dm_channel.id

            while True:
                wait_view = asyncio.create_task(view.wait())
                wait_msg = asyncio.create_task(self.bot.wait_for("message", timeout=1800, check=check_opt_msg))
                done, pending = await asyncio.wait(
                    {wait_view, wait_msg},
                    timeout=1800,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for task in pending:
                    task.cancel()

                if not done:
                    await dm_channel.send("⌛ **Timed out** after 30 minutes. Your application has been cancelled.")
                    return None

                if view.cancelled:
                    await dm_channel.send("❌ Application cancelled.")
                    return None

                if view.skipped:
                    return "*Left blank*"

                if wait_msg in done:
                    msg = wait_msg.result()
                    raw = msg.content.strip()
                    if raw.lower() == "cancel":
                        await dm_channel.send("❌ Application cancelled.")
                        return None
                    if raw.lower() in {"skip", "blank", "none", "n/a"}:
                        return "*Left blank*"
                    if not raw:
                        await dm_channel.send("⚠️ Empty message. Type your answer or click **Skip (Leave Blank)**.")
                        continue
                    return raw

        # Standard required text/short question
        await dm_channel.send(embed=q_embed)

        def check_msg(m: discord.Message) -> bool:
            return m.author.id == applicant.id and m.channel.id == dm_channel.id

        while True:
            try:
                msg = await self.bot.wait_for("message", timeout=1800, check=check_msg)
            except asyncio.TimeoutError:
                await dm_channel.send("⌛ **Timed out** after 30 minutes. Your application has been cancelled.")
                return None

            raw = msg.content.strip()
            if raw.lower() == "cancel":
                await dm_channel.send("❌ Application cancelled.")
                return None

            if not raw:
                await dm_channel.send("⚠️ Please type a valid response.")
                continue

            max_s = q.get("max_sentences")
            if max_s:
                s_count = count_sentences(raw)
                if s_count > max_s:
                    await dm_channel.send(
                        f"⚠️ Your answer has **{s_count} sentences**, which exceeds the limit of **{max_s} full sentences max**. "
                        f"Please shorten your response and send it again:"
                    )
                    continue

            return raw

    # ── Full Questionnaire + Review Loop ──────────────────────────────────────

    async def _run_dm_questionnaire(
        self,
        guild: Optional[discord.Guild],
        applicant: discord.User | discord.Member,
        dm_channel: discord.DMChannel,
        faction: str,
    ):
        cfg = FACTIONS_CONFIG[faction]
        questions = cfg["questions"]
        answers: list[str] = [""] * len(questions)

        last_section = None
        for idx, q in enumerate(questions):
            show_note = q["section"] != last_section
            last_section = q["section"]
            ans = await self._ask_single_question(
                applicant=applicant,
                dm_channel=dm_channel,
                faction=faction,
                index=idx,
                total=len(questions),
                q=q,
                show_section_note=show_note,
            )
            if ans is None:
                return
            answers[idx] = ans

        # Final Review & Edit Loop
        while True:
            summary_lines = []
            for idx, (q, ans) in enumerate(zip(questions, answers), start=1):
                summary_lines.append(f"**Q{idx}. {q['prompt']}**\n> {ans}")

            full_summary = "\n\n".join(summary_lines)
            if len(full_summary) > 3800:
                full_summary = full_summary[:3790] + "\n…"

            outro_embed = discord.Embed(
                title=f"{cfg['emoji']} {faction} — Review Your Application",
                description=f"{cfg['outro']}\n\n────────────────────\n{full_summary}",
                color=cfg["color"],
            )
            outro_embed.set_footer(text="Use the dropdown below to edit any question, or click Submit Application.")

            review_view = ReviewSubmissionView(applicant.id, questions)
            await dm_channel.send(embed=outro_embed, view=review_view)
            await review_view.wait()

            if review_view.action == "edit" and review_view.edit_index is not None:
                e_idx = review_view.edit_index
                new_ans = await self._ask_single_question(
                    applicant=applicant,
                    dm_channel=dm_channel,
                    faction=faction,
                    index=e_idx,
                    total=len(questions),
                    q=questions[e_idx],
                    show_section_note=False,
                )
                if new_ans is None:
                    return
                answers[e_idx] = new_ans
                continue

            if review_view.action == "submit":
                state = load_state()
                if not state["open_status"].get(faction, False):
                    await dm_channel.send(
                        f"🔒 Unfortunately, **{faction}** applications were closed while you were finishing."
                    )
                    return

                posted = await self._post_application_to_review(
                    guild=guild,
                    applicant=applicant,
                    faction=faction,
                    questions=questions,
                    answers=answers,
                )
                if posted:
                    await dm_channel.send(
                        f"✅ Your **{faction}** application has been submitted! Good luck!"
                    )
                else:
                    await dm_channel.send(
                        "⚠️ Could not locate the faction review channel. Please notify a staff member."
                    )
                return

            await dm_channel.send("❌ Application discarded.")
            return

    # ── Post Application Embed to Review Channel ──────────────────────────────

    async def _post_application_to_review(
        self,
        guild: Optional[discord.Guild],
        applicant: discord.User | discord.Member,
        faction: str,
        questions: list[dict[str, Any]],
        answers: list[str],
    ) -> bool:
        cfg = FACTIONS_CONFIG[faction]
        review_channel = self.bot.get_channel(cfg["review_channel_id"])
        if not isinstance(review_channel, discord.TextChannel):
            return False

        roblox_username = answers[0].strip() if answers else "Unknown"

        embed = discord.Embed(
            title=f"{cfg['emoji']} New {faction} Application",
            description=(
                f"**Applicant:** {applicant.mention} (`{applicant.id}`)\n"
                f"**Roblox Username:** `{roblox_username}`"
            ),
            color=cfg["color"],
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_thumbnail(url=applicant.display_avatar.url)

        for idx, (q, ans) in enumerate(zip(questions, answers), start=1):
            field_name = f"Q{idx}: {q['prompt']}"[:256]
            field_val = ans[:1024] if ans else "*Left blank*"
            embed.add_field(name=field_name, value=field_val, inline=False)

        embed.set_footer(text=f"Applicant ID: {applicant.id} • Roblox: {roblox_username}")

        view = ApplicationReviewView(
            faction=faction,
            applicant_id=applicant.id,
            roblox_username=roblox_username,
        )
        await review_channel.send(embed=embed, view=view)
        return True

    # ── Accept → Update Running Roster (NO DM) ────────────────────────────────

    async def handle_accept_application(
        self,
        interaction: discord.Interaction,
        faction: str,
        applicant_id: int,
        roblox_username: str,
    ):
        await interaction.response.defer(ephemeral=True)

        # Delete the individual application embed
        try:
            await interaction.message.delete()
        except discord.HTTPException:
            pass

        state = load_state()
        passers: list[dict[str, Any]] = state["accepted_passers"].setdefault(faction, [])

        # Prevent duplicate entries if accepted twice
        if not any(p["user_id"] == applicant_id for p in passers):
            member = interaction.guild.get_member(applicant_id) if interaction.guild else None
            display_name = member.name if member else str(applicant_id)
            passers.append(
                {
                    "user_id": applicant_id,
                    "display_name": display_name,
                    "roblox_username": roblox_username,
                }
            )
            save_state(state)

        await self._refresh_roster_message(interaction.guild, faction)

        await interaction.followup.send(
            f"✅ Added <@{applicant_id}> (`{roblox_username}`) to **{faction}**'s accepted list (no DM sent). "
            f"Click **Confirm Applicants & Close Applications** when finished reviewing.",
            ephemeral=True,
        )

    async def remove_passer_from_roster(
        self,
        guild: Optional[discord.Guild],
        faction: str,
        target_user_id: int,
    ):
        state = load_state()
        passers = state["accepted_passers"].get(faction, [])
        state["accepted_passers"][faction] = [p for p in passers if p["user_id"] != target_user_id]
        save_state(state)
        await self._refresh_roster_message(guild, faction)

    async def _refresh_roster_message(self, guild: Optional[discord.Guild], faction: str):
        cfg = FACTIONS_CONFIG[faction]
        review_channel = self.bot.get_channel(cfg["review_channel_id"])
        if not isinstance(review_channel, discord.TextChannel):
            return

        state = load_state()
        passers = state["accepted_passers"].get(faction, [])
        roster_info = state["roster_messages"].get(faction)

        # If list became empty after a manual removal, clean up roster message
        if not passers:
            if roster_info:
                try:
                    old_msg = await review_channel.fetch_message(roster_info["message_id"])
                    await old_msg.delete()
                except discord.HTTPException:
                    pass
                state["roster_messages"].pop(faction, None)
                save_state(state)
            return

        lines = ["**Your accepted applications:**"]
        for idx, p in enumerate(passers, start=1):
            lines.append(f"{idx}. <@{p['user_id']}> ({p['user_id']}) {p['roblox_username']}")

        embed = discord.Embed(
            title=f"{cfg['emoji']} {faction} — Accepted Applications Roster",
            description="\n".join(lines),
            color=cfg["color"],
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        embed.set_footer(text="Click 'Confirm Applicants & Close Applications' once all applications are reviewed.")
        view = ConfirmApplicantsView(faction, passers)

        # Edit existing roster message if it still exists, otherwise post a new one
        if roster_info:
            try:
                existing = await review_channel.fetch_message(roster_info["message_id"])
                await existing.edit(embed=embed, view=view)
                return
            except discord.HTTPException:
                pass

        new_msg = await review_channel.send(embed=embed, view=view)
        state["roster_messages"][faction] = {
            "channel_id": review_channel.id,
            "message_id": new_msg.id,
        }
        save_state(state)

    # ── Confirm Applicants → Close Apps, Delete Roster, Announce Passers ──────

    async def confirm_and_announce_passers(self, interaction: discord.Interaction, faction: str):
        await interaction.response.defer(ephemeral=True)
        cfg = FACTIONS_CONFIG[faction]
        state = load_state()
        passers = state["accepted_passers"].get(faction, [])

        if not passers:
            return await interaction.followup.send(
                "❌ There are no accepted applicants on the roster to confirm.",
                ephemeral=True,
            )

        # 1. Close applications & disable Apply button on the announcement
        state["open_status"][faction] = False
        await self._disable_announcement_button(interaction.guild, faction)

        # 2. Delete the roster message in the private review channel
        roster_info = state["roster_messages"].pop(faction, None)
        if roster_info:
            review_ch = self.bot.get_channel(roster_info["channel_id"])
            if isinstance(review_ch, discord.TextChannel):
                try:
                    msg = await review_ch.fetch_message(roster_info["message_id"])
                    await msg.delete()
                except discord.HTTPException:
                    pass

        # 3. Post public congratulations announcement in the faction's announcement channel
        announce_ch = self.bot.get_channel(cfg["announce_channel_id"])
        if isinstance(announce_ch, discord.TextChannel):
            passer_lines = [
                f"**{idx}.** <@{p['user_id']}> (`{p['roblox_username']}`)"
                for idx, p in enumerate(passers, start=1)
            ]
            pings = " ".join(f"<@{p['user_id']}>" for p in passers)

            congrats_embed = discord.Embed(
                title=f"{cfg['emoji']} {faction} — Accepted Applicants!",
                description=(
                    f"Congratulations to everyone who passed **{faction}** applications! "
                    f"Welcome to the faction!\n\n"
                    + "\n".join(passer_lines)
                ),
                color=cfg["color"],
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            congrats_embed.set_footer(text=f"{faction} Applications are now CLOSED.")

            await announce_ch.send(
                content=f"🎉 **CONGRATULATIONS TO OUR NEWEST {faction.upper()} MEMBERS!**\n{pings}",
                embed=congrats_embed,
                allowed_mentions=discord.AllowedMentions(users=True),
            )

        # 4. Clear pending accepted list for next cycle
        state["accepted_passers"][faction] = []
        save_state(state)

        await interaction.followup.send(
            f"📣 Confirmed **{len(passers)}** accepted applicants, closed **{faction}** applications, "
            f"deleted the review roster, and announced the passers in <#{cfg['announce_channel_id']}>!",
            ephemeral=True,
        )

    async def _disable_announcement_button(self, guild: Optional[discord.Guild], faction: str):
        state = load_state()
        ann = state["announcement_messages"].get(faction)
        if not ann:
            return
        ch = self.bot.get_channel(ann["channel_id"])
        if isinstance(ch, discord.TextChannel):
            try:
                msg = await ch.fetch_message(ann["message_id"])
                await msg.edit(view=FactionAnnouncementView(faction, disabled=True))
            except discord.HTTPException:
                pass


async def setup(bot: commands.Bot):
    await bot.add_cog(FactionAppsCog(bot))
