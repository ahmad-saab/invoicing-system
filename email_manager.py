#!/usr/bin/env python3
"""
Email Manager for fetching and processing LPO emails
Supports IMAP email fetching with attachment handling
"""
import imaplib
import email
from email.header import decode_header
import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import logging
import tempfile
import shutil
from datetime import datetime, timedelta
import hashlib
import re

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EmailManager:
    """Manage email fetching and processing for invoice system"""
    
    def __init__(self, db_path: str = "test_customers.db"):
        """Initialize email manager with database connection"""
        self.db_path = db_path
        self.temp_dir = Path("temp/email_attachments")
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.connection = None
        self.config = None
        self.known_customers = None  # Cache for known customer emails
        
    def get_email_config(self, config_name: str = "default") -> Dict[str, Any]:
        """Get email configuration from database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM email_config 
            WHERE config_name = ? AND active = 1
        ''', (config_name,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_known_customer_emails(self) -> List[str]:
        """Get list of known customer email addresses from database"""
        if self.known_customers is not None:
            return self.known_customers
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT DISTINCT email FROM customers WHERE active = 1')
        emails = [row[0].lower() for row in cursor.fetchall() if row[0]]
        conn.close()
        
        self.known_customers = emails
        logger.info(f"Loaded {len(emails)} known customer emails")
        return emails
    
    def generate_email_hash(self, msg) -> str:
        """Generate unique hash for email to detect duplicates"""
        # Use Message-ID if available, otherwise use subject + date + sender
        message_id = msg.get('Message-ID', '')
        if message_id:
            return hashlib.md5(message_id.encode()).hexdigest()
        
        # Fallback to subject + date + sender
        subject = msg.get('Subject', '')
        date = msg.get('Date', '')
        sender = msg.get('From', '')
        content = f"{subject}{date}{sender}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def is_email_already_processed(self, email_hash: str) -> bool:
        """Check if email with this hash was already processed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM invoice_queue WHERE email_hash = ? LIMIT 1', (email_hash,))
        exists = cursor.fetchone() is not None
        conn.close()
        
        return exists
    
    def is_likely_order_email(self, subject: str, body_text: str = "") -> bool:
        """Check if email is likely to contain an order/LPO"""
        # Keywords that indicate order/LPO emails
        order_keywords = [
            'lpo', 'purchase order', 'order', 'po #', 'po#', 'po number',
            'purchase', 'quote', 'quotation', 'invoice', 'supply',
            'delivery', 'urgent', 'requirement', 'needed', 'request'
        ]
        
        # Keywords that indicate non-order emails (to be rejected)
        non_order_keywords = [
            'newsletter', 'marketing', 'promotion', 'unsubscribe',
            'meeting', 'calendar', 'reminder', 'notification',
            'receipt', 'thank you', 'confirmation', 'welcome',
            'password reset', 'account', 'login', 'security'
        ]
        
        text_to_check = f"{subject} {body_text}".lower()
        
        # Check for non-order keywords first (reject)
        for keyword in non_order_keywords:
            if keyword in text_to_check:
                return False
        
        # Check for order keywords
        for keyword in order_keywords:
            if keyword in text_to_check:
                return True
        
        # If no clear indicators, check if it has attachments mentioned
        attachment_indicators = ['attached', 'attachment', 'please find', 'pdf', 'excel']
        for indicator in attachment_indicators:
            if indicator in text_to_check:
                return True
        
        return False
    
    def connect_to_email(self, config: Dict[str, Any]) -> bool:
        """Connect to email server using IMAP"""
        try:
            # Validate required fields
            if not config.get('email_address') or config['email_address'] == 'placeholder@example.com':
                logger.error("Invalid email address - please enter a real email address")
                return False
                
            if not config.get('password'):
                logger.error("Password is required - please enter your email password or app password")
                return False
                
            if not config.get('server') or config['server'] == 'mail.example.com':
                logger.error("Invalid server - please enter a real IMAP server (e.g., imap.gmail.com)")
                return False
            
            logger.info(f"Attempting to connect to {config['server']}:{config['port']} as {config['email_address']}")
            
            if config['use_ssl']:
                self.connection = imaplib.IMAP4_SSL(config['server'], config['port'])
            else:
                self.connection = imaplib.IMAP4(config['server'], config['port'])
            
            logger.info(f"IMAP connection established, checking server capabilities...")
            
            # Check server capabilities
            try:
                capabilities = self.connection.capability()[1][0].decode()
                logger.info(f"Server capabilities: {capabilities}")
            except:
                logger.info("Could not retrieve server capabilities")
            
            logger.info(f"Attempting login with username: {config['email_address']}")
            
            # Login
            self.connection.login(config['email_address'], config['password'])
            logger.info(f"Successfully connected to {config['server']} as {config['email_address']}")
            return True
            
        except imaplib.IMAP4.error as e:
            error_msg = str(e)
            logger.error(f"IMAP authentication error: {error_msg}")
            
            if 'AUTHENTICATIONFAILED' in error_msg:
                logger.error("Authentication failed. Possible issues:")
                logger.error("1. Check username format - try full email vs username only")
                logger.error("2. Verify IMAP is enabled on server")
                logger.error("3. Check for IP restrictions")
                logger.error("4. Verify account is not locked/suspended")
            return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def fetch_unread_emails(self, folder: str = "INBOX") -> List[Dict[str, Any]]:
        """Fetch unread emails with enhanced filtering"""
        emails = []
        
        try:
            # Get known customer emails
            known_emails = self.get_known_customer_emails()
            if not known_emails:
                logger.warning("No known customer emails found - skipping fetch")
                return []
                
            # Select folder
            self.connection.select(folder)
            
            # Calculate 24 hours ago date for filtering
            yesterday = datetime.now() - timedelta(days=1)
            date_str = yesterday.strftime("%d-%b-%Y")
            
            # Search for recent unread emails
            search_criteria = f'(UNSEEN SINCE "{date_str}")'
            
            _, message_ids = self.connection.search(None, search_criteria)
            if not message_ids[0]:
                logger.info("No recent unread emails found")
                return []
                
            total_found = len(message_ids[0].split())
            logger.info(f"Found {total_found} recent unread emails, filtering...")
            
            filtered_count = 0
            skipped_not_customer = 0
            skipped_duplicate = 0
            skipped_not_order = 0
            
            for msg_id in message_ids[0].split():
                email_data = self.fetch_email_details(msg_id)
                if not email_data:
                    continue
                    
                # Check if from known customer
                sender_email = email_data.get('sender_email', '').lower()
                if sender_email not in known_emails:
                    skipped_not_customer += 1
                    continue
                
                # Check for duplicates
                email_hash = self.generate_email_hash(email_data['msg'])
                if self.is_email_already_processed(email_hash):
                    skipped_duplicate += 1
                    logger.debug(f"Skipping duplicate email: {email_data.get('subject', 'No subject')}")
                    continue
                
                # Check if likely to be an order email
                subject = email_data.get('subject', '')
                body_text = email_data.get('body_text', '')
                if not self.is_likely_order_email(subject, body_text[:500]):  # Check first 500 chars
                    skipped_not_order += 1
                    logger.debug(f"Skipping non-order email: {subject}")
                    continue
                
                # Add email hash to the data
                email_data['email_hash'] = email_hash
                emails.append(email_data)
                filtered_count += 1
            
            logger.info(f"Email filtering results:")
            logger.info(f"  - Total found: {total_found}")
            logger.info(f"  - Accepted: {filtered_count}")
            logger.info(f"  - Skipped (not customer): {skipped_not_customer}")
            logger.info(f"  - Skipped (duplicate): {skipped_duplicate}")
            logger.info(f"  - Skipped (not order): {skipped_not_order}")
            
            return emails
            
        except Exception as e:
            logger.error(f"Failed to fetch emails: {e}")
            return []
    
    def fetch_email_details(self, msg_id: bytes) -> Dict[str, Any]:
        """Fetch details of a single email"""
        try:
            # Fetch email data
            _, msg_data = self.connection.fetch(msg_id, '(RFC822)')
            
            # Parse email
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Extract email details
                    subject = self.decode_header_value(msg['Subject'])
                    from_addr = self.decode_header_value(msg['From'])
                    date = msg['Date']
                    message_id = msg['Message-ID']
                    
                    # Extract sender email
                    sender_email = self.extract_email_address(from_addr)
                    
                    # Get attachments
                    attachments = self.extract_attachments(msg)
                    
                    # Extract body text for filtering
                    body_text = self.get_email_body_text(msg)
                    
                    # If no attachments, extract email body
                    if not attachments:
                        email_body = self.extract_email_body(msg, message_id)
                        if email_body:
                            attachments = [email_body]
                    
                    return {
                        'message_id': message_id,
                        'subject': subject,
                        'from': from_addr,
                        'sender_email': sender_email,
                        'date': date,
                        'attachments': attachments,
                        'msg_id': msg_id.decode() if isinstance(msg_id, bytes) else msg_id,
                        'body_text': body_text,
                        'msg': msg  # Include original message for hash generation
                    }
            
        except Exception as e:
            logger.error(f"Failed to fetch email details: {e}")
            return None
    
    def get_email_body_text(self, msg) -> str:
        """Extract plain text from email body for filtering purposes"""
        body_text = ""
        
        try:
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_text += payload.decode('utf-8', errors='ignore')
                    elif content_type == "text/html":
                        # Get HTML as fallback if no plain text
                        if not body_text:
                            payload = part.get_payload(decode=True)
                            if payload:
                                html_content = payload.decode('utf-8', errors='ignore')
                                # Simple HTML tag removal for basic text
                                import re
                                body_text = re.sub(r'<[^>]+>', '', html_content)
            else:
                # Single part message
                payload = msg.get_payload(decode=True)
                if payload:
                    body_text = payload.decode('utf-8', errors='ignore')
                    
        except Exception as e:
            logger.debug(f"Failed to extract body text: {e}")
            
        return body_text.strip()[:1000]  # Return first 1000 chars
    
    def decode_header_value(self, header_value: str) -> str:
        """Decode email header value"""
        if not header_value:
            return ""
        
        decoded_parts = decode_header(header_value)
        decoded_string = ""
        
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                if encoding:
                    decoded_string += part.decode(encoding)
                else:
                    decoded_string += part.decode('utf-8', errors='ignore')
            else:
                decoded_string += part
        
        return decoded_string
    
    def extract_email_address(self, from_field: str) -> str:
        """Extract email address from From field"""
        import re
        email_pattern = r'<(.+?)>'
        match = re.search(email_pattern, from_field)
        if match:
            return match.group(1)
        # If no angle brackets, assume the whole thing is the email
        return from_field.strip()
    
    def extract_attachments(self, msg) -> List[Dict[str, str]]:
        """Extract attachments from email"""
        attachments = []
        
        for part in msg.walk():
            if part.get_content_disposition() == 'attachment':
                filename = part.get_filename()
                if filename:
                    # Decode filename if needed
                    filename = self.decode_header_value(filename)
                    
                    # Save attachment
                    file_path = self.temp_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{filename}"
                    
                    with open(file_path, 'wb') as f:
                        f.write(part.get_payload(decode=True))
                    
                    attachments.append({
                        'filename': filename,
                        'path': str(file_path),
                        'content_type': part.get_content_type()
                    })
                    
                    logger.info(f"Saved attachment: {filename}")
        
        return attachments
    
    def extract_email_body(self, msg, message_id: str) -> Dict[str, str]:
        """Extract and save email body content"""
        body_content = None
        content_type = 'text/plain'
        
        # Try to get HTML content first, then plain text
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/html":
                    body_content = part.get_payload(decode=True)
                    content_type = 'text/html'
                    break
                elif part.get_content_type() == "text/plain" and body_content is None:
                    body_content = part.get_payload(decode=True)
                    content_type = 'text/plain'
        else:
            body_content = msg.get_payload(decode=True)
            content_type = msg.get_content_type()
        
        if body_content:
            # Determine file extension
            ext = '.html' if 'html' in content_type else '.txt'
            
            # Create filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"email_body_{timestamp}_{message_id.replace('<', '').replace('>', '').replace('@', '_')}{ext}"
            
            # Save email body
            file_path = self.temp_dir / filename
            
            # Handle encoding
            if isinstance(body_content, bytes):
                with open(file_path, 'wb') as f:
                    f.write(body_content)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(body_content)
            
            logger.info(f"Saved email body: {filename}")
            
            return {
                'filename': filename,
                'path': str(file_path),
                'content_type': content_type
            }
        
        return None
    
    def add_to_queue(self, email_data: Dict[str, Any]) -> List[int]:
        """Add email attachments to processing queue"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        queue_ids = []
        
        try:
            # Get customer email from sender
            sender_email = email_data['sender_email']
            
            # Check if customer exists
            cursor.execute('''
                SELECT email FROM customers 
                WHERE email = ? AND active = 1
            ''', (sender_email,))
            
            customer = cursor.fetchone()
            customer_email = customer[0] if customer else sender_email
            
            # Add each attachment to queue
            for attachment in email_data.get('attachments', []):
                # Check if it's a supported format - now supporting ALL formats
                filename = attachment['filename'].lower()
                supported_formats = [
                    '.pdf', '.xlsx', '.xls', '.html', '.htm', '.txt',
                    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff',
                    '.docx', '.doc', '.csv', '.json', '.xml'
                ]
                
                if any(filename.endswith(ext) for ext in supported_formats) or filename.startswith('email_body_'):
                    cursor.execute('''
                        INSERT INTO invoice_queue 
                        (source, source_id, filename, file_path, customer_email, status, email_hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', ('email', email_data['message_id'], attachment['filename'], 
                          attachment['path'], customer_email, 'pending', 
                          email_data.get('email_hash', '')))
                    
                    queue_ids.append(cursor.lastrowid)
                    logger.info(f"Added {attachment['filename']} to queue (ID: {cursor.lastrowid})")
                else:
                    logger.info(f"Skipped unsupported file: {attachment['filename']}")
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Failed to add to queue: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        return queue_ids
    
    def mark_as_read(self, msg_id: str):
        """Mark email as read"""
        try:
            self.connection.store(msg_id.encode(), '+FLAGS', '\\Seen')
            logger.info(f"Marked email {msg_id} as read")
        except Exception as e:
            logger.error(f"Failed to mark email as read: {e}")
    
    def disconnect(self):
        """Disconnect from email server"""
        if self.connection:
            try:
                self.connection.close()
                self.connection.logout()
                logger.info("Disconnected from email server")
            except:
                pass
    
    def fetch_and_queue_emails(self, config_name: str = "default") -> Dict[str, Any]:
        """Main method to fetch emails and add to processing queue"""
        results = {
            'success': False,
            'emails_fetched': 0,
            'attachments_queued': 0,
            'errors': []
        }
        
        # Get configuration
        self.config = self.get_email_config(config_name)
        if not self.config:
            results['errors'].append("No email configuration found")
            return results
        
        if not self.config.get('password'):
            results['errors'].append("Email password not configured")
            return results
        
        # Connect to email
        if not self.connect_to_email(self.config):
            results['errors'].append("Failed to connect to email server")
            return results
        
        try:
            # Fetch unread emails
            folders = self.config.get('folders', 'INBOX').split(',')
            
            for folder in folders:
                emails = self.fetch_unread_emails(folder.strip())
                results['emails_fetched'] += len(emails)
                
                # Process each email
                for email_data in emails:
                    # Add to queue
                    queue_ids = self.add_to_queue(email_data)
                    results['attachments_queued'] += len(queue_ids)
                    
                    # Mark as read if configured
                    if not self.config.get('keep_unread'):
                        self.mark_as_read(email_data['msg_id'])
            
            results['success'] = True
            
        except Exception as e:
            results['errors'].append(str(e))
            logger.error(f"Error during email fetching: {e}")
        
        finally:
            self.disconnect()
        
        return results


# Test function
if __name__ == "__main__":
    manager = EmailManager()
    
    # Test configuration
    config = manager.get_email_config()
    if config:
        print("Email Configuration:")
        print(json.dumps({k: v for k, v in config.items() if k != 'password'}, indent=2))
    else:
        print("No email configuration found")
    
    # You can test fetching emails here if password is configured
    # results = manager.fetch_and_queue_emails()
    # print("\nFetch Results:")
    # print(json.dumps(results, indent=2))