"""
config_ai.py — Config for AI Scanner Bot.
Separate from the main bot config.
Designed for Railway deployment with environment variables.
"""

import os
import sys
import getpass
import configparser
from pathlib import Path
from cryptography.fernet import Fernet

BASE_DIR   = Path(__file__).parent
KEY_FILE   = BASE_DIR / ".ai_secret.key"
TOKEN_FILE = BASE_DIR / ".ai_bot_token"
INI_FILE   = BASE_DIR / "config_ai.ini"


def _fernet():
    if KEY_FILE.exists():
        return Fernet(KEY_FILE.read_bytes())
    key = Fernet.generate_key()
    KEY_FILE.write_bytes(key)
    KEY_FILE.chmod(0o600)
    return Fernet(key)


def _load_token():
    # Check env first (Railway)
    env = os.getenv("AI_BOT_TOKEN")
    if env:
        return env
    
    # Try encrypted local file
    f = _fernet()
    if TOKEN_FILE.exists():
        try:
            return f.decrypt(TOKEN_FILE.read_bytes()).decode()
        except Exception:
            TOKEN_FILE.unlink(missing_ok=True)
    
    # Interactive local setup
    print("\n══════════════════════════════════════")
    print("  AI Scanner Bot - First Run Setup")
    print("══════════════════════════════════════")
    token = getpass.getpass("Paste your AI bot token: ").strip()
    if not token:
        sys.exit("No token provided.")
    TOKEN_FILE.write_bytes(f.encrypt(token.encode()))
    TOKEN_FILE.chmod(0o600)
    print("[OK] Token saved.\n")
    return token


def _load_ini():
    # Check env vars first - if all required env vars are set, no need for ini
    if os.getenv("DRIVER_GROUP_ID") and os.getenv("AI_ALERTS_CHANNEL_ID") and os.getenv("GROQ_API_KEY"):
        return None
    
    ini = configparser.ConfigParser()
    if INI_FILE.exists():
        ini.read(INI_FILE)
        return ini
    
    # For local without ini file, return None - env vars should be set
    # This allows Railway to work with just env vars
    return None


class Config:
    TELEGRAM_TOKEN   = _load_token()
    _ini             = _load_ini()
    DRIVER_GROUP_ID  = int(os.getenv("DRIVER_GROUP_ID")  or (_ini.get("channels", "driver_group_id",  fallback="0") if _ini else "0"))
    REPORTS_GROUP_ID = int(os.getenv("REPORTS_GROUP_ID") or (_ini.get("channels", "reports_group_id", fallback="0") if _ini else "0"))
    AI_ALERTS_CHANNEL_ID = int(os.getenv("AI_ALERTS_CHANNEL_ID") or (_ini.get("channels", "ai_alerts_channel_id", fallback="0") if _ini else "0"))
    GROQ_API_KEY     = os.getenv("GROQ_API_KEY") or (_ini.get("groq", "api_key", fallback="") if _ini else "")


config = Config()

