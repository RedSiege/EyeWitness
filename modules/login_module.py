import base64
import os
import urllib2
import urllib
import cookielib
import re
from random import choice
from bs4 import BeautifulSoup as beatsop
import socket

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


def parseDataFile(input):
    # this is where you will parse the data file for each category
    with open(input, 'r') as f1:
        file = f1.readlines()

    currentCategory = []

    for line in file:
        if line.startswith("Category"):
            category = {}
            category['category'] = re.findall("Category:\s(.*)", line)
        elif line.startswith("identifier"):
            identifier = re.findall("identifier:\s(.*)", line)
            category['identifier'] = identifier
        elif line.startswith("invalid_identifier"):
            identifier = re.findall("invalid_identifier:\s(.*)", line)
            category['invalid_identifier'] = identifier
        elif line.startswith("login_type"):
            identifier = re.findall("login_type:\s(.*)", line)
            category['login_type'] = identifier
        elif line.startswith("default creds"):
            defaultCreds = re.findall("default creds:\s(.*)", line)
            category['defaultCreds'] = defaultCreds
        elif line.startswith("default path"):
            defaultPath = re.findall("default path:\s(.*)", line)
            category['defaultPath'] = defaultPath

            currentCategory.append(category)
    return currentCategory


def parseHTML(identifier, htmlSource):
    # This wil determine if the identifier is in the html of the target page
    # TODO: Consider logging the ones that were not identified
    identified = False
    if identifier[0].lower() in htmlSource.lower():
        identified = True
    return identified


def parseURL(url, protocol):
    # this will parse the URL to get the html data from the page
    # TODO: If this is HTTP, need to figure out if we handle it differently.
    # TODO: May need to add http(s) in front of it
    # depending on the check result
    # TODO: Handle exceptions so it doens't break
    # TODO: If it returns a 401 it will throw exception.
    # Need to handle that as basic auth
    htmlSource = ''
    if url.startswith('http') is False:
        url = protocol + '://' + url
    try:
        # consider a timeout for this because it takes awhile
        sock = urllib2.urlopen(url, timeout=3)
        htmlSource = sock.read()
        sock.close()
    except urllib2.URLError, e:
        raise Exception("There was an error: {}".format(e))
    except Exception, e:
        raise Exception("There was an error: {}".format(e))
    return htmlSource


def checkValidUrl(url):
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
    else:
        return response.getcode()


def handleCategoryMatch(data, http_object):
    # this is where you will login to the site
    # you ca call parseURL if you need to get the html of
    # the path to get for data
    # TODO: You only login to the path specific within data
    logintype = data['login_type']
    creds1 = data['defaultCreds']
    # This will get the login URL to the target
    origTarget = http_object.remote_system
    target = origTarget + data['defaultPath'][0]

    if logintype[0] == 'http_post':
        redirect = False
        try:
            req = urllib2.Request(origTarget)
            opener = urllib2.build_opener(SmartRedirectHandler())
            rsp = opener.open(req)
            code = rsp.getcode()

            # print req.getcode()
            if code == 301 or code == 302:
                # get the html source so you can see if password
                #  is in the new url
                target = rsp.geturl()
                redirect = True

        except urllib2.URLError, e:
            raise Exception("There was an error: {}".format(e))

        htmlSource = parseURL(origTarget, '')
        inputs = getInputFields(htmlSource)
        if inputs[1] is not None:
            target = updateTarget(http_object.remote_system, inputs[1])
        inputs = inputs[0]

    for x in creds1:
        seperated = re.split(',\s*', x)

    for y in seperated:
        creds = y.split(':')
        username = creds[0]
        password = creds[1]

        # Check to see if authentication is form based or http_basic
        if logintype[0] == 'http_auth':
            check = httpAuth(target, username, password)
            # Auth was successful, no need to continue
            if check:
                http_object.default_creds = "Default creds are valid: {}".format(y)
                http_object.category = "successfulLogin"
                http_object._remote_login = target
                break
        elif logintype[0] == 'http_post':
            # login with form based auth
            if inputs is not None:
                postData = getPostData(inputs, username, password)
                # to be used for logging
                if loginPost(origTarget, target, postData, data):
                    print "\x1b[32m[+]Form Successful login against {} using {}\x1b[0m".format(target, y)
                    http_object.default_creds = "Default creds are valid: {}".format(y)
                    http_object.category = "successfulLogin"
                    http_object._remote_login = target
                    break
                else:
                    http_object.category = "identifiedLogin"

        else:
            print 'incorrect login type for {}'.format(data)
    return http_object


def checkLoginForm(html_data):
    try:
        html_proc = beatsop(html_data)
        loginForm = False

        forms = html_proc.findAll('form')
        for x in forms:
            if x.findAll('input', {'type': 'password'}) != []:
                loginForm = True
        return loginForm
    except Exception:
            pass


def getInputFields(html_data):
    # TODO: Consider getting new target if 301 or 302
    try:
        html_proc = beatsop(html_data)
        postData = {}
        inputs = []
        allInputs = ['', '']
        action = None

        forms = html_proc.findAll('form')
        for x in forms:
            if x.findAll('input', {'type': 'password'}) != []:
                inputs = x.findAll('input')
                # Get form action and append it to the base URL
                # Not everything will have an action. Maybe log
                # that it's a login form, but couldn't attempt login
                action = x.get('action')

        allInputs[0] = inputs
        allInputs[1] = action
        return allInputs
    except Exception as e:
            print e


def updateTarget(target, action):
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


def getPostData(inputs, uname, pword):
    postData = {}
    try:
        if inputs != []:
            for y in inputs:
                if 'name' in str(y) or 'user' in str(y) or 'usr' in str(y):
                    if y['type'] == 'text' or y['type'] == 'email':
                        if 'name' in str(y):
                            postData[y['name']] = uname
                        elif 'user' in str(y):
                            postData[y['user']] = uname
                        elif 'usr' in str(y):
                            postData[y['usr']] = uname
                    elif y['type'] == 'password':
                        postData[y['name']] = pword
                    elif y['type'] == 'hidden':
                        if 'value' in str(y):
                            try:
                                postData[y['name']] = y['value'].encode(
                                    'utf-8')
                            except:
                                pass
                        else:
                            postData[y['name']] = ""
                    else:
                        if 'value' in str(y):
                            try:
                                postData[y['name']] = y['value'].encode(
                                    'utf-8')
                            except:
                                pass
                        else:
                            postData[y['name']] = ""
        return postData

    except:
        pass


def loginPost(url, target, postData, data, stillTrying=False):
    # This function will post the data that is passed to it after the post data
    # is populated
    failChecks = [
        'fail', 'error', 'invalid', 'failed', 'incorrect',
        'try entering it again', 'bad user name', 'bad password',
        'name="password"']
    try:
        result = False
        # acquire cookie
        req = urllib2.Request(url)
        rsp = urllib2.urlopen(req, timeout=3)

        # do POST
        pData = urllib.urlencode(postData)
        req = urllib2.Request(target, pData)
        rsp = urllib2.urlopen(req, timeout=3)
        content = rsp.read()

        if stillTrying is False:
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
            if any(x in content.lower() for x in failChecks) or rsp.getcode() == 401:
                result = False
            else:
                result = True

    except urllib2.URLError, e:
        if isinstance(e.reason, socket.timeout):
            raise Exception("There was an error with {}".format(e))
            result = False

    except socket.timeout, e:
        raise Exception("There was an error with {}".format(e))
        result = False
    except Exception, e:
        raise Exception("There was an error: {}".format(e))

    return result


def httpAuth(target, username, password):
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
        result = urllib2.urlopen(request)
        success = True
        print "\x1b[32m[+]Http basic Successful login against {} using {}\x1b[0m".format(target, creds)
    except:
        success = False
    return success


def getAllCreds(dataFile):
    file = open(dataFile, 'r').readlines()
    passwords = []
    listStart = False

    for line in file:
        if listStart:
            if line == '\n' or line == '' or line == '\r\n':
                break
            else:
                passwords.append(line.rstrip())
        if line.startswith("### still trying"):
            listStart = True
    return passwords


def parseURLs(input):
    file = open(input, 'r').readlines()
    urls = []
    listStart = False

    for line in file:
        if listStart:
            if line == '\n' or line == '' or line == '\r\n':
                break
            else:
                urls.append(line.rstrip())
        if line.startswith("###URL"):
            listStart = True
    return urls


def findLogins(http_object, creds, urls):
    # append list of urls to see if there are urls associated with host
    # TODO: make new category for logins
    validUrls200 = []
    validUrls401 = []
    origTarget = http_object.remote_system
    result = False
    for url in urls:
        target = http_object.remote_system + url
        if checkValidUrl(target) == 200:
            validUrls200.append(target)
        elif checkValidUrl(target) == 401:
            validUrls401.append(target)
    # There is a basic auth
    if validUrls401 != []:
        for cred in creds:
            httpAuth(validUrls401[0], cred[0], cred[1])
    # see if form authentication and if there is, then try to login
    if validUrls200 != []:
        for validURL in validUrls200:
            target = validURL
            if result is True:
                break
            source = parseURL(validURL, '')
            if checkLoginForm(source):
                http_object._remote_login = target
                inputs = getInputFields(source)
                if inputs[1] is not None:
                    target = updateTarget(origTarget, inputs[1])
                inputs = inputs[0]
                if inputs is not None:
                    for cred in creds:
                        tempCred = cred.split(':')
                        postData = getPostData(
                            inputs, tempCred[0], tempCred[1])
                        # to be used for loggin
                        if loginPost(target, target, postData, "", True):
                            print "\x1b[32m[+]Form Successful login against {} using {}\x1b[0m".format(origTarget, ':'.join(tempCred))
                            http_object.default_creds = "Default creds are valid: {}".format(tempCred)
                            result = True
                            http_object.category = "successfulLogin"
                            http_object._remote_login = target
                            break
                        else:
                            http_object.category = "identifiedLogin"
    return http_object


def checkCreds(http_object):
    identifier = False
    target = http_object.remote_system
    print "Attempting active scan against {}".format(target)

    try:
        dataFile = os.path.join(os.path.dirname(
            os.path.abspath(__file__)), '..', 'dataFile.txt')
        creds = getAllCreds(dataFile)
        data = parseDataFile(dataFile)
    except IOError:
        print("[*] WARNING: Credentials file not in the same directory"
              " as EyeWitness")
        print '[*] Skipping credential check'

    try:
        # Loop through and see if there are any matches from the source code
        # EyeWitness obtained
        if http_object.source_code is not None and '401 Unauthorized' not in http_object.page_title:
            for internalData in data:
                # Check to see if there is a signature for default creds
                if parseHTML(
                        internalData['identifier'], http_object.source_code):
                    http_object = handleCategoryMatch(
                        internalData, http_object)
                    identifier = True
                    break
            # There was not a signature for it.
            # But let's check to see if there is a login form
            if identifier is False:
                # checkLogin(http_object, dataFile)
                if checkLoginForm(http_object.source_code):
                    # Need to add and for if they want to continue checking
                    inputs = getInputFields(http_object.source_code)
                    if inputs[1] is not None:
                        target = updateTarget(target, inputs[1])
                    inputs = inputs[0]
                    if inputs is not None:
                        for cred in creds:
                            tempCred = cred.split(':')
                            postData = getPostData(
                                inputs, tempCred[0], tempCred[1])
                            # to be used for loggin
                            if loginPost(
                                    http_object.remote_system, target,
                                    postData, data, True):
                                print "\x1b[32m[+]Form Successful login against {} using {}s\x1b[0m".format(http_object.remote_system, ':'.join(tempCred))
                                http_object.category = "successfulLogin"
                                http_object.default_creds = "Default creds are valid: {}".format(tempCred)
                                http_object._remote_login = target
                                break
                            else:
                                http_object.category = "identifiedLogin"

                # attempt to append known login urls to target
                # and see if there is auth page
                else:
                    urls = parseURLs(dataFile)
                    http_object = findLogins(http_object, creds, urls)
        # Check to see if it is basic authentication and try logging in
        elif '401 Unauthorized' in http_object.page_title:
            # Need to add and for if they want to continue checking
            for cred in creds:
                tempCred = cred.split(':')
                if httpAuth(
                        http_object.remote_system, tempCred[0], tempCred[1]):
                    http_object.category = "successfulLogin"
                    http_object.default_creds = "Default creds are valid: {}".format(tempCred)
                    break

    except Exception, e:
        print e
    return http_object
