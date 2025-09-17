from app.utils.exchange_client import ExchangeClient
from typing import List, Dict, Any

def fetch_today_emails_as_dict(target_email: str) -> List[Dict[str, Any]]:
    """
    Fetch today's emails and convert them to a list of dicts for summarization.
    """
    client = ExchangeClient(target_email=target_email)
    emails = client.fetch_today_emails()
    email_dicts = []
    for msg in emails:
        email_dicts.append({
            "subject": getattr(msg, "subject", ""),
            "body": getattr(msg, "body", ""),
            "sender": str(getattr(msg, "sender", "")),
            "datetime_received": getattr(msg, "datetime_received", None),
        })
    return email_dicts
