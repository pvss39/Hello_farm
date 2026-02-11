
import os
import base64
import requests
import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict
from dotenv import load_dotenv

load_dotenv()


class WhatsAppService:
    # auto-detects mode from .env: twilio → callmebot → mock (console)

    def __init__(self):
        self.farmer_number   = os.getenv("FARMER_WHATSAPP", "").strip()
        self.observer_number = os.getenv("OBSERVER_WHATSAPP", "").strip()

        self._twilio_sid    = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
        self._twilio_token  = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
        self._twilio_from   = os.getenv("TWILIO_WHATSAPP_NUMBER",
                                        "whatsapp:+14155238886").strip()

        self._callmebot_key = os.getenv("CALLMEBOT_API_KEY", "").strip()
        self._imgur_client  = os.getenv("IMGUR_CLIENT_ID", "").strip()

        if self._twilio_sid and self._twilio_token:
            self.mode = "twilio"
        elif self._callmebot_key and self.farmer_number:
            self.mode = "callmebot"
        else:
            self.mode = "mock"

        self.available = self.mode != "mock"
        print(f"[WhatsApp] Mode: {self.mode}")

    # ──────────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────────

    def send_message(self, to_number: str, message_text: str,
                     image_path: Optional[str] = None) -> Dict:
        to_number = to_number.strip()
        if not to_number:
            return {"status": "failed", "error": "No number provided"}

        if self.mode == "mock":
            return self._send_mock(to_number, message_text, image_path)
        elif self.mode == "twilio":
            return self._send_twilio(to_number, message_text, image_path)
        else:
            return self._send_callmebot(to_number, message_text)

    def send_to_multiple(self, message_text: str,
                         numbers: Optional[List[str]] = None,
                         image_path: Optional[str] = None) -> List[Dict]:
        if numbers is None:
            numbers = [n for n in [self.farmer_number, self.observer_number]
                       if n.strip()]

        results = []
        for number in numbers:
            result = self.send_message(number, message_text, image_path)
            result["number"] = number
            results.append(result)

        delivered = sum(1 for r in results if r["status"] in ("sent", "mock"))
        print(f"[WhatsApp] Delivered to {delivered}/{len(results)} numbers")
        return results

    def send_report_card(self, report_text: str,
                         image_path: Optional[str] = None) -> List[Dict]:
        return self.send_to_multiple(report_text, image_path=image_path)

    def _send_twilio(self, to_number: str, message_text: str,
                     image_path: Optional[str] = None) -> Dict:
        try:
            try:
                from twilio.rest import Client  # type: ignore[import-untyped]
            except ImportError:
                print("[WhatsApp] twilio package not installed — run: pip install twilio")
                return {"status": "failed", "error": "twilio not installed"}
            client = Client(self._twilio_sid, self._twilio_token)

            if not to_number.startswith("whatsapp:"):
                to_number = f"whatsapp:{to_number}"

            params = {
                "from_": self._twilio_from,
                "to":    to_number,
                "body":  message_text[:1600],
            }

            image_url = None
            if image_path and Path(image_path).exists():
                image_url = self.upload_image_to_imgur(image_path)
                if image_url:
                    params["media_url"] = image_url  # type: ignore[assignment]
                else:
                    print("[WhatsApp] Image upload failed, sending text only")

            msg = client.messages.create(**params)
            return {"status": "sent", "message_sid": msg.sid,
                    "image_url": image_url}

        except ImportError:
            print("[WhatsApp] twilio package not installed — run: pip install twilio")
            return {"status": "failed", "error": "twilio not installed"}
        except Exception as e:
            print(f"[WhatsApp] Twilio error: {e}")
            return {"status": "failed", "error": str(e)}

    # ──────────────────────────────────────────────────────────────────
    def _send_callmebot(self, to_number: str, message_text: str) -> Dict:
        try:
            url = (
                "https://api.callmebot.com/whatsapp.php"
                f"?phone={to_number}"
                f"&text={urllib.parse.quote(message_text)}"
                f"&apikey={self._callmebot_key}"
            )
            response = requests.get(url, timeout=15)

            if response.status_code == 200 and "Message Sent" in response.text:
                print(f"[WhatsApp] Sent to {to_number}")
                return {"status": "sent", "message_sid": None, "image_url": None}
            else:
                print(f"[WhatsApp] CallMeBot error {response.status_code}: "
                      f"{response.text[:120]}")
                return {"status": "failed", "error": response.text[:120]}

        except requests.exceptions.Timeout:
            return {"status": "failed", "error": "timeout"}
        except Exception as e:
            return {"status": "failed", "error": str(e)}

    def _send_mock(self, to_number: str, message_text: str,
                   image_path: Optional[str]) -> Dict:
        print("\n[WhatsApp MOCK] ─────────────────────────")
        print(f"  To:    {to_number}")
        if image_path:
            print(f"  Image: {image_path}")
        print(f"  Body:\n{message_text}")
        print("──────────────────────────────────────────")
        print("  To activate: add CALLMEBOT_API_KEY or TWILIO_* keys to .env")
        return {"status": "mock", "message_sid": None, "image_url": None}

    def upload_image_to_imgur(self, image_path: str) -> Optional[str]:
        if not self._imgur_client:
            print("[WhatsApp] IMGUR_CLIENT_ID not set — cannot upload image")
            return None

        if not Path(image_path).exists():
            print(f"[WhatsApp] Image not found: {image_path}")
            return None

        try:
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read())

            response = requests.post(
                "https://api.imgur.com/3/image",
                headers={"Authorization": f"Client-ID {self._imgur_client}"},
                data={"image": image_data, "type": "base64"},
                timeout=30,
            )

            if response.status_code == 200:
                url = response.json()["data"]["link"]
                print(f"[WhatsApp] Imgur upload OK: {url}")
                return url
            else:
                print(f"[WhatsApp] Imgur upload failed: {response.text[:120]}")
                return None

        except Exception as e:
            print(f"[WhatsApp] Imgur error: {e}")
            return None

    def format_phone(self, phone: str) -> str:
        digits = "".join(filter(str.isdigit, phone))
        if len(digits) == 10:
            return f"+91{digits}"
        if len(digits) == 12 and digits.startswith("91"):
            return f"+{digits}"
        return f"+91{digits[-10:]}"

    @property
    def configured_numbers(self) -> List[str]:
        return [n for n in [self.farmer_number, self.observer_number]
                if n.strip()]

    def send_daily_report(self, report_text: str,
                          to_number: Optional[str] = None) -> bool:
        result = self.send_message(to_number or self.farmer_number, report_text)
        return result["status"] in ("sent", "mock")
