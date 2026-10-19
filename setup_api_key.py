#!/usr/bin/env python3
"""
setup_api_key.py
Utility to securely set up, encrypt, and verify the OpenRouter API key for the RAG project.
Creates secret.key and api_key.enc so that the notebook can load it automatically.
Running it again replaces the stored key.
"""

import os
import sys
import getpass
from pathlib import Path

import requests
from cryptography.fernet import Fernet

KEY_FILE = Path("secret.key")
ENC_FILE = Path("api_key.enc")
OLD_ENC_FILE = Path("gemini_api_key.enc")   # from the earlier Gemini setup
MODEL = "google/gemini-2.5-flash-lite"

def save_encrypted_key(api_key: str) -> None:
    fernet_key = Fernet.generate_key()
    KEY_FILE.write_bytes(fernet_key)
    ENC_FILE.write_bytes(Fernet(fernet_key).encrypt(api_key.encode("utf-8")))
    if OLD_ENC_FILE.exists():
        OLD_ENC_FILE.unlink()
        print(f"✓ Removed old {OLD_ENC_FILE}")
    print(f"✓ Encrypted API key saved to {ENC_FILE}")
    print(f"✓ Encryption secret key saved to {KEY_FILE}")
    print("  (Both files are excluded by .gitignore and should not be committed to GitHub)")

def verify_key(api_key: str) -> bool:
    print("\nVerifying API key with OpenRouter...")
    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": MODEL, "messages": [{"role": "user", "content": "Say 'OK' in one word."}]},
            timeout=60)
        r.raise_for_status()
        print("✓ API key verified successfully! Model response:",
              r.json()["choices"][0]["message"]["content"].strip())
        return True
    except Exception as e:
        print(f"✗ Verification warning: {e}")
        print("  Key has still been saved. Please check the key and your credits on openrouter.ai.")
        return False

def main():
    print("=" * 60)
    print(" OpenRouter API Key Setup & Encryption")
    print("=" * 60)

    # 1. Check if argument passed or env var exists
    api_key = None
    if len(sys.argv) > 1:
        api_key = sys.argv[1].strip()
    elif os.environ.get("OPENROUTER_API_KEY"):
        env_key = os.environ.get("OPENROUTER_API_KEY").strip()
        use_env = input(f"Found OPENROUTER_API_KEY in environment ({env_key[:6]}...{env_key[-4:]}). Use it? (y/n): ").strip().lower()
        if use_env in ("y", "yes", ""):
            api_key = env_key

    # 2. Prompt user if still none
    if not api_key:
        print("Get your API key from OpenRouter: https://openrouter.ai/keys")
        api_key = getpass.getpass("Enter your OpenRouter API key (input will be hidden): ").strip()

    if not api_key:
        print("Error: No API key provided.")
        sys.exit(1)

    save_encrypted_key(api_key)
    verify_key(api_key)
    print("\nSetup complete! You can now run the notebook without entering the key again.")

if __name__ == "__main__":
    main()
