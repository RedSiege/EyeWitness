import http.client
import os
import socket
import sys
import time
import traceback
import urllib.request
import urllib.error
from urllib.parse import urlparse
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import requests
import ssl
import json

try:
    from ssl import CertificateError as sslerr
except:
    from ssl import SSLError as sslerr

try:
    # from seleniumwire import webdriver
    from selenium import webdriver
    from selenium.webdriver.firefox.options import Options
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.by import By
    from selenium.common.exceptions import NoAlertPresentException
    from selenium.common.exceptions import TimeoutException
    from selenium.common.exceptions import UnexpectedAlertPresentException
    from selenium.common.exceptions import WebDriverException
    from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
except ImportError:
    print('[*] Selenium not found.')
    print('[*] Please run the script in the setup directory!')
    sys.exit()

from modules.helpers import do_delay

def create_driver(cli_parsed, user_agent=None):
    """Creates a selenium FirefoxDriver

    Args:
        cli_parsed (ArgumentParser): Command Line Object
        user_agent (String, optional): Optional user-agent string

    Returns:
        FirefoxDriver: Selenium Firefox Webdriver
    """
    profile = webdriver.FirefoxProfile()
    # Load our custom firefox addon to handle basic auth.
    extension_path = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        '..', 'bin', 'dismissauth.xpi')
    profile.add_extension(extension_path)
    profile.accept_untrusted_certs = True

    # This user agent case covers a user provided one
    if cli_parsed.user_agent is not None:
        profile.set_preference(
            'general.useragent.override', cli_parsed.user_agent)

    # This user agent case should only be hit when cycling
    if user_agent is not None:
        profile.set_preference('general.useragent.override', user_agent)

    # Set up our proxy information directly in the firefox profile
    if cli_parsed.proxy_ip is not None and cli_parsed.proxy_port is not None:
        profile.set_preference('network.proxy.type', 1)
        if "socks" in cli_parsed.proxy_type:
            profile.set_preference('network.proxy.socks', cli_parsed.proxy_ip)
            profile.set_preference('network.proxy.socks_port', cli_parsed.proxy_port)
        else:
            profile.set_preference('network.proxy.http', cli_parsed.proxy_ip)
            profile.set_preference(
                'network.proxy.http_port', cli_parsed.proxy_port)
            profile.set_preference('network.proxy.ssl', cli_parsed.proxy_ip)
            profile.set_preference('network.proxy.ssl_port', cli_parsed.proxy_port)

    profile.set_preference('app.update.enabled', False)
    profile.set_preference('browser.search.update', False)
    profile.set_preference('extensions.update.enabled', False)

    try:
        capabilities = DesiredCapabilities.FIREFOX.copy()
        capabilities.update({'acceptInsecureCerts': True})
        options = Options()
        options.add_argument("--headless")
        profile.update_preferences()
        driver = webdriver.Firefox(profile, capabilities=capabilities, options=options, service_log_path=cli_parsed.selenium_log_path)
        driver.set_page_load_timeout(cli_parsed.timeout)
        return driver
    except Exception as e:
        if 'Failed to find firefox binary' in str(e):
            print('Firefox not found!')
            print('You can fix this by installing Firefox/Iceweasel\
             or using phantomjs/ghost')
        else:
            print(e)
        sys.exit()

def _has_failure_contents(contents):

    if '500 Internal Server Error' in contents: return True
    elif '401 Unauthorized' in contents: return True

    return False

def _auth_log(cred, cli_parsed, http_object, driver, method='form'):
    """Writes a detected host with a valid default credential to disk

    Args:
        cred (Tuple): Consists of username, password, comment, and status result once tested (bool)
        cli_parsed (ArgumentParser): Command Line Object
        http_object (HTTPTableObject): Object containing data relating to current URL
        driver (FirefoxDriver): webdriver instance
        ua (String, optional): Optional user agent string

    Returns:
        Boolean: True for success, False for failure
    """

    print("\x1b[32m[!] AUTH LOG: Potential authentication success: {0} username: {1} password: {2} method: {3}\x1b[0m".format(http_object.remote_system, cred[0], cred[1], method)) 
    if not cli_parsed.validation_output:
        return

    with open(cli_parsed.validation_output, "a+") as f:
        print("AUTH LOG: Potential authentication success: {0} username: {1} password: {2} method: {3}".format(http_object.remote_system, cred[0], cred[1], method), file=f) 
        f.close()
        
        

def _auth_host_uri(cred, cli_parsed, http_object, driver, ua=None):
    """Performs the internal authentication with single given credential

    Args:
        cred (Tuple): Consists of username, password, comment, and status result once tested (bool)
        cli_parsed (ArgumentParser): Command Line Object
        http_object (HTTPTableObject): Object containing data relating to current URL
        driver (FirefoxDriver): webdriver instance
        ua (String, optional): Optional user agent string

    Returns:
        Boolean: String (filename of screenshot) for success, and False for failure
    """

    # first attempt for each cred, attempt cred call ie: https://username:password@hostname:port/
    # if result is unauthorized or a form is found with a password input (assuming failure)

    p = urlparse(http_object.remote_system)
    if cred[0] and cred[1]:
        auth_url = p.scheme + "://" + cred[0] + ":" + cred[1] + "@" + p.netloc + p.path
    elif cred[0]:
        auth_url = p.scheme + "://" + cred[0] + ":@" + p.netloc + p.path
    else:
        print("[*] No credentials found, skipping...")
        # print(cred)
        # auth_url = p.scheme + "://" + p.netloc + p.path
        return False
    print("[*] Attempting authentication via url: ", auth_url)

    # Attempt to take the screenshot
    try:
        # If cookie is presented we need to avoid cookie-averse error. To do so, we need to get the page twice.
        driver.get(auth_url)

        # if a text input and a password input are shown, print content, and assume login failed
        screenshots = False

        # print(driver.page_source) debugging
        if _has_failure_contents(driver.page_source): return False

        try:
            elem = driver.find_element('xpath', "//input[@type='password']")
        except WebDriverException as e:
            print("[!] AUTH SUCCESS: No password element found, potential auth success: {0}".format(http_object.remote_system)) 
            _auth_log(cred, cli_parsed, http_object, driver, 'uri')
            # Save our screenshot to the specified directory
            try:
                time.sleep(5) # wait for page to load
                filename = http_object.screenshot_path[:-4] + ".auth.1.png"
                i = 0
                while os.path.exists(filename):
                    filename = http_object.screenshot_path[:-4] + ".auth.1_%d.png" % i
                    i += 1

                print("[!] Saving screenshot to: ", filename)
                driver.save_screenshot(filename)
                if not screenshots: screenshots = filename
                else: screenshots += ';' + filename
            except WebDriverException as e:
                print('[*] Error saving web page screenshot'
                      ' for ' + http_object.remote_system)

        # get contents and inspect
        if cli_parsed.cookies is not None:
            for cookie in cli_parsed.cookies:
                driver.add_cookie(cookie)

            driver.get(auth_url)

            # get contents and inspect again
            try:
                elem = driver.find_element('xpath', "//input[@type='password']")
            except WebDriverException as e:
                print("[!] AUTH SUCCESS: No password element found, potential auth success: {0}".format(http_object.remote_system)) 
                _auth_log(cred, cli_parsed, http_object, driver, 'uri')
                # Save our screenshot to the specified directory
                try:
                  time.sleep(5) # wait for page to load
                  filename = http_object.screenshot_path[:-4] + ".auth.2.png"
                  print("[!] Saving screenshot to: ", filename)
                  i = 0
                  while os.path.exists(filename):
                    filename = http_object.screenshot_path[:-4] + ".auth.2_%d.png" % i
                    i += 1
                  driver.save_screenshot(filename)
                  if not screenshots: screenshots = filename
                  else: screenshots += ';' + filename
                except WebDriverException as e:
                    print('[*] Error saving web page screenshot'
                          ' for ' + http_object.remote_system)
                return screenshots

            return False

    except KeyboardInterrupt:
        print('[*] Skipping: {0}'.format(http_object.remote_system))
        http_object.error_state = 'Skipped'
        http_object.page_title = 'Page Skipped by User'
    except TimeoutException:
        print('[*] Hit timeout limit when connecting to {0}, retrying'.format(http_object.remote_system))
    except http.client.BadStatusLine:
        print('[*] Bad status line when connecting to {0}'.format(http_object.remote_system))
    except WebDriverException as e:
        print('[*] WebDriverError when connecting to {0}'.format(http_object.remote_system))
        # print('[*] WebDriverError when connecting to {0} -> {1}'.format(http_object.remote_system, e))
    except Exception as e:
        print("[*] URI login failure: ", e)
        print(traceback.format_exc())

    # Dismiss any alerts present on the page
    # Will not work for basic auth dialogs!
    try:
        alert = driver.switch_to.alert
        alert.dismiss()
    except Exception as e:
        pass

    return False

def _auth_host_form(cred, cli_parsed, http_object, driver, ua=None):
    """Performs the internal authentication with single given credential

    Args:
        cred (Tuple): Consists of username, password, comment, and status result once tested (bool)
        cli_parsed (ArgumentParser): Command Line Object
        http_object (HTTPTableObject): Object containing data relating to current URL
        driver (FirefoxDriver): webdriver instance
        ua (String, optional): Optional user agent string

    Returns:
        Boolean: String (filename of screenshot) for success, and False for failure
        Driver: Needed since this functions closes connections and retries
    """

    # form is found, leverage selenium

    # selenium: for each form: 
    #     find forms that contain password input type. 
    #     form: provide each user/password and confirm non 400 return

    print("[!] Attempting form validation...")
    driver2 = None
    try:
        success=False

        # If cookie is presented we need to avoid cookie-averse error. To do so, we need to get the page twice. ???

        driver2 = create_driver(cli_parsed, ua)
        driver2.get(http_object.remote_system)
        if cli_parsed.cookies is not None:
            for cookie in cli_parsed.cookies:
                driver2.add_cookie(cookie)
            driver2.get(http_object.remote_system)

        # get contents and inspect again
        # for each form that contains an input
        try:
            forms = driver2.find_elements('xpath', "//form")
        except WebDriverException as e:
            print('[*] WebDriverError when connecting to {0} -> {1}'.format(http_object.remote_system, e))
            print('[*] No forms have been found! Exiting.')
            driver2.quit()
            return False

        # print("FORMS: ", forms)
        print("[!] %d forms found..." % len(forms))
        screenshots = False
        i = 0
        for form in forms:
          # for each radio button, for each radio button option
            
          # get contents and inspect again
          # for each form that contains an input
          radios = [ ]
          try:
              radios = form.find_elements('xpath', "//input[@type='radio']")
          except WebDriverException:
              pass

          if len(radios) > 0:
            # print("[*] Testing additional radio input found in form (radio #%d)" % radioOffset)
            # radios[radioOffset].click()
            # radioOffset += 1
            for radio in radios:
                i = i + 1
                radio.click()
                # submit

                i = i + 1
                try:
                  pass_elem = form.find_element('xpath', "//input[@type='password']")
                  if pass_elem:
                    pass_elem.send_keys(cred[1])
                except WebDriverException:
                  print("[*] No password input found in form, skipping form...")
                  continue
  
                try:
                  user_elem = form.find_element('xpath', "//input[@type='input']")
                  user_elem.send_keys(cred[0])
                except WebDriverException:
                  print('[*] No username element found, attempting to send password only.')
  
                try:
                  form.find_element('xpath', "//input[@type='submit']").click()
                except WebDriverException:
                  print('[*] No submit input element found, attempting to give up.')
                  try:
                    form.submit()
                  except Exception as e:
                    print('[!] Unable to submit form: ', e)

                try:
                  elem = driver2.find_element('xpath', "//input[@type='password']")
                  print('[*] Authentication failure.')
                except WebDriverException:
                  print("[!] AUTH SUCCESS(2): No password element found, potential auth success!")
                  _auth_log(cred, cli_parsed, http_object, driver)
                  success=True
                  # Save our screenshot to the specified directory
                  try:
                      time.sleep(5) # wait for page to load
                      filename = http_object.screenshot_path[:-4] + ".auth.3_%d.png" % i
                      print("[!] Saving screenshot to: ", filename)
                      k = 0
                      while os.path.exists(filename):
                          filename = http_object.screenshot_path[:-4] + ".auth.3_%d_%d.png" % (i, k)
                          k += 1
                      driver2.save_screenshot(filename)
                      if not screenshots: screenshots = filename
                      else: screenshots += ';' + filename
                  except WebDriverException as e:
                      print('[*] Error saving web page screenshot'
                            ' for ' + http_object.remote_system)
  
                # Dismiss any alerts present on the page
                # Will not work for basic auth dialogs!
                try:
                    alert = driver2.switch_to.alert
                    alert.dismiss()
                except Exception as e:
                    pass
  
                driver2.back()

          else:

            i = i + 1
            try:
              pass_elem = form.find_element('xpath', "//input[@type='password']")
              if pass_elem and cred[1]:
                pass_elem.send_keys(cred[1])
              elif pass_elem: 
                pass_elem.send_keys("")
            except WebDriverException:
              print("[*] No password input found in form, skipping form...")
              continue
            except Exception as e:
              print("[*] Failed to send password input, skipping form...")
              continue
  
            try:
              user_elem = form.find_element('xpath', "//input[@type='input']")
              user_elem.send_keys(cred[0])
            except WebDriverException:
              print('[*] No username element found, attempting to send password only.')
  
            try:
              form.find_element('xpath', "//input[@type='submit']").click()
            except WebDriverException:
              print('[*] No submit input element found, attempting to give up.')
              try:
                form.submit()
              except Exception as e:
                print('[!] Unable to submit form: ', e)
  
            try:
              elem = driver2.find_element('xpath', "//input[@type='password']")
              print('[*] Authentication failure.')
            except WebDriverException:
              print("[!] AUTH SUCCESS(2): No password element found, potential auth success!")
              _auth_log(cred, cli_parsed, http_object, driver)
              success=True
              # Save our screenshot to the specified directory
              try:
                  time.sleep(5) # wait for page to load
                  filename = http_object.screenshot_path[:-4] + ".auth.3_%d.png" % i
                  print("[!] Saving screenshot to: ", filename)
                  k = 0
                  while os.path.exists(filename):
                      filename = http_object.screenshot_path[:-4] + ".auth.3_%d_%d.png" % (i, k)
                      k += 1
                  driver2.save_screenshot(filename)
                  if not screenshots: screenshots = filename
                  else: screenshots += ';' + filename
              except WebDriverException as e:
                  print('[*] Error saving web page screenshot'
                        ' for ' + http_object.remote_system)
  
            # Dismiss any alerts present on the page
            # Will not work for basic auth dialogs!
            try:
                alert = driver2.switch_to.alert
                alert.dismiss()
            except Exception as e:
                pass
  
            driver2.back()
  

        driver2.quit()

        return screenshots
    except KeyboardInterrupt:
        print('[*] Skipping: {0}'.format(http_object.remote_system))
        http_object.error_state = 'Skipped'
        http_object.page_title = 'Page Skipped by User'
    except TimeoutException:
        print('[*] Hit timeout limit when connecting to {0}, retrying'.format(http_object.remote_system))
    except http.client.BadStatusLine:
        print('[*] Bad status line when connecting to {0}'.format(http_object.remote_system))
    except WebDriverException:
        print('[*] WebDriverError when connecting to {0}'.format(http_object.remote_system))
        # print('[*] WebDriverError when connecting to {0} -> {1}'.format(http_object.remote_system, e))
    except Exception as e:
        print("[*] Form login failure: ", e)
        print(traceback.format_exc())

    if driver2: driver2.quit()

    return False

def _auth_host(cred, cli_parsed, http_object, driver, is_protected, ua=None):
    """Performs the internal authentication with single given credential

    Args:
        cred (Tuple): Consists of username, password, comment, and status result once tested (bool)
        cli_parsed (ArgumentParser): Command Line Object
        http_object (HTTPTableObject): Object containing data relating to current URL
        driver (FirefoxDriver): webdriver instance
        ua (String, optional): Optional user agent string

    Returns:
        Boolean: String (filename of screenshot) for success, and False for failure
    """

    # first attempt for each cred, attempt cred call ie: https://username:password@hostname:port/
    # if result is unauthorized or a form is found with a password input (assuming failure), try next request
    # else if form is found, leverage selenium

    # selenium: for each form: 
    #     find forms that contain password input type. 
    #     form: provide each user/password and confirm non 400 return

    if is_protected:
        return _auth_host_uri(cred, cli_parsed, http_object, driver, ua)

    return _auth_host_form(cred, cli_parsed, http_object, driver, ua)


def auth_host(cli_parsed, http_object, driver, is_protected, ua=None):
    """Attempts to authenticate to a single host, given
    the data available in http_object._parsed_creds

    Args:
        cli_parsed (ArgumentParser): Command Line Object
        http_object (HTTPTableObject): Object containing data relating to current URL
        driver (FirefoxDriver): webdriver instance
        ua (String, optional): Optional user agent string

    Returns:
        HTTPTableObject: Complete http_object
    """


    if len(http_object._parsed_creds) == 0:
      # print("[!] Failed to test authentication, no credentials have been found: ", http_object.default_creds)
      return http_object

    for idx in range(len(http_object._parsed_creds)):
      c = http_object._parsed_creds[idx]
      s = ""
      if c[0] and c[1]:
        s += "User: %s Password: %s" % (c[0], c[1])
      elif c[0]:
        s += "User: %s Password: empty" % c[0]
      if c[2]:
        s += " Comment: %s" % c[2]
      s += "\n"

      screenshots = _auth_host(c, cli_parsed, http_object, driver, is_protected, ua)
      if screenshots != False:
        # print("[*] Authentication Success! Credentials:\n%s" % s.strip("\n"))
        c = list(c)
        c[3] = True
        # XXX
        c[4] = screenshots
        http_object._parsed_creds[idx] = tuple(c)

    return http_object

def test_realm(cli_parsed, http_object, driver, ua=None):
    """Capture HTTP HEAD request and look for Server and WWW-Authenticate headers
    Args:
        cli_parsed (ArgumentParser): Command Line Object
        http_object (HTTPTableObject): Object containing data relating to current URL
        driver (FirefoxDriver): webdriver instance
        ua (String, optional): Optional user agent string

    Returns:
        HTTPTableObject: Complete http_object
        Boolean: if site is protected by a realm
    """

    status = None
    is_protected = False

    try:
        response = requests.head(http_object.remote_system, timeout=cli_parsed.timeout, verify=False)
        # print("[*] Status Code: ", response.status_code, " Headers : ", json.dumps(dict(response.headers)))
        if response.status_code >= 400 and response.status_code < 500:
            # Realm detected? 
            auth_header = server_response = None
            if 'Server' in response.headers:
                server_response = response.headers['Server']
                if len(server_response.strip()) == 0: server_response = None
            if 'WWW-Authenticate' in response.headers:
                auth_header = response.headers['WWW-Authenticate']
                if len(auth_header.strip()) == 0: auth_header = None
            else:
               response.close()
               return status, is_protected # no authentication prompt

            # parse
            if auth_header: 
                is_protected = True
                print("Header detected: ", auth_header)
            if server_response: print("Server detected: ", server_response)

            # parse out our signature data and attempt to match. for each match: attempt defalut creds. if success, use creds and take screenshot

            http_object.default_creds = None
            http_object.category = None
            sigpath = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               '..', 'signatures_realm.txt')
            with open(sigpath) as sig_file:
                signatures = sig_file.readlines()

            for sig in signatures:
                # Find the signature(s), split them into their own list if needed
                # Assign default creds to its own variable
                # !! added support for description field and cred field, so that creds can be
                # !! automatically checked
                sig = sig.rstrip("\n")
                sig_cred = sig.split('|')
                if len(sig_cred) > 4:
                  # character '|' is contained in the page_sig, rejoin and work backwards
                  tmp_sig = sig_cred[0:len(sig_cred)-3]
                  sig = "|".join(tmp_sig)
                  sig_cred2 = [ sig, sig_cred[len(sig_cred) - 3], sig_cred[len(sig_cred) - 2] ]
                  sig_cred = sig_cred2

                server_sig = sig_cred[0].strip()
                realm_sig = sig_cred[1].strip()
                desc = sig_cred[2].strip()
                try:
                  cred_info = sig_cred[3]
                except Exception as e:
                  # default to description, assume description is missing
                  cred_info = desc

                # if all([x.lower() in server_response.lower() for x in page_sig]) and :
                if server_sig and realm_sig and server_response and auth_header and server_sig.lower() in server_response.lower() and auth_header.lower() in realm_sig.lower():
                    print("[*] Matched Server Response and Authentication Header, attempting default credentials")
                    http_object._description = desc
                    if http_object.default_creds is None:
                        http_object.default_creds = cred_info
                    else:
                        http_object.default_creds += ';' + cred_info
                    status = http_object
                elif server_sig and server_response and server_sig.lower() in server_response.lower():
                    print("[*] Matched Server Response, attempting default credentials")
                    http_object._description = desc
                    if http_object.default_creds is None:
                        http_object.default_creds = cred_info
                    else:
                        http_object.default_creds += ';' + cred_info
                    status = http_object
                elif realm_sig and auth_header and auth_header.lower() in realm_sig.lower():
                    print("[*] Matched Authentication Header, attempting default credentials")
                    http_object._description = desc
                    if http_object.default_creds is None:
                        http_object.default_creds = cred_info
                    else:
                        http_object.default_creds += ';' + cred_info
                    status = http_object

        response.close()

    except Exception as e:
        print('[*] Error ({0}), Skipping: {1}'.format(e, http_object.remote_system))
        http_object.error_state = 'Skipped'

    # take screenshot! 

    return status, is_protected

def capture_host(cli_parsed, http_object, driver, ua=None):
    """Screenshots a single host, saves information, and returns
    a complete HTTP Object

    Args:
        cli_parsed (ArgumentParser): Command Line Object
        http_object (HTTPTableObject): Object containing data relating to current URL
        driver (FirefoxDriver): webdriver instance
        ua (String, optional): Optional user agent string

    Returns:
        HTTPTableObject: Complete http_object
    """

    # Attempt to take the screenshot
    try:
        # If cookie is presented we need to avoid cookie-averse error. To do so, we need to get the page twice.
        driver.get(http_object.remote_system)
        if cli_parsed.cookies is not None:
            for cookie in cli_parsed.cookies:
                driver.add_cookie(cookie)
            driver.get(http_object.remote_system)
    except KeyboardInterrupt:
        print('[*] Skipping: {0}'.format(http_object.remote_system))
        http_object.error_state = 'Skipped'
        http_object.page_title = 'Page Skipped by User'
    except TimeoutException:
        print('[*] Hit timeout limit when connecting to {0}, retrying'.format(http_object.remote_system))
        driver.quit()
        driver = create_driver(cli_parsed, ua)
        http_object.error_state = 'Timeout'
    except http.client.BadStatusLine:
        print('[*] Bad status line when connecting to {0}'.format(http_object.remote_system))
        http_object.error_state = 'BadStatus'
        return http_object, driver
    except WebDriverException as e:
        # print('[*] WebDriverError when connecting to {0} -> {1}'.format(http_object.remote_system, e))
        print('[*] WebDriverError when connecting to {0}'.format(http_object.remote_system))
        http_object.error_state = 'BadStatus'
        return http_object, driver

    # Dismiss any alerts present on the page
    # Will not work for basic auth dialogs!
    try:
        alert = driver.switch_to.alert
        alert.dismiss()
    except Exception as e:
        pass

    # If we hit a timeout earlier, retry once
    if http_object.error_state == 'Timeout':
        retry_counter = 0
        return_status = False
        while retry_counter < cli_parsed.max_retries:
            http_object.error_state = None
            try:
                driver.get(http_object.remote_system)
                if cli_parsed.cookies is not None:
                    for cookie in cli_parsed.cookies:
                        driver.add_cookie(cookie)
                    driver.get(http_object.remote_system)
                break
            except TimeoutException:
                # Another timeout results in an error state and a return
                print('[*] Hit timeout limit when connecting to {0}'.format(http_object.remote_system))
                http_object.error_state = 'Timeout'
                http_object.page_title = 'Timeout Limit Reached'
                http_object.headers = {}
                driver.quit()
                driver = create_driver(cli_parsed, ua)
                return_status = True
            except KeyboardInterrupt:
                print('[*] Skipping: {0}'.format(http_object.remote_system))
                http_object.error_state = 'Skipped'
                http_object.page_title = 'Page Skipped by User'
                break
            except http.client.BadStatusLine:
                print('[*] Bad status line when connecting to {0}'.format(http_object.remote_system))
                http_object.error_state = 'BadStatus'
                return_status = True
                break
            except WebDriverException:
                print('[*] WebDriverError when connecting to {0}'.format(http_object.remote_system))
                http_object.error_state = 'BadStatus'
                return_status = True
                break
            retry_counter += 1

        # Determine if I need to return the objects
        if return_status:
            return http_object, driver

        try:
            alert = driver.switch_to.alert
            alert.dismiss()
        except Exception as e:
            pass

    do_delay(cli_parsed)

    # Save our screenshot to the specified directory
    try:
        time.sleep(5) # wait for page to load
        driver.save_screenshot(http_object.screenshot_path)
    except WebDriverException as e:
        print('[*] Error saving web page screenshot'
              ' for ' + http_object.remote_system)

    # Get our headers using urllib
    context = None
    try:
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
    except:
        context = None
        pass

    if cli_parsed.user_agent:
        tempua = cli_parsed.user_agent
    else:
        try:
            tempua = driver.execute_script("return navigator.userAgent")
        except:
            tempua = ''
    try:
        req = urllib.request.Request(http_object.remote_system, headers={'User-Agent': tempua})
        if cli_parsed.proxy_ip is not None:
            req.set_proxy(str(cli_parsed.proxy_ip) + ':' + str(cli_parsed.proxy_port), 'http')
            req.set_proxy(str(cli_parsed.proxy_ip) + ':' + str(cli_parsed.proxy_port), 'https')
        if context is None:
            opened = urllib.request.urlopen(req)
        else:
            opened = urllib.request.urlopen(req, context=context)
        headers = dict(opened.info())
        headers['Response Code'] = str(opened.getcode())
    except urllib.error.HTTPError as e:
        responsecode = e.code
        if responsecode == 404:
            http_object.category = 'notfound'
        elif responsecode == 403 or responsecode == 401:
            http_object.category = 'unauth'
        elif responsecode == 500:
            http_object.category = 'inerror'
        elif responsecode == 400:
            http_object.category = 'badreq'
        headers = dict(e.headers)
        headers['Response Code'] = str(e.code)
    except urllib.error.URLError as e:
        if '104' in str(e.reason):
            headers = {'Error': 'Connection Reset'}
            http_object.error_state = 'ConnReset'
            return http_object, driver
        elif '111' in str(e.reason):
            headers = {'Error': 'Connection Refused'}
            http_object.error_state = 'ConnRefuse'
            return http_object, driver
        elif 'Errno 1' in str(e.reason) and 'SSL23' in str(e.reason):
            headers = {'Error': 'SSL Handshake Error'}
            http_object.error_state = 'SSLHandshake'
            return http_object, driver
        elif 'Errno 8' in str(e.reason) and 'EOF occurred' in str(e.reason):
            headers = {'Error': 'SSL Handshake Error'}
            http_object.error_state = 'SSLHandshake'
            return http_object, driver
        else:
            headers = {'Error': 'HTTP Error...'}
            http_object.error_state = 'BadStatus'
            return http_object, driver
    except socket.error as e:
        if e.errno == 104:
            headers = {'Error': 'Connection Reset'}
            http_object.error_state = 'ConnReset'
            return http_object, driver
        elif e.errno == 10054:
            headers = {'Error': 'Connection Reset'}
            http_object.error_state = 'ConnReset'
            return http_object, driver
        else:
            http_object.error_state = 'BadStatus'
            return http_object, driver
    except http.client.BadStatusLine:
        http_object.error_state = 'BadStatus'
        return http_object, driver
    except sslerr:
        headers = {'Error': 'Invalid SSL Certificate'}
        http_object.ssl_error = True

    try:
        http_object.page_title = 'Unknown' if driver.title == '' else driver.title.encode(
            'utf-8')
    except Exception:
        http_object.page_title = 'Unable to Display'
    # Save page source to the object and to a file. Also set the title in the object
    try:
        http_object.headers = headers
        http_object.source_code = driver.page_source.encode('utf-8')
        with open(http_object.source_path, 'w') as f:
            f.write(http_object.source_code.decode())
    except UnexpectedAlertPresentException:
        with open(http_object.source_path, 'w') as f:
            f.write('Cannot render webpage')
        http_object.headers = {'Cannot Render Web Page': 'n/a'}
    except IOError:
        print("[*] ERROR: URL too long, surpasses max file length.")
        print("[*] ERROR: Skipping: " + http_object.remote_system)
    except WebDriverException:
        print("[*] ERROR: Skipping source code capture for: " + http_object.remote_system)

    return http_object, driver
