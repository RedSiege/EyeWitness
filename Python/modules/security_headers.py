#!/usr/bin/env python3
"""
HTTP header collection module for EyeWitness
Collects HTTP response headers for display in reports
"""

from typing import Dict, Tuple, Optional


def collect_http_headers(url: str, timeout: int = 10, user_agent: str = None, proxy: Dict[str, str] = None) -> Tuple[Optional[Dict[str, str]], Optional[str]]:
    """
    Collect HTTP headers from a URL using HTTP client
    
    Args:
        url: Target URL
        timeout: Request timeout in seconds
        user_agent: Custom user agent string
        proxy: Proxy configuration dict
        
    Returns:
        Tuple of (headers_dict, error_message)
    """
    import urllib.request
    import urllib.error
    import ssl
    from urllib.parse import urlparse
    
    try:
        # Create request with custom headers
        request = urllib.request.Request(url)
        
        # Set user agent
        if user_agent:
            request.add_header('User-Agent', user_agent)
        else:
            request.add_header('User-Agent', 'EyeWitness Security Scanner')
        
        # Accept common content types
        request.add_header('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        request.add_header('Accept-Language', 'en-US,en;q=0.5')
        request.add_header('Accept-Encoding', 'gzip, deflate')
        request.add_header('Connection', 'keep-alive')
        
        # Create SSL context that allows self-signed certificates
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Set up proxy if provided
        opener = None
        if proxy and proxy.get('ip') and proxy.get('port'):
            proxy_handler = urllib.request.ProxyHandler({
                'http': f"http://{proxy['ip']}:{proxy['port']}",
                'https': f"https://{proxy['ip']}:{proxy['port']}"
            })
            opener = urllib.request.build_opener(proxy_handler, urllib.request.HTTPSHandler(context=ssl_context))
        else:
            opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=ssl_context))
        
        # Make request with timeout
        response = opener.open(request, timeout=timeout)
        
        # Extract headers from response
        headers = {}
        for header_name, header_value in response.headers.items():
            headers[header_name] = header_value
        
        response.close()
        return headers, None
        
    except urllib.error.HTTPError as e:
        # Still try to get headers from error response
        if e.headers:
            headers = {}
            for header_name, header_value in e.headers.items():
                headers[header_name] = header_value
            return headers, f"HTTP {e.code} {e.reason}"
        return None, f"HTTP Error {e.code}: {e.reason}"
        
    except urllib.error.URLError as e:
        return None, f"URL Error: {str(e.reason)}"
        
    except ssl.SSLError as e:
        return None, f"SSL Error: {str(e)}"
        
    except Exception as e:
        return None, f"Request Error: {str(e)}"


if __name__ == "__main__":
    # Test the security header analyzer
    analyzer = SecurityHeaderAnalyzer()
    
    # Test with sample headers
    test_headers = {
        'Server': 'Apache/2.4.41',
        'X-Powered-By': 'PHP/7.4.3',
        'Content-Type': 'text/html; charset=UTF-8',
        'X-Frame-Options': 'SAMEORIGIN',
        'Content-Security-Policy': 'default-src \'self\' \'unsafe-inline\''
    }
    
    results = analyzer.analyze_headers(test_headers, 'https://example.com')
    print("Security Header Analysis Results:")
    print(f"Security Score: {results['security_score']}/100")
    print(f"Missing Headers: {len(results['missing_headers'])}")
    print(f"Present Headers: {len(results['present_headers'])}")
    print(f"Info Disclosure: {len(results['info_disclosure'])}")