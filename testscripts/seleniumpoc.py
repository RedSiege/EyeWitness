from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.proxy import Proxy, ProxyType

# Simple Stuff
driver = webdriver.Firefox()
driver.get('http://whatsmyuseragent.com/')

# User Agent Switch
profile = webdriver.FirefoxProfile()
profile.set_preference("general.useragent.override",
                       "Mozilla/5.0 (Windows NT 6.3; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/37.0.2049.0 Safari/537.36")
driver = webdriver.Firefox(profile)
driver.get('http://whatsmyuseragent.com/')

# Selenium with a proxy
proxhost = "localhost:8080"

proxy = Proxy({
    'proxyType': ProxyType.MANUAL,
    'httpProxy': proxhost,
    'ftpProxy': proxhost,
    'sslProxy': proxhost,
    'noProxy': ''
})

driver = webdriver.Firefox(proxy=proxy)
driver.get('http://www.google.com')
