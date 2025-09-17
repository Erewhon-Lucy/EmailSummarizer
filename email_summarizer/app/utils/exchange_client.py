from exchangelib import Credentials, Account, DELEGATE, Configuration, Message, EWSTimeZone, UTC, NTLM
from email_summarizer.app.config import Config
from datetime import datetime, timedelta
from typing import List
from markitdown import MarkItDown
class ExchangeClient:
    def __init__(self, target_email: str = None):
        creds = Credentials(
            username=Config.EXCHANGE_USERNAME,
            password=Config.EXCHANGE_PASSWORD
        )
        config = Configuration(server=Config.EXCHANGE_SERVER, credentials=creds, auth_type=NTLM)
        self.account = Account(
            primary_smtp_address=target_email,
            config=config,
            autodiscover=False,
            access_type=DELEGATE
        )
        # Use the account's default timezone if available, else UTC
        self.tz = getattr(self.account, 'default_timezone', UTC)

    def fetch_emails(self, since: datetime, until: datetime = None) -> List[dict]:
        """
        Fetch emails received between 'since' and 'until' (default: now).
        Returns a list of JSON-serializable dicts, each containing:
        sender, to_recipients, cc_recipients, bcc_recipients, author, message_id, is_read, received_by, main_content (HTML)
        """
        if until is None:
            until = datetime.now(self.tz)
        if since.tzinfo is None:
            since = self.tz.localize(since)
        if until.tzinfo is None:
            until = self.tz.localize(until)
        inbox = self.account.inbox
        qs = inbox.filter(datetime_received__range=(since, until)).order_by('-datetime_received')
        emails = []
        md = MarkItDown(enable_plugins=False)
        import tempfile, os
        for i, msg in enumerate(qs):
            content_html = getattr(msg, "body", "").body if hasattr(getattr(msg, "body", ""), "body") else str(getattr(msg, "body", ""))
            with tempfile.NamedTemporaryFile("w+", suffix=".html", delete=False, encoding="utf-8") as tmpf:
                tmpf.write(content_html)
                tmpf.flush()
                tmpf_name = tmpf.name
            try:
                content_markdown = md.convert(tmpf_name)
                markdown_content = content_markdown.markdown
            finally:
                os.remove(tmpf_name)
            email_dict = {
                "sender": str(f"Name: {getattr(msg, 'sender', '').name}, Email: {getattr(msg, 'sender', '').email_address}"),
                "to_recipients": ";".join([str(f"Name: {r.name}, Email: {r.email_address}") for r in getattr(msg, "to_recipients", [])]) if getattr(msg, "to_recipients", None) else "",
                "cc_recipients": ";".join([str(f"Name: {r.name}, Email: {r.email_address}") for r in getattr(msg, "cc_recipients", [])]) if getattr(msg, "cc_recipients", None) else "",
                "bcc_recipients": ";".join([str(f"Name: {r.name}, Email: {r.email_address}") for r in getattr(msg, "bcc_recipients", [])]) if getattr(msg, "bcc_recipients", None) else "",
                "author": str(f"Name: {getattr(msg, 'author', '').name}, Email: {getattr(msg, 'author', '').email_address}"),
                "message_id": getattr(msg, "message_id", ""),
                "is_read": getattr(msg, "is_read", False),
                "main_content": markdown_content,
                "datetime_received": getattr(msg, "datetime_received", None).isoformat() if getattr(msg, "datetime_received", None) else None,
                "subject": getattr(msg, "subject", None),
                "importance": getattr(msg, "importance", None),
            }
            emails.append(email_dict)
        return emails

    def fetch_today_emails(self) -> List[dict]:
        """
        Fetch emails received in the last 24 hours.
        """
        now = datetime.now(self.tz)
        start = now - timedelta(hours=24)
        return self.fetch_emails(since=start, until=now)

    def fetch_all_emails(self) -> List[dict]:
        """
        Fetch all emails in the inbox.
        Returns a list of JSON-serializable dicts, each containing:
        sender, to_recipients, cc_recipients, bcc_recipients, author, message_id, is_read, received_by, main_content (HTML)
        """
        inbox = self.account.inbox
        qs = inbox.all().order_by('-datetime_received')
        emails = []
        md = MarkItDown(enable_plugins=False)
        import tempfile, os
        for i, msg in enumerate(qs):
            content_html = getattr(msg, "body", "").body if hasattr(getattr(msg, "body", ""), "body") else str(getattr(msg, "body", ""))
            with tempfile.NamedTemporaryFile("w+", suffix=".html", delete=False, encoding="utf-8") as tmpf:
                tmpf.write(content_html)
                tmpf.flush()
                tmpf_name = tmpf.name
            try:
                content_markdown = md.convert(tmpf_name)
                markdown_content = content_markdown.markdown
            finally:
                os.remove(tmpf_name)
            email_dict = {
                "sender": str(f"Name: {getattr(msg, 'sender', '').name}, Email: {getattr(msg, 'sender', '').email_address}"),
                "to_recipients": ";".join([str(f"Name: {r.name}, Email: {r.email_address}") for r in getattr(msg, "to_recipients", [])]) if getattr(msg, "to_recipients", None) else "",
                "cc_recipients": ";".join([str(f"Name: {r.name}, Email: {r.email_address}") for r in getattr(msg, "cc_recipients", [])]) if getattr(msg, "cc_recipients", None) else "",
                "bcc_recipients": ";".join([str(f"Name: {r.name}, Email: {r.email_address}") for r in getattr(msg, "bcc_recipients", [])]) if getattr(msg, "bcc_recipients", None) else "",
                "author": str(f"Name: {getattr(msg, 'author', '').name}, Email: {getattr(msg, 'author', '').email_address}"),
                "message_id": getattr(msg, "message_id", ""),
                "is_read": getattr(msg, "is_read", False),
                "main_content": markdown_content,
                "datetime_received": getattr(msg, "datetime_received", None).isoformat() if getattr(msg, "datetime_received", None) else None,
                "subject": getattr(msg, "subject", None),
                "importance": getattr(msg, "importance", None),
            }
            emails.append(email_dict)
        return emails
