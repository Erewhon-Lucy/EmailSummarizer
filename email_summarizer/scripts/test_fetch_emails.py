from email_summarizer.app.utils.exchange_client import ExchangeClient

if __name__ == "__main__":
    target_email = "alfredzou@thebig1.biz"
    client = ExchangeClient(target_email=target_email)
    # Test fetch_today_emails
    emails_today = client.fetch_today_emails()
    import json
    print("=== fetch_today_emails ===")
    print(json.dumps(emails_today, indent=2, ensure_ascii=False))

    # Test fetch_all_emails
    emails_all = client.fetch_all_emails()
    print("=== fetch_all_emails ===")
    print(json.dumps(emails_all, indent=2, ensure_ascii=False))
