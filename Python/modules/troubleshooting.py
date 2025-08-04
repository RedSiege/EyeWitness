#!/usr/bin/env python3
"""
Troubleshooting and error message module for EyeWitness
Provides actionable error messages and troubleshooting guidance
"""

# Error message templates with troubleshooting guidance
ERROR_MESSAGES = {
    'timeout': {
        'message': 'Connection timeout to {url}',
        'guidance': [
            'Try increasing timeout with --timeout 60',
            'Check if the target is accessible: ping {host}',
            'Verify firewall rules allow outbound connections',
            'If behind a proxy, use --proxy-ip and --proxy-port'
        ]
    },
    'connection_refused': {
        'message': 'Connection refused by {url}',
        'guidance': [
            'Verify the service is running on the target',
            'Check if the correct port is specified',
            'Try accessing the URL in a browser first',
            'Target may be blocking automated requests'
        ]
    },
    'connection_reset': {
        'message': 'Connection reset by {url}',
        'guidance': [
            'Target may have rate limiting - try --delay 5',
            'Reduce thread count with --threads 5',
            'Add jitter between requests with --jitter 3',
            'Target may be detecting automated scanning'
        ]
    },
    'ssl_error': {
        'message': 'SSL/TLS error connecting to {url}',
        'guidance': [
            'Certificate may be self-signed or expired',
            'Try accessing with http:// instead of https://',
            'Update your SSL certificates: update-ca-certificates',
            'Target may require specific TLS version'
        ]
    },
    'dns_error': {
        'message': 'Cannot resolve hostname for {url}',
        'guidance': [
            'Check DNS settings: nslookup {host}',
            'Verify hostname spelling',
            'Try using IP address instead of hostname',
            'Add --resolve flag to attempt resolution'
        ]
    },
    'memory_error': {
        'message': 'Running low on memory',
        'guidance': [
            'Reduce thread count with --threads 5',
            'Process URLs in smaller batches',
            'Close other applications to free memory',
            'Current usage: {memory_info}'
        ]
    },
    'disk_space': {
        'message': 'Insufficient disk space in {path}',
        'guidance': [
            'Free up disk space or choose different output directory',
            'Current: {available_gb:.1f}GB available of {total_gb:.1f}GB',
            'Screenshots require ~100KB-1MB per target',
            'Use --output to specify different directory'
        ]
    },
    'firefox_missing': {
        'message': 'Firefox browser not found',
        'guidance': [
            'Install Firefox: sudo apt install firefox-esr',
            'On Windows: Navigate to setup folder and run .\\setup.ps1 as Administrator',
            'On macOS: brew install --cask firefox',
            'Ensure Firefox is in system PATH'
        ]
    },
    'geckodriver_missing': {
        'message': 'Geckodriver not found',
        'guidance': [
            'Run setup script from setup directory: ./setup.sh',
            'Download manually from: https://github.com/mozilla/geckodriver/releases',
            'Place geckodriver in system PATH',
            'On Linux: sudo apt install firefox-geckodriver'
        ]
    },
    'permission_denied': {
        'message': 'Permission denied: {path}',
        'guidance': [
            'Check file permissions: ls -la {path}',
            'Run with appropriate user permissions',
            'Output directory may be write-protected',
            'On Windows: Run as Administrator if needed'
        ]
    },
    'invalid_url': {
        'message': 'Invalid URL format: {url}',
        'guidance': [
            'URLs should be in format: http://example.com',
            'Check for special characters or spaces',
            'Encode special characters properly',
            'Remove any leading/trailing whitespace'
        ]
    },
    'file_not_found': {
        'message': 'File not found: {path}',
        'guidance': [
            'Check file path and spelling',
            'Use absolute paths to avoid confusion',
            'Ensure file exists: ls {path}',
            'Check current directory: pwd'
        ]
    }
}


def get_error_guidance(error_type, **kwargs):
    """
    Get formatted error message with troubleshooting guidance
    
    Args:
        error_type (str): Type of error from ERROR_MESSAGES
        **kwargs: Variables to format into the message
        
    Returns:
        str: Formatted error message with guidance
    """
    if error_type not in ERROR_MESSAGES:
        return f"Error: {error_type}"
    
    error_info = ERROR_MESSAGES[error_type]
    message = error_info['message'].format(**kwargs)
    
    output = f"\n[!] {message}\n"
    output += "[*] Troubleshooting suggestions:\n"
    
    for suggestion in error_info['guidance']:
        formatted_suggestion = suggestion.format(**kwargs)
        output += f"    - {formatted_suggestion}\n"
    
    return output


def format_exception(e, context=""):
    """
    Format an exception with context and suggestions
    
    Args:
        e (Exception): The exception to format
        context (str): Additional context about what was happening
        
    Returns:
        str: Formatted error message
    """
    error_type = type(e).__name__
    error_msg = str(e)
    
    output = f"\n[!] {error_type}: {error_msg}"
    if context:
        output += f"\n[*] Context: {context}"
    
    # Add specific guidance based on exception type
    if "timeout" in error_msg.lower():
        output += "\n[*] Try: --timeout 60 or check network connectivity"
    elif "connection" in error_msg.lower():
        output += "\n[*] Try: Check firewall, use --proxy-ip if needed"
    elif "memory" in error_msg.lower():
        output += "\n[*] Try: Reduce --threads or close other applications"
    elif "permission" in error_msg.lower():
        output += "\n[*] Try: Check file permissions or run with appropriate privileges"
    
    return output


def get_progress_message(current, total, start_time=None):
    """
    Get formatted progress message with ETA
    
    Args:
        current (int): Current progress
        total (int): Total items
        start_time (float): Start time from time.time()
        
    Returns:
        str: Formatted progress message
    """
    percentage = (current / total) * 100 if total > 0 else 0
    
    if start_time:
        import time
        elapsed = time.time() - start_time
        if current > 0:
            rate = current / elapsed
            remaining = (total - current) / rate if rate > 0 else 0
            
            # Format time remaining
            if remaining < 60:
                time_str = f"{int(remaining)}s"
            elif remaining < 3600:
                time_str = f"{int(remaining / 60)}m {int(remaining % 60)}s"
            else:
                hours = int(remaining / 3600)
                minutes = int((remaining % 3600) / 60)
                time_str = f"{hours}h {minutes}m"
            
            return f"[*] Progress: {current}/{total} ({percentage:.1f}%) - ETA: {time_str}"
    
    return f"[*] Progress: {current}/{total} ({percentage:.1f}%)"


class TroubleshootingTips:
    """Collection of troubleshooting tips for common issues"""
    
    PERFORMANCE_TIPS = [
        "Reduce thread count for stability: --threads 5",
        "Add delay between requests: --delay 2",
        "Enable jitter for randomization: --jitter 5",
        "Process in smaller batches for large scans"
    ]
    
    NETWORK_TIPS = [
        "Check firewall rules and proxy settings",
        "Verify DNS resolution: nslookup <target>",
        "Test connectivity: ping <target>",
        "Increase timeout for slow connections: --timeout 60"
    ]
    
    SETUP_TIPS = [
        "Run setup script with appropriate permissions",
        "Ensure Firefox and geckodriver are installed",
        "Check PATH environment variable",
        "Verify all dependencies with: pip list"
    ]
    
    @staticmethod
    def get_tips_for_error(error_string):
        """Get relevant tips based on error string"""
        error_lower = error_string.lower()
        
        if any(word in error_lower for word in ['timeout', 'slow', 'performance']):
            return TroubleshootingTips.PERFORMANCE_TIPS
        elif any(word in error_lower for word in ['connection', 'network', 'refused']):
            return TroubleshootingTips.NETWORK_TIPS
        elif any(word in error_lower for word in ['firefox', 'gecko', 'driver', 'setup']):
            return TroubleshootingTips.SETUP_TIPS
        
        return []