import base64
import os
import urllib2
import urllib
import cookielib
import re
from random import choice
import socket
from bs4 import BeautifulSoup

# Used to get cookies and set user agents in all requests
user_agents = [
    'Mozilla/5.0 (Windows; U; Windows NT 5.1; it; rv:1.8.1.11) Gecko/20071127 Firefox/2.0.0.11',
    'Opera/9.25 (Windows NT 5.1; U; en)',
    'Mozilla/4.0 (compatible; MSIE 6.0; Windows NT 5.1; SV1; .NET CLR 1.1.4322; .NET CLR 2.0.50727)',
    'Mozilla/5.0 (compatible; Konqueror/3.5; Linux) KHTML/3.5.5 (like Gecko) (Kubuntu)',
    'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.8.0.12) Gecko/20070731 Ubuntu/dapper-security Firefox/1.5.0.12',
    'Lynx/2.8.5rel.1 libwww-FM/2.14 SSL-MM/1.4.1 GNUTLS/1.2.9',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/38.0.2125.111']

cookie_jar = cookielib.CookieJar()

opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookie_jar))
opener.addheaders = [('User-agent', choice(user_agents))]
urllib2.install_opener(opener)


# Need this to handle redirects for POST. So new URLs
class SmartRedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        result = urllib2.HTTPRedirectHandler.http_error_302(
            self, req, fp, code, msg, headers)
        result.status = code
        result.headers = headers
        return result
    http_error_301 = http_error_302


def parse_data_file(file_path):
    # this is where you will parse the data file for each category
    with open(file_path, 'r') as f:
        data_file = f.readlines()

    current_category = []

    for line in data_file:
        if line.startswith("Category"):
            category = {}
            category['category'] = re.findall(r"Category:\s(.*)", line)
        elif line.startswith("identifier"):
            identifier = re.findall(r"identifier:\s(.*)", line)
            category['identifier'] = identifier
        elif line.startswith("invalid_identifier"):
            identifier = re.findall(r"invalid_identifier:\s(.*)", line)
            category['invalid_identifier'] = identifier
        elif line.startswith("login_type"):
            identifier = re.findall(r"login_type:\s(.*)", line)
            category['login_type'] = identifier
        elif line.startswith("default creds"):
            default_creds = re.findall(r"default creds:\s(.*)", line)
            category['defaultCreds'] = default_creds
        elif line.startswith("default path"):
            default_path = re.findall(r"default path:\s(.*)", line)
            category['defaultPath'] = default_path

            current_category.append(category)
    return current_category


def parse_html(identifier, html_source):
    # This wil determine if the identifier is in the html of the target page
    # TODO: Consider logging the ones that were not identified
    identified = False
    if identifier[0].lower() in html_source.lower():
        identified = True
    return identified


def parse_url(url, protocol):
    # this will parse the URL to get the html data from the page
    # TODO: If this is HTTP, need to figure out if we handle it differently.
    # TODO: May need to add http(s) in front of it
    # depending on the check result
    # TODO: Handle exceptions so it doens't break
    # TODO: If it returns a 401 it will throw exception.
    # Need to handle that as basic auth
    html_source = ''
    if url.startswith('http') is False:
        url = protocol + '://' + url
    try:
        # consider a timeout for this because it takes awhile
        sock = urllib2.urlopen(url, timeout=3)
        html_source = sock.read()
        sock.close()
    except urllib2.URLError, e:
        raise Exception("There was an error: {}".format(e))
    except Exception, e:
        raise Exception("There was an error: {}".format(e))
    return html_source


def check_valid_url(url):
    error = False
    try:
        response = urllib2.urlopen(url, timeout=3)
    except urllib2.URLError, e:
        error = True
        if isinstance(e.reason, socket.timeout):
            print "error with {}".format(url)

    except socket.timeout, e:
        error = True
        print("There was an error with {}").format(url)
    except Exception, e:
        error = True
        print "{} issue with {}".format(url, e)

    if error:
        return e.getcode()
    return response.getcode()


def handle_category_match(data, http_object):
    # this is where you will login to the site
    # you ca call parse_url if you need to get the html of
    # the path to get for data
    # TODO: You only login to the path specific within data
    logintype = data['login_type']
    creds1 = data['defaultCreds']
    # This will get the login URL to the target
    orig_target = http_object.remote_system
    target = orig_target + data['defaultPath'][0]

    if logintype[0] == 'http_post':
        try:
            req = urllib2.Request(orig_target)
            opener = urllib2.build_opener(SmartRedirectHandler())
            rsp = opener.open(req)
            code = rsp.getcode()

            # print req.getcode()
            if code == 301 or code == 302:
                # get the html source so you can see if password
                #  is in the new url
                target = rsp.geturl()

        except urllib2.URLError, e:
            raise Exception("There was an error: {}".format(e))

        html_source = parse_url(orig_target, '')
        inputs = get_input_fields(html_source)
        if inputs[1] is not None:
            target = update_target(http_object.remote_system, inputs[1])
        inputs = inputs[0]

    for line in creds1:
        seperated = re.split(r',\s*', line)

    for cred in seperated:
        username, password = cred.split(':')

        # Check to see if authentication is form based or http_basic
        if logintype[0] == 'http_auth':
            check = http_auth(target, username, password)
            # Auth was successful, no need to continue
            if check:
                http_object.default_creds = "Default creds are valid: {}".format(cred)
                http_object.category = "successfulLogin"
                http_object._remote_login = target
                break
        elif logintype[0] == 'http_post':
            # login with form based auth
            if inputs is not None:
                post_data = get_post_data(inputs, username, password)
                # to be used for logging
                if login_post(orig_target, target, post_data, data):
                    print "\x1b[32m[+]Form Successful login against {} using {}\x1b[0m".format(target, cred)
                    http_object.default_creds = "Default creds are valid: {}".format(cred)
                    http_object.category = "successfulLogin"
                    http_object._remote_login = target
                    break
                else:
                    http_object.category = "identifiedLogin"

        else:
            print 'incorrect login type for {}'.format(data)
    return http_object


def check_login_form(html_data):
    try:
        soup = BeautifulSoup(html_data, "html.parser")
        login_form = False

        forms = soup.find_all('form')
        for form in forms:
            if form.find_all('input', {'type': 'password'}) != []:
                login_form = True
        return login_form
    except Exception:
        pass


def get_input_fields(html_data):
    # TODO: Consider getting new target if 301 or 302
    try:
        soup = BeautifulSoup(html_data, "html.parser")
        inputs = []
        action = None

        forms = soup.find_all('form')
        for form in forms:
            if form.find_all('input', {'type': 'password'}) != []:
                inputs = form.find_all('input')
                # Get form action and append it to the base URL
                # Not everything will have an action. Maybe log
                # that it's a login form, but couldn't attempt login
                action = form.get('action')

        return [inputs, action]
    except Exception as e:
        print e


def update_target(target, action):
    if "http://" in action or "https://" in action:
        target = action
    elif action.startswith('/') and target.endswith('/') is False:
        target = '{}{}'.format(target, action)
    elif target.endswith('/') and action.startswith('/') is False:
        target = '{}{}'.format(target, action)
    elif target.endswith('/') and action.startswith('/'):
        target = '{}{}'.format(target[:-1], action)
    else:
        target = '{}{}{}'.format(target, '/', action)
    return target


def get_post_data(inputs, uname, pword):
    post_data = {}
    try:
        if inputs != []:
            for y in inputs:
                if 'name' in str(y) or 'user' in str(y) or 'usr' in str(y):
                    if y['type'] == 'text' or y['type'] == 'email':
                        if 'name' in str(y):
                            post_data[y['name']] = uname
                        elif 'user' in str(y):
                            post_data[y['user']] = uname
                        elif 'usr' in str(y):
                            post_data[y['usr']] = uname
                    elif y['type'] == 'password':
                        post_data[y['name']] = pword
                    elif y['type'] == 'hidden':
                        if 'value' in str(y):
                            try:
                                post_data[y['name']] = y['value'].encode(
                                    'utf-8')
                            except:
                                pass
                        else:
                            post_data[y['name']] = ""
                    else:
                        if 'value' in str(y):
                            try:
                                post_data[y['name']] = y['value'].encode(
                                    'utf-8')
                            except:
                                pass
                        else:
                            post_data[y['name']] = ""
        return post_data

    except:
        pass


def login_post(url, target, post_data, data, still_trying=False):
    # This function will post the data that is passed to it after the post data
    # is populated
    fail_checks = [
        'fail', 'error', 'invalid', 'failed', 'incorrect',
        'try entering it again', 'bad user name', 'bad password',
        'name="password"']
    try:
        result = False
        # acquire cookie
        req = urllib2.Request(url)
        rsp = urllib2.urlopen(req, timeout=3)

        # do POST
        req = urllib2.Request(target, urllib.urlencode(post_data))
        rsp = urllib2.urlopen(req, timeout=3)
        content = rsp.read()

        if still_trying is False:
            if data['invalid_identifier'][0] != '401' and rsp.getcode() != 401 and data['invalid_identifier'][0] not in content:
                # success
                result = True
            elif data['invalid_identifier'][0] == '401' and rsp.getcode() != 401:
                # success
                result = True
            else:
                # failed
                result = False

        else:
            if any(x in content.lower() for x in fail_checks) or rsp.getcode() == 401:
                result = False
            else:
                result = True

    except urllib2.URLError, e:
        if isinstance(e.reason, socket.timeout):
            raise Exception("There was an error with {}".format(e))
    except socket.timeout, e:
        raise Exception("There was an error with {}".format(e))
    except Exception, e:
        raise Exception("There was an error: {}".format(e))

    return result


def http_auth(target, username, password):
    # This function will perform http basic authentication
    header = {}
    creds = '{}{}{}'.format(username, ':', password)

    success = False
    try:
        base64string = base64.encodestring(
            '%s:%s' % (username, password)).replace('\n', '')
        header["Authorization"] = "Basic {}".format(base64string)
        request = urllib2.Request(target, "", header)
        #added this because if data is in the request it will default to POST request
        request.get_method = lambda: "GET"
        urllib2.urlopen(request)
        success = True
        print "\x1b[32m[+]Http basic Successful login against {} using {}\x1b[0m".format(target, creds)
    except:
        success = False
    return success


def get_all_creds(file_path):
    data_file = open(file_path, 'r').readlines()
    passwords = []
    list_start = False

    for line in data_file:
        if list_start:
            if line == '\n' or line == '' or line == '\r\n':
                break
            else:
                passwords.append(line.rstrip())
        if line.startswith("### still trying"):
            list_start = True
    return passwords


def parse_urls(file_path):
    lines = open(file_path, 'r').readlines()
    urls = []
    list_start = False

    for line in lines:
        if list_start:
            if line == '\n' or line == '' or line == '\r\n':
                break
            else:
                urls.append(line.rstrip())
        if line.startswith("###URL"):
            list_start = True
    return urls


def find_logins(http_object, creds, urls):
    # append list of urls to see if there are urls associated with host
    # TODO: make new category for logins
    valid_urls200 = []
    valid_urls401 = []
    orig_target = http_object.remote_system
    result = False
    for url in urls:
        target = http_object.remote_system + url
        if check_valid_url(target) == 200:
            valid_urls200.append(target)
        elif check_valid_url(target) == 401:
            valid_urls401.append(target)
    # There is a basic auth
    if valid_urls401 != []:
        for cred in creds:
            http_auth(valid_urls401[0], cred[0], cred[1])
    # see if form authentication and if there is, then try to login
    if valid_urls200 != []:
        for valid_url in valid_urls200:
            target = valid_url
            if result is True:
                break
            source = parse_url(valid_url, '')
            if check_login_form(source):
                http_object._remote_login = target
                inputs = get_input_fields(source)
                if inputs[1] is not None:
                    target = update_target(orig_target, inputs[1])
                inputs = inputs[0]
                if inputs is not None:
                    for cred in creds:
                        temp_cred = cred.split(':')
                        post_data = get_post_data(
                            inputs, temp_cred[0], temp_cred[1])
                        # to be used for loggin
                        if login_post(target, target, post_data, "", True):
                            print "\x1b[32m[+]Form Successful login against {} using {}\x1b[0m".format(orig_target, ':'.join(temp_cred))
                            http_object.default_creds = "Default creds are valid: {}".format(temp_cred)
                            result = True
                            http_object.category = "successfulLogin"
                            http_object._remote_login = target
                            break
                        else:
                            http_object.category = "identifiedLogin"
    return http_object


def check_creds(http_object):
    identifier = False
    target = http_object.remote_system
    print "Attempting active scan against {}".format(target)

    try:
        data_file = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), '..', 'dataFile.txt')
        creds = get_all_creds(data_file)
        data = parse_data_file(data_file)
    except IOError:
        print("[*] WARNING: Credentials file not in the same directory"
              " as EyeWitness")
        print '[*] Skipping credential check'

    try:
        # Loop through and see if there are any matches from the source code
        # EyeWitness obtained
        if http_object.source_code is not None and '401 Unauthorized' not in http_object.page_title:
            for internal_data in data:
                # Check to see if there is a signature for default creds
                if parse_html(
                        internal_data['identifier'], http_object.source_code):
                    http_object = handle_category_match(
                        internal_data, http_object)
                    identifier = True
                    break
            # There was not a signature for it.
            # But let's check to see if there is a login form
            if identifier is False:
                # checkLogin(http_object, data_file)
                if check_login_form(http_object.source_code):
                    # Need to add and for if they want to continue checking
                    inputs = get_input_fields(http_object.source_code)
                    if inputs[1] is not None:
                        target = update_target(target, inputs[1])
                    inputs = inputs[0]
                    if inputs is not None:
                        for cred in creds:
                            temp_cred = cred.split(':')
                            post_data = get_post_data(
                                inputs, temp_cred[0], temp_cred[1])
                            # to be used for loggin
                            if login_post(
                                    http_object.remote_system, target,
                                    post_data, data, True):
                                print "\x1b[32m[+]Form Successful login against {} using {}s\x1b[0m".format(http_object.remote_system, ':'.join(temp_cred))
                                http_object.category = "successfulLogin"
                                http_object.default_creds = "Default creds are valid: {}".format(temp_cred)
                                http_object._remote_login = target
                                break
                            else:
                                http_object.category = "identifiedLogin"

                # attempt to append known login urls to target
                # and see if there is auth page
                else:
                    urls = parse_urls(data_file)
                    http_object = find_logins(http_object, creds, urls)
        # Check to see if it is basic authentication and try logging in
        elif '401 Unauthorized' in http_object.page_title:
            # Need to add and for if they want to continue checking
            for cred in creds:
                temp_cred = cred.split(':')
                if http_auth(
                        http_object.remote_system, temp_cred[0], temp_cred[1]):
                    http_object.category = "successfulLogin"
                    http_object.default_creds = "Default creds are valid: {}".format(temp_cred)
                    break

    except Exception, e:
        print e
    return http_object
