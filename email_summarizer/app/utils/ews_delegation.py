import requests
from requests.auth import HTTPBasicAuth
from requests_ntlm import HttpNtlmAuth
import xml.etree.ElementTree as ET
from typing import Iterator, Tuple, Optional


class EWSDelegationManager:
    """
    Class for managing Exchange Web Services (EWS) delegation.
    Provides methods to get, add, update, and ensure inbox delegation permissions.
    """
    
    # Namespace constants
    NS_M = {"m": "http://schemas.microsoft.com/exchange/services/2006/messages"}
    NS_T = {"t": "http://schemas.microsoft.com/exchange/services/2006/types"}
    NS = {**NS_M, **NS_T}
    
    def __init__(self, ews_url: str, owner_upn: str, owner_username: str, owner_password: str, verify_tls: bool = True):
        """
        Initialize the EWSDelegationManager with owner credentials and EWS URL.
        
        Args:
            ews_url: URL for Exchange Web Services
            owner_upn: Owner's user principal name
            owner_username: Owner's username for authentication
            owner_password: Owner's password for authentication
            verify_tls: Whether to verify TLS certificates (default: True)
        """
        self.ews_url = ews_url
        self.owner_upn = owner_upn
        self.owner_username = owner_username
        self.owner_password = owner_password
        self.verify_tls = verify_tls
    
    def _post_ews(self, soap_xml: str, anchor: str = None) -> str:
        """
        Post SOAP XML to EWS and return the response.
        
        Args:
            soap_xml: SOAP XML to send
            anchor: Optional X-AnchorMailbox header
            
        Returns:
            Response text from EWS
        """
        headers = {"Content-Type": "text/xml; charset=utf-8"}
        if anchor:
            headers["X-AnchorMailbox"] = anchor  # on-prem 非必须，加上无害
        resp = requests.post(
            self.ews_url,
            data=soap_xml.encode("utf-8"),
            headers=headers,
            # auth=HTTPBasicAuth(self.owner_username, self.owner_password), 
            auth=HttpNtlmAuth(self.owner_username, self.owner_password),
            timeout=60,
            verify=self.verify_tls,
            allow_redirects=False
        )
        
        # check authentication errors
        if resp.status_code == 401:
            raise ValueError(
                f"401 Unauthorized. WWW-Authenticate: {resp.headers.get('WWW-Authenticate')}"
            )

        resp.raise_for_status()
        
        # Check if response is XML or HTML
        response_text = resp.text
        if response_text.strip().startswith("<!DOCTYPE HTML") or response_text.strip().startswith("<html"):
            raise ValueError(f"Received HTML response instead of XML. This typically indicates an authentication issue or incorrect EWS URL. Check your credentials and URL. First 100 chars: {response_text[:100]}")
        
        return response_text
    
    def _soap_header(self) -> str:
        """
        Generate SOAP header without impersonation.
        
        Returns:
            SOAP header XML string
        """
        # 无Imperson场景：不包含 <ExchangeImpersonation>
        return "<soap:Header><t:RequestServerVersion Version=\"Exchange2010_SP2\"/></soap:Header>"
    
    def get_inbox_level(self) -> Iterator[Tuple[str, Optional[str]]]:
        """
        Get inbox permission levels for all delegates of the owner.
        
        Returns:
            Iterator of tuples containing (delegate_upn, permission_level)
        """
        # Clean up the SOAP XML by removing indentation
        soap = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types" xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages">
{self._soap_header()}
<soap:Body>
<m:GetDelegate IncludePermissions="true">
<m:Mailbox><t:EmailAddress>{self.owner_upn}</t:EmailAddress></m:Mailbox>
<m:UserIds>
<!-- 不指定具体 delegate，GetDelegate 会返回所有委派。如需只查某个 delegate，可在这里放 <t:UserId> -->
</m:UserIds>
</m:GetDelegate>
</soap:Body>
</soap:Envelope>"""
        xml = self._post_ews(soap, self.owner_upn)
        
        # Debug: Print the first 100 characters of the response to see where the error might be
        print(f"DEBUG: XML response first 100 chars: {xml[:100]}")
        
        try:
            root = ET.fromstring(xml)
        except ET.ParseError as e:
            print(f"DEBUG: XML Parse Error: {e}")
            print(f"DEBUG: First 200 chars of response: {xml[:200]}")
            raise
        # 找到 owner 的所有委派条目，逐个看 InboxFolderPermissionLevel
        for du in root.findall(".//t:DelegateUser", self.NS):
            upn = du.find("./t:UserId/t:PrimarySmtpAddress", self.NS)
            if upn is None or not (upn.text or "").strip():
                continue
            inbox = du.find("./t:DelegatePermissions/t:InboxFolderPermissionLevel", self.NS)
            yield upn.text.lower(), (inbox.text if inbox is not None else None)
    
    def add_delegate_inbox_reviewer(self, delegate_upn: str,
                                   receive_copies: bool = False, view_private: bool = False,
                                   deliver_meeting: str = "DelegatesAndSendInformationToMe") -> Tuple[bool, str]:
        """
        Add a delegate with Reviewer permission level for the inbox.
        
        Args:
            delegate_upn: Delegate's user principal name
            receive_copies: Whether to send meeting message copies to delegate
            view_private: Whether delegate can view private items
            deliver_meeting: How to deliver meeting requests
            
        Returns:
            Tuple of (success, message)
        """
        soap = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types" xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages">
{self._soap_header()}
<soap:Body>
<m:AddDelegate>
<m:Mailbox><t:EmailAddress>{self.owner_upn}</t:EmailAddress></m:Mailbox>
<m:DelegateUsers>
<t:DelegateUser>
<t:UserId><t:PrimarySmtpAddress>{delegate_upn}</t:PrimarySmtpAddress></t:UserId>
<t:DelegatePermissions>
<t:InboxFolderPermissionLevel>Reviewer</t:InboxFolderPermissionLevel>
</t:DelegatePermissions>
<t:ReceiveCopiesOfMeetingMessages>{str(receive_copies).lower()}</t:ReceiveCopiesOfMeetingMessages>
<t:ViewPrivateItems>{str(view_private).lower()}</t:ViewPrivateItems>
</t:DelegateUser>
</m:DelegateUsers>
<m:DeliverMeetingRequests>{deliver_meeting}</m:DeliverMeetingRequests>
</m:AddDelegate>
</soap:Body>
</soap:Envelope>"""
        xml = self._post_ews(soap, self.owner_upn)
        root = ET.fromstring(xml)
        resp = root.find(".//m:AddDelegateResponse", self.NS_M)
        if resp is not None and resp.attrib.get("ResponseClass") == "Success":
            return True, "AddDelegate Success"
        code = root.find(".//m:ResponseCode", self.NS_M)
        return False, (code.text if code is not None else "UnknownError")
    
    def update_delegate_inbox(self, delegate_upn: str, level: str = "Reviewer") -> Tuple[bool, str]:
        """
        Update a delegate's inbox permission level.
        
        Args:
            delegate_upn: Delegate's user principal name
            level: Inbox permission level to set
            
        Returns:
            Tuple of (success, message)
        """
        soap = f"""<?xml version="1.0" encoding="utf-8"?>
<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:t="http://schemas.microsoft.com/exchange/services/2006/types" xmlns:m="http://schemas.microsoft.com/exchange/services/2006/messages">
{self._soap_header()}
<soap:Body>
<m:UpdateDelegate>
<m:Mailbox><t:EmailAddress>{self.owner_upn}</t:EmailAddress></m:Mailbox>
<m:DelegateUsers>
<t:DelegateUser>
<t:UserId><t:PrimarySmtpAddress>{delegate_upn}</t:PrimarySmtpAddress></t:UserId>
<t:DelegatePermissions>
<t:InboxFolderPermissionLevel>{level}</t:InboxFolderPermissionLevel>
</t:DelegatePermissions>
</t:DelegateUser>
</m:DelegateUsers>
<m:DeliverMeetingRequests>DelegatesAndSendInformationToMe</m:DeliverMeetingRequests>
</m:UpdateDelegate>
</soap:Body>
</soap:Envelope>"""
        xml = self._post_ews(soap, self.owner_upn)
        root = ET.fromstring(xml)
        resp = root.find(".//m:UpdateDelegateResponse", self.NS_M)
        if resp is not None and resp.attrib.get("ResponseClass") == "Success":
            return True, "UpdateDelegate Success"
        code = root.find(".//m:ResponseCode", self.NS_M)
        return False, (code.text if code is not None else "UnknownError")
    
    def ensure_inbox_reviewer(self, delegate_upn: str) -> Tuple[bool, str]:
        """
        Ensure a delegate has Reviewer permission for the inbox.
        This is an idempotent operation that will add or update the delegate as needed.
        
        Args:
            delegate_upn: Delegate's user principal name
            
        Returns:
            Tuple of (success, message)
        """
        # 幂等：先查该 owner 的所有委派，看看是否已有目标 delegate
        found_level = None
        for upn, level in self.get_inbox_level():
            if upn == delegate_upn.lower():
                found_level = level
                break
        if found_level is None:
            return self.add_delegate_inbox_reviewer(delegate_upn)
        if found_level != "Reviewer":
            return self.update_delegate_inbox(delegate_upn, "Reviewer")
        return True, "Already Reviewer"
