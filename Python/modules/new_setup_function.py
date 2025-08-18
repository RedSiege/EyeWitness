def setup_virtual_display(platform_mgr: PlatformManager, show_selenium: bool = False):
    """Setup virtual display with proper cross-platform and Docker handling"""
    if not platform_mgr.needs_virtual_display() or show_selenium:
        return None
    
    # Docker-specific handling: If we're in Docker and DISPLAY is already set,
    # assume Xvfb is already running from the entrypoint script
    if platform_mgr.is_docker:
        display_env = os.environ.get('DISPLAY')
        if display_env:
            print(f'[*] Docker environment detected with DISPLAY={display_env}')
            print('[*] Using existing virtual display from Docker entrypoint')
            return None  # Don't start our own display
        else:
            print('[*] Docker environment detected but no DISPLAY set')
            print('[*] Will attempt to start virtual display')
    
    if not platform_mgr.can_use_virtual_display():
        if platform_mgr.is_windows:
            # Windows doesn't need virtual display
            return None
        else:
            print('[*] Warning: Virtual display needed but not available')
            print('[*] Install with: sudo apt-get install xvfb (Debian/Ubuntu)')
            print('[*] Or run with --show-selenium flag')
            return None
    
    try:
        from pyvirtualdisplay import Display
        # In Docker, if we get here, try to use a different display number
        # to avoid conflicts with existing Xvfb
        display_num = ':1' if platform_mgr.is_docker else ':0'
        display = Display(visible=0, size=(1920, 1080), display=display_num)
        display.start()
        print(f'[*] Started virtual display on {display_num}')
        return display
    except ImportError:
        print('[*] Warning: pyvirtualdisplay package not found')
        print('[*] Install with: pip install pyvirtualdisplay')
        return None
    except Exception as e:
        print(f'[*] Warning: Could not start virtual display: {e}')
        if platform_mgr.is_docker:
            print('[*] Docker: Assuming existing Xvfb is available')
        print('[*] Continuing in headless mode...')
        return None
EOF < /dev/null
