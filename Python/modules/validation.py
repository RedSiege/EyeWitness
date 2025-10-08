#!/usr/bin/env python3
"""
URL and input validation module for EyeWitness
Provides robust validation for URLs and other user inputs
"""

import re
import socket
from urllib.parse import urlparse, urlunparse
import ipaddress


def validate_url(url, allow_private=True, require_scheme=True):
    """
    Validate a URL for safety and correctness
    
    Args:
        url (str): URL to validate
        allow_private (bool): Whether to allow private/local IPs
        require_scheme (bool): Whether URL must have http/https scheme
    
    Returns:
        tuple: (is_valid, error_message, normalized_url)
    """
    if not url or not isinstance(url, str):
        return False, "URL cannot be empty", None
    
    # Basic length check to prevent DoS
    if len(url) > 2048:
        return False, "URL too long (max 2048 characters)", None
    
    # Check for null bytes or other dangerous characters
    if '\x00' in url or '\r' in url or '\n' in url:
        return False, "URL contains invalid characters", None
    
    # Add scheme if missing and not required
    if not require_scheme and not url.startswith(('http://', 'https://')):
        url = 'http://' + url
    
    try:
        parsed = urlparse(url)
        
        # Validate scheme
        if parsed.scheme not in ['http', 'https']:
            return False, f"Invalid scheme '{parsed.scheme}' - only http/https allowed", None
        
        # Validate host
        if not parsed.netloc:
            return False, "No host specified in URL", None
        
        # Extract hostname and port
        hostname = parsed.hostname
        if not hostname:
            return False, "Invalid hostname in URL", None
        
        # Check for IP address
        try:
            ip = ipaddress.ip_address(hostname)
            if not allow_private and ip.is_private:
                return False, f"Private IP address {hostname} not allowed", None
            if ip.is_multicast:
                return False, f"Multicast IP address {hostname} not allowed", None
            if ip.is_reserved:
                return False, f"Reserved IP address {hostname} not allowed", None
        except ValueError:
            # Not an IP, check as hostname
            # Basic hostname validation
            hostname_regex = re.compile(
                r'^([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9])' +
                r'(\.([a-zA-Z0-9]|[a-zA-Z0-9][a-zA-Z0-9\-]*[a-zA-Z0-9]))*$'
            )
            if not hostname_regex.match(hostname):
                return False, f"Invalid hostname format: {hostname}", None
        
        # Validate port if specified
        if parsed.port:
            if not 1 <= parsed.port <= 65535:
                return False, f"Invalid port number: {parsed.port}", None
        
        # Check for suspicious patterns
        suspicious_patterns = [
            r'\.\./',  # Directory traversal
            r'%00',    # Null byte
            r'%0[dD]', # CR
            r'%0[aA]', # LF
            r'<script', # XSS attempt
            r'javascript:', # XSS attempt
        ]
        
        for pattern in suspicious_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return False, f"URL contains suspicious pattern", None
        
        # Reconstruct normalized URL
        normalized = urlunparse(parsed)
        
        return True, None, normalized
        
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}", None


def validate_url_list(urls, allow_private=True, require_scheme=True):
    """
    Validate a list of URLs
    
    Args:
        urls (list): List of URLs to validate
        allow_private (bool): Whether to allow private/local IPs
        require_scheme (bool): Whether URLs must have http/https scheme
    
    Returns:
        tuple: (valid_urls, invalid_urls)
               where invalid_urls is a list of (url, error) tuples
    """
    valid_urls = []
    invalid_urls = []
    
    for url in urls:
        is_valid, error, normalized = validate_url(url, allow_private, require_scheme)
        if is_valid:
            valid_urls.append(normalized)
        else:
            invalid_urls.append((url, error))
    
    return valid_urls, invalid_urls


def validate_file_path(path, must_exist=False, allow_directory_traversal=False):
    """
    Validate a file path for safety
    
    Args:
        path (str): File path to validate
        must_exist (bool): Whether file must already exist
        allow_directory_traversal (bool): Whether to allow .. in paths
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not path:
        return False, "Path cannot be empty"
    
    # Check for null bytes
    if '\x00' in path:
        return False, "Path contains null bytes"
    
    # Check for directory traversal
    if not allow_directory_traversal and '..' in path:
        return False, "Directory traversal not allowed"
    
    # Additional platform-specific validation could go here
    
    return True, None


def sanitize_filename(filename):
    """
    Sanitize a filename to be safe for filesystem usage
    
    Args:
        filename (str): Filename to sanitize
    
    Returns:
        str: Sanitized filename
    """
    # Remove null bytes
    filename = filename.replace('\x00', '')
    
    # Replace problematic characters
    invalid_chars = '<>:"|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')
    
    # Remove control characters
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # Limit length
    max_length = 200  # Leave room for extensions
    if len(filename) > max_length:
        name, ext = filename[:max_length], filename[max_length:]
        if '.' in ext:
            ext = ext[ext.rfind('.'):]
            filename = name[:max_length-len(ext)] + ext
        else:
            filename = name
    
    # Ensure it's not empty
    if not filename:
        filename = 'unnamed'
    
    return filename


def get_url_validation_errors(urls):
    """
    Get detailed validation errors for a list of URLs
    
    Args:
        urls (list): List of URLs to validate
    
    Returns:
        str: Formatted error message or None if all valid
    """
    _, invalid_urls = validate_url_list(urls)
    
    if not invalid_urls:
        return None
    
    error_msg = "URL validation errors:\n"
    for url, error in invalid_urls:
        error_msg += f"  - {url}: {error}\n"
    
    return error_msg