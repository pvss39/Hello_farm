"""
Telegram delivery service for Hello Farm.

Sends crop monitoring messages and NDVI images via Telegram Bot API.
No opt-in restrictions — works permanently after one-time /start.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()


class TelegramService:
    """Sends messages and images to Telegram chat IDs via Bot API."""

    BASE_URL = "https://api.telegram.org/bot{token}/{method}"

    def __init__(self) -> None:
        self.token    = os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_ids = self._load_chat_ids()
        self.enabled  = bool(self.token and "your_" not in self.token)

        if self.enabled:
            print(f"[Telegram] Ready — {len(self.chat_ids)} recipient(s): {self.chat_ids}")
        else:
            print("[Telegram] TELEGRAM_BOT_TOKEN not set — disabled")

    def _load_chat_ids(self) -> List[str]:
        ids = []
        for key in ("FARMER_TELEGRAM_ID", "FATHER_TELEGRAM_ID"):
            val = os.getenv(key, "").strip()
            if val and "your_" not in val:
                ids.append(val)
        # dedupe while preserving order
        return list(dict.fromkeys(ids))

    def _url(self, method: str) -> str:
        return self.BASE_URL.format(token=self.token, method=method)

    def send_message(self, chat_id: str, text: str) -> bool:
        """Send a text message to one chat ID. Returns True on success."""
        try:
            resp = requests.post(
                self._url("sendMessage"),
                data={"chat_id": chat_id, "text": text},
                timeout=15,
            )
            ok = resp.json().get("ok", False)
            if not ok:
                print(f"[Telegram] sendMessage failed for {chat_id}: {resp.text[:200]}")
            return ok
        except Exception as exc:
            print(f"[Telegram] sendMessage error for {chat_id}: {exc}")
            return False

    def send_photo(self, chat_id: str, image_path: str, caption: str = "") -> bool:
        """Send a photo file to one chat ID. Returns True on success."""
        if not Path(image_path).exists():
            print(f"[Telegram] Image not found: {image_path}")
            return False
        try:
            with open(image_path, "rb") as fh:
                resp = requests.post(
                    self._url("sendPhoto"),
                    data={"chat_id": chat_id, "caption": caption},
                    files={"photo": fh},
                    timeout=30,
                )
            ok = resp.json().get("ok", False)
            if not ok:
                print(f"[Telegram] sendPhoto failed for {chat_id}: {resp.text[:200]}")
            return ok
        except Exception as exc:
            print(f"[Telegram] sendPhoto error for {chat_id}: {exc}")
            return False

    def broadcast(self, text: str, image_path: Optional[str] = None) -> int:
        """
        Send message (and optional image) to all configured recipients.
        Returns count of successful deliveries.
        """
        if not self.enabled:
            print("[Telegram] Disabled — skipping broadcast")
            return 0

        sent = 0
        for cid in self.chat_ids:
            if image_path and Path(image_path).exists():
                ok = self.send_photo(cid, image_path, caption=text[:1024])
            else:
                ok = self.send_message(cid, text)
            if ok:
                sent += 1
                print(f"[Telegram] Sent to {cid}")

        return sent
