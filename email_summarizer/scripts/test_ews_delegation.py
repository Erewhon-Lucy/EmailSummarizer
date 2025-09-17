import logging
from email_summarizer.app.utils.ews_delegation import EWSDelegationManager

# =========================
# MANUAL PARAMETERS (EDIT)
# =========================
EWS_URL = "https://mail.thebig1.biz/EWS/Exchange.asmx"
OWNER_UPN = "alfredzou@thebig1.biz"
OWNER_USERNAME = r"y\alfredzou"
OWNER_PASSWORD = "Msft@3652022"
VERIFY_TLS = True
DELEGATE_UPN = "dongchen1@thebig1.biz"
UPDATE_LEVEL = "Reviewer"

# Toggle which steps run
RUN_LIST_BEFORE = True
RUN_ADD_IF_NOT_EXISTS = False   # Add as Reviewer explicitly (if you know they are absent)
RUN_UPDATE = False              # Force update to UPDATE_LEVEL
RUN_ENSURE = True               # Idempotent ensure Reviewer
RUN_LIST_AFTER = True

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ews_delegation_test")

def test_get_inbox_level(delegation_manager):
    """Test retrieving inbox permission levels for all delegates."""
    logger.info("Testing get_inbox_level method...")
    try:
        print("\n=== Current Inbox Delegation Levels ===")
        found_delegates = False
        for upn, level in delegation_manager.get_inbox_level():
            found_delegates = True
            print(f"Delegate: {upn}, Permission Level: {level}")
        if not found_delegates:
            print("No delegates found for this mailbox.")
    except Exception as e:
        logger.error(f"Error in get_inbox_level: {e}")
        raise

def test_ensure_inbox_reviewer(delegation_manager, delegate_upn):
    """Test ensuring a delegate has Reviewer permission."""
    logger.info(f"Testing ensure_inbox_reviewer method for {delegate_upn}...")
    try:
        print(f"\n=== Ensuring Reviewer Access for {delegate_upn} ===")
        success, message = delegation_manager.ensure_inbox_reviewer(delegate_upn)
        status = "Succeeded" if success else "Failed"
        print(f"Operation {status}: {message}")
        return success, message
    except Exception as e:
        logger.error(f"Error in ensure_inbox_reviewer: {e}")
        raise

def test_update_delegate_inbox(delegation_manager, delegate_upn, level):
    """Test updating a delegate's inbox permission level."""
    logger.info(f"Testing update_delegate_inbox method for {delegate_upn} with level {level}...")
    try:
        print(f"\n=== Updating Inbox Access to {level} for {delegate_upn} ===")
        success, message = delegation_manager.update_delegate_inbox(delegate_upn, level)
        status = "Succeeded" if success else "Failed"
        print(f"Operation {status}: {message}")
        return success, message
    except Exception as e:
        logger.error(f"Error in update_delegate_inbox: {e}")
        raise

def test_add_delegate_inbox_reviewer(delegation_manager, delegate_upn):
    """Test adding a delegate with Reviewer permission."""
    logger.info(f"Testing add_delegate_inbox_reviewer method for {delegate_upn}...")
    try:
        print(f"\n=== Adding Delegate {delegate_upn} with Reviewer Access ===")
        success, message = delegation_manager.add_delegate_inbox_reviewer(
            delegate_upn,
            receive_copies=False,
            view_private=False
        )
        status = "Succeeded" if success else "Failed"
        print(f"Operation {status}: {message}")
        return success, message
    except Exception as e:
        logger.error(f"Error in add_delegate_inbox_reviewer: {e}")
        raise

def main():
    # Basic safety checks
    missing = []
    if not EWS_URL: missing.append("EWS_URL")
    if not OWNER_UPN: missing.append("OWNER_UPN")
    if not OWNER_USERNAME: missing.append("OWNER_USERNAME")
    if not OWNER_PASSWORD: missing.append("OWNER_PASSWORD")
    if missing:
        raise SystemExit(f"Fill required constants first: {', '.join(missing)}")

    manager = EWSDelegationManager(
        ews_url=EWS_URL,
        owner_upn=OWNER_UPN,
        owner_username=OWNER_USERNAME,
        owner_password=OWNER_PASSWORD,
        verify_tls=VERIFY_TLS
    )

    print("\n========== EWS Delegation Test Harness ==========")
    print(f"Owner mailbox: {OWNER_UPN}")
    print(f"Delegate target: {DELEGATE_UPN}")
    print("=================================================\n")

    try:
        if RUN_LIST_BEFORE:
            print("[STEP] List delegates (before)")
            test_get_inbox_level(manager)

        if RUN_ADD_IF_NOT_EXISTS:
            print("[STEP] Add delegate as Reviewer (may fail if already exists)")
            test_add_delegate_inbox_reviewer(manager, DELEGATE_UPN)

        if RUN_UPDATE:
            print(f"[STEP] Update delegate to level: {UPDATE_LEVEL}")
            test_update_delegate_inbox(manager, DELEGATE_UPN, UPDATE_LEVEL)

        if RUN_ENSURE:
            print("[STEP] Ensure delegate is Reviewer (idempotent)")
            test_ensure_inbox_reviewer(manager, DELEGATE_UPN)

        if RUN_LIST_AFTER:
            print("[STEP] List delegates (after)")
            test_get_inbox_level(manager)

        print("\nAll selected steps completed.")
    except Exception:
        print("\nOne or more steps failed; see logs above.")
        raise

if __name__ == "__main__":
    main()