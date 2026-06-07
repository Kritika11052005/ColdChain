from typing import List, Dict

def deduplicate_contacts(contacts: List[dict]) -> List[dict]:
    seen_emails = set()
    unique_contacts = []
    
    for contact in contacts:
        email = contact.get("email")
        if email:
            email_lower = email.strip().lower()
            if email_lower in seen_emails:
                continue
            seen_emails.add(email_lower)
        unique_contacts.append(contact)
        
    return unique_contacts
