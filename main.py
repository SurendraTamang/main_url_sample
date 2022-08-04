from datetime import datetime
import sqlite3
from tabnanny import check
from seleniumwire import webdriver
from random import randint
from time import sleep
import sys
import os
import fnmatch
from urllib.parse import urlparse
from selenium.common.exceptions import TimeoutException

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TIMEOUT_DELAY_MIN = 18
TIMEOUT_DELAY_MAX = 20
RESETART_DRIVER_COUNT = 15


def setup_folders():
    os.makedirs("history", exist_ok=True)
    os.makedirs("source", exist_ok=True)
    os.makedirs("screenshots", exist_ok=True)

def setup_database(cur):
    query = '''CREATE TABLE IF NOT EXISTS entries
            (date text, time text, url text, found text, fonts_url text)'''
    cur.execute(query)

def setup_driver():
    opts = webdriver.FirefoxOptions()
    opts.set_preference("browser.cache.disk.enable", False)
    opts.set_preference("browser.cache.memory.enable", False)
    opts.set_preference("browser.cache.offline.enable", False)
    opts.set_preference('permissions.default.image', 2)
    opts.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'false')
    opts.set_preference("network.http.use-cache", False)
    opts.set_preference("network.http.pipelining", True)
    opts.set_preference("network.http.proxy.pipelining", True)
    opts.set_preference("network.http.pipelining.maxrequests", 8)
    opts.set_preference("content.notify.interval", 500000)
    opts.set_preference("content.notify.ontimer", True)
    opts.set_preference("content.switch.threshold", 250000)
    opts.set_preference("browser.cache.memory.capacity", 65536) # Increase the cache capacity.
    opts.set_preference("browser.startup.homepage", "about:blank")
    opts.set_preference("reader.parse-on-load.enabled", False) # Disable reader, we won't need that
    opts.set_preference("browser.pocket.enabled", False) # Duck pocket too!
    opts.set_preference("loop.enabled", False)
    opts.set_preference("browser.chrome.toolbar_style", 1) # Text on Toolbar instead of icons
    opts.set_preference("browser.display.show_image_placeholders", False) # Don't show thumbnails on not loaded images.
    opts.set_preference("browser.display.use_document_colors", False) # Don't show document colors.
    opts.set_preference("browser.display.use_system_colors", True) # Use system colors.
    opts.set_preference("browser.formfill.enable", False) # Autofill on forms disabled.
    opts.set_preference("browser.helperApps.deleteTempFileOnExit", True) # Delete temprorary files.
    opts.set_preference("browser.shell.checkDefaultBrowser", False)
    opts.set_preference("browser.startup.homepage", "about:blank")
    opts.set_preference("browser.startup.page", 0) # blank
    opts.set_preference("browser.tabs.forceHide", True) # Disable tabs, We won't need that.
    opts.set_preference("browser.urlbar.autoFill", False) # Disable autofill on URL bar.
    opts.set_preference("browser.urlbar.autocomplete.enabled", False) # Disable autocomplete on URL bar.
    opts.set_preference("browser.urlbar.showPopup", False) # Disable list of URLs when typing on URL bar.
    opts.set_preference("browser.urlbar.showSearch", False) # Disable search bar.
    opts.set_preference("extensions.checkCompatibility", False) # Addon update disabled
    opts.set_preference("extensions.checkUpdateSecurity", False)
    opts.set_preference("extensions.update.autoUpdateEnabled", False)
    opts.set_preference("extensions.update.enabled", False)
    opts.set_preference("general.startup.browser", False)
    opts.set_preference("plugin.default_plugin_disabled", False)
    opts.set_preference("permissions.default.image", 2) # Image load disabled again
    opts.set_preference('javascript.enabled', False)

    
    
    
    
    
    
    driver = webdriver.Firefox(options=opts, executable_path='geckodriver')
    driver.set_page_load_timeout(randint(TIMEOUT_DELAY_MIN, TIMEOUT_DELAY_MAX))
    return driver

def load_sites():
    try:
        result = []
        with open("sites.txt", "r") as f:
            for l in f:
                result.append(l.strip())
        return result
    except Exception as e:
        print("Error loading sites.txt", str(e))
        sys.exit(1)

def analyze_requests(requests):
    try:
        for req in requests:
            if "fonts.googleapis.com" in req.url or "fonts.gstatic.com" in req.url:
                return req
        return None
    except Exception as e:
        print("Error analyzing requests", str(e))
        return None

def insert_result(found, url, fonts_url = ""):
    try:
        _date = datetime.now().strftime("%H:%M:%S")
        _time = datetime.now().strftime("%d/%m/%Y")
        print(_date, _time, url, found, fonts_url)
        query = '''INSERT INTO entries (date, time, url, found, fonts_url) VALUES (?,?,?,?,?)'''
        cur.execute(query, (_date, _time, url, found, fonts_url))
    except Exception as e:
        print("Unhandled exception while inserting", url, str(e))

def take_screenshot(driver, url):
    try:
        img_name = urlparse(url).netloc + ".png"
        driver.save_screenshot(os.path.join(ROOT_DIR, "screenshots", img_name))
        sleep(2)
    except Exception as e:
        print("Error saving screenshot for url", url, str(e))

def save_request(req, url):
    try:
        result = "___Request___\n"
        for header in req.headers:
            result += header + ": " + req.headers[header] + "\n"
        
        result += "\n___Response___\n"
        for header in req.response.headers:
            result += header + ": " + req.response.headers[header] + "\n"
            

        history_file = open(os.path.join(ROOT_DIR, "history", urlparse(url).netloc + ".txt"), "w")
        history_file.write(result)
        history_file.close()
    except Exception as e:
        print("Error saving request to history for", url, str(e))

def save_source(driver, url):
    try:
        html_source = driver.page_source
        source_file = open(os.path.join(ROOT_DIR, "source", urlparse(url).netloc + ".txt"), "w")
        source_file.write(html_source)
        source_file.close()
    except Exception as e:
        print("Error while saving source code for website", url, str(e))

def is_site_visited(cursor, url):
    query = '''SELECT EXISTS(SELECT 1 FROM entries WHERE url=?) LIMIT 1;'''
    cursor.execute(query, (url,))
    rows = cursor.fetchall()
    exists = rows[0][0]
    if exists: return True
    else: return False

def drive(driver, url):
    try:
        # reset requests
        del driver.requests
        # load page
        try:
            driver.get(url)
        except TimeoutException:
            pass
        # analyze requests
        result = analyze_requests(driver.requests)
        if not result:
            insert_result(False, url)
            return False
        # Write to database
        insert_result(True, url, result.url)
        # save screenshot
        take_screenshot(driver, url)
        # save source code
        save_source(driver, url)
        # save request headers
        save_request(result, url)
        print("number of found:",len(fnmatch.filter(os.listdir("history"), '*.*')))
    except Exception as e:
        print("unhandled exception while driving to url", url, str(e))
        return False

if __name__ == "__main__":
    # setup structure
    setup_folders()
    # database setup
    con = sqlite3.connect("database.db")
    cur =  con.cursor()
    setup_database(cur)

    # selenium setup
    driver = setup_driver()
    # load files
    sites = load_sites()

    reset_driver_counter = 0
    print("start")
    
    
    for site in sites:
        if is_site_visited(cur, site):
        		print("already visited:",site)
        		continue
        if reset_driver_counter == RESETART_DRIVER_COUNT:
            driver.quit()
            driver = setup_driver()
            reset_driver_counter = 0
        
        drive(driver, site)

        reset_driver_counter += 1
        con.commit()