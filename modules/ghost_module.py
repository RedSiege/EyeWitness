import ghost
import urllib2
import re

title_regex = re.compile("<title(.*)>(.*)</title>", re.IGNORECASE + re.DOTALL)


def create_driver(cli_parsed, ua=None):
    user_agent = None
    viewport_size = (1200, 675)
    if cli_parsed.user_agent is not None:
        user_agent = cli_parsed.user_agent

    if ua is not None:
        user_agent = ua

    if user_agent is not None:
        driver = ghost.Ghost(wait_timeout=cli_parsed.t,
                             user_agent=user_agent,
                             ignore_ssl_errors=True,
                             viewport_size=viewport_size)
    else:
        driver = ghost.Ghost(wait_timeout=cli_parsed.t,
                             ignore_ssl_errors=True,
                             viewport_size=viewport_size)
    return driver


def capture_host(cli_parsed, http_object, driver, ua=None):
    global title_regex
    ghost_page, ghost_extra_reousrces = driver.open(
        http_object.remote_system,
        auth=('none', 'none'), default_popup_response=True)

    driver.capture_to(http_object.screenshot_path)
    http_object.headers = ghost_page.headers

    if ghost_page.content == 'None':
        try:
            response = urllib2.urlopen(http_object.remote_system)
            source = response.read()
            http_object.source_code = source
            response.close()
        except urllib2.HTTPError:
            http_object.source_code = ("Sorry, but I couldn't get source code for\
            potentially a couple reasons. If it was Basic Auth, a 50X, or a \
            40X error, EyeWitness won't return source code. Couldn't get\
            source from {0}.").format(http_object.remote_system)
        except urllib2.URLError:
            http_object.source_code = ("Could not resolve the following domain\
                : {0}").format(http_object.remote_system)
        except:
            http_object.source_code = ("Unknown error, server responded with\
                an unknown error code when connecting to {0}").format(
                http_object.remote_system)
    else:
        http_object.source_code = ghost_page.content

    with open(http_object.source_path, 'w') as f:
        f.write(http_object.source_code)

    with open(http_object.source_path) as f:
        src = f.read()
        tag = title_regex.search(src.encode('utf-8'))
        if tag is not None:
            http_object.page_title = tag.group(2).strip()
        else:
            http_object.page_title = 'Unknown'

    return http_object, driver
