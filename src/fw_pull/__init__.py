#!/usr/bin/env python3

import re
import sys
import json
from argparse import ArgumentParser as AP

from bs4 import BeautifulSoup
import requests
from requests.exceptions import HTTPError

#from pyvirtualdisplay import Display

from selenium import webdriver 
from selenium.webdriver.common.by import By 
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait 
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC 
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile


def get_args():
    parser = AP(description="Gets the latest firmware version from vendor sites")
    parser.add_argument(
        "-d",
        "--debug",
        help="Turns on debug mode and loads the driver in the foreground",
        action="store_true"
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help="JSON file containing the server models to retrieve fw info for",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=False,
        help="File to write JSON data to",
    )

    return parser.parse_args()


def read_json(path):
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"Failed to decode json: {e}")
        sys.exit(1)
    except OSError as e:
        print(f"Could not read {path}: {e}")
        sys.exit(1)


def write_json(data, path):
    try:
        with open(path, 'w') as f:
            return json.dump(data, f)
    except TypeError as e:
        print(f"Failed to encode json: {e}")
        sys.exit(1)
    except OSError as e:
        print(f"Could not write {path}: {e}")
        sys.exit(1)


def get_oracle(server):
    model = server['Model']

    fw_re = re.compile('(^Sun System Firmware \d*\.\d*\.\d*(\.[a-z])?)')

    # fw_url = "https://www.oracle.com/technetwork/systems/patches/firmware/release-history-jsp-138416.html"
    fw_url = "https://www.oracle.com/servers/technologies/firmware/release-history-jsp.html"

    try:
        response = requests.get(fw_url)
        response.raise_for_status()
    except HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
        sys.exit(1)
    except Exception as e:
        print(f'An unexpected error occured: {e}')
        sys.exit(1)

    servers_soup = BeautifulSoup(response.text, 'html.parser')

    # find the table with all the fw versions
    # table = servers_soup.find('table', class_="vatop")
    table = servers_soup.find('table', class_="otable-w2 otable-tech-basic")

    # starting from the table look for the link containing this model

    if table == None:
        print(servers_soup.prettify())

    for link in table.find_all('a'):
        if model.lower() in link.text.lower():
            link = link
            break

    # the newest fw version is the next fw tag
    fw_ver = link.find_next('strong')

    # get previous version
    app_fw = link.find_next('td').find_next('td').find_next('td').find_next('p')

    # extract the fw version from the text
    ver = fw_re.match(fw_ver.text).groups(0)[0]
    app_ver = fw_re.match(app_fw.text).groups(0)[0]

    server['GA Firmware Version'] = ver.split()[-1]
    server['N-1 Approved Firmware'] = app_ver.split()[-1]

    return server


# No longer needed since we have to search for the HPs
def hp_model(model):
    return model.split()[1]


def get_hp(driver, server):
    timeout = 60

    url = "https://support.hpe.com/hpesc/public/home"

    try:
        driver.get(url)

        # wait for search box
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(
                (By.XPATH, "/html/body/div[1]/div/div[3]/div/div[1]/div/div[2]/div[1]/div/div[1]/div/div/div[2]/div[1]/div[3]/div[3]/div[1]/input")
            )
        )

        # send input
        search_box = driver.find_element_by_xpath("/html/body/div[1]/div/div[3]/div/div[1]/div/div[2]/div[1]/div/div[1]/div/div/div[2]/div[1]/div[3]/div[3]/div[1]/input")
        search_box.send_keys(server['Model'])
        search_box.send_keys(Keys.RETURN)

        # wait for bios link
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(
                (By.XPATH, "/html/body/div[1]/div[1]/div/div[3]/div/div/div[4]/div[2]/div[14]/div[1]/div/div[1]/div/div[2]/div[2]/div[2]/div/a[1]")
            )
        )

        bios_link = driver.find_element_by_xpath("/html/body/div[1]/div[1]/div/div[3]/div/div/div[4]/div[2]/div[14]/div[1]/div/div[1]/div/div[2]/div[2]/div[2]/div/a[1]")
        bios_link.click()

        # wait for the bios quick filter to become visible
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//a[@id='biosanchor']")
            )
        )

        # find and click the bios quick filter
        bios_button = driver.find_element_by_xpath("//div[@id='biosquickfilter']")
        bios_button.click()

#        # wait for field containing the bios version
#        WebDriverWait(driver, timeout).until(
#            EC.visibility_of_element_located(
#                (By.XPATH, "/html/body/div[1]/div[1]/div/div[3]/div/div/div[4]/div[3]/div[5]/div[10]/div/div[1]/div/div/div[2]/div/div[3]/div[1]/span[3]/span")
#            )
#        )
#
#        print("Bios field is there")
#
#        bios_field = driver.find_element_by_xpath("/html/body/div[1]/div[1]/div/div[3]/div/div/div[4]/div[3]/div[5]/div[10]/div/div[1]/div/div/div[2]/div/div[3]/div[1]/span[3]/span")
#        bios_field.click()
#
#        field_html = bios_field.get_attribute('outerHTML')
#        field_src = BeautifulSoup(field_html, 'html.parser')
#        print(field_src.text)

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/8);")

        #wait for more details button
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(
                (By.XPATH, "/html/body/div[1]/div[1]/div/div[3]/div/div/div[4]/div[3]/div[5]/div[10]/div/div[1]/div/div/div[3]/div/div[1]")
            )
        )

        more_details = driver.find_element_by_xpath("/html/body/div[1]/div[1]/div/div[3]/div/div/div[4]/div[3]/div[5]/div[10]/div/div[1]/div/div/div[3]/div/div[1]")
        more_details.click()

        # wait for the link to the dl page to be visible
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(
                (By.XPATH, "/html/body/div[1]/div[1]/div/div[3]/div/div/div[4]/div[3]/div[5]/div[10]/div/div[1]/div/div/div[3]/div/div[2]/table/tbody/tr[1]/td/span/a")
            )
        )
        dl_link = driver.find_element_by_xpath("/html/body/div[1]/div[1]/div/div[3]/div/div/div[4]/div[3]/div[5]/div[10]/div/div[1]/div/div/div[3]/div/div[2]/table/tbody/tr[1]/td/span/a")

        # get the a tag
        link_outter = dl_link.get_attribute('outerHTML')
        link_html = BeautifulSoup(link_outter, 'html.parser')

        driver.get(link_html.a['href'])

        # wait for revision history
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//*[@id='ui-id-6']")
            )
        )
        rev_history = driver.find_element_by_xpath("//*[@id='ui-id-6']")
        rev_history.click()
    
        source = BeautifulSoup(driver.page_source, 'html.parser')

    except Exception as e:
        source = driver.page_source
        print(f'Error: {e}')
        driver.get_screenshot_as_file('Failed_hp.png')
        #driver.close()
        sys.exit(1)

    ga_fw = None
    approved_fw = None
    bold_tags = source.find_all('b')
    for tag in bold_tags:
        if tag.text.startswith("Version"):
            fw = tag.text.split(":")[1].split("_")[0]
            if not ga_fw:
                ga_fw = fw
            elif ga_fw and not approved_fw and fw != ga_fw:
                approved_fw = fw

    server['GA Firmware Version'] = ga_fw
    server['N-1 Apporved Firmware'] = approved_fw

    return server


def get_dell(driver, server):
    timeout = 20

    model = dell_model(server['Model'])
    
    url = "https://www.dell.com/support/home/us/en/04/product-support/product/" + model.lower() + "/drivers"
    try:
        driver.get(url)
        
        body = driver.find_element_by_xpath("//option[@label='Support']")
        
        action = ActionChains(driver)
        action.move_to_element(body).perform()
        
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//select[@id='operating-system']")
            )
        )

        os_sort = driver.find_element_by_xpath("//select[@id='operating-system']")
        os_sort.click()

        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(
                (By.XPATH, "//option[@value='NAA']")
            )
        )

        bios_select = driver.find_element_by_xpath("//option[@value='NAA']")
        bios_select.click()

        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(
                (By.XPATH,"//select[@id='ddl-category']")
            )
        )
        cat_select = driver.find_element_by_xpath("//select[@id='ddl-category']")
        cat_select.click()

        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(
                (By.XPATH,"//option[@value='BI']")
            )
        )
        cat_bios_sel = driver.find_element_by_xpath("//option[@value='BI']")
        cat_bios_sel.click()

        driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")

        source = BeautifulSoup(driver.page_source, 'html.parser')
    
    except Exception as e:
        print(e)
        if not debug:
            driver.quit()
        sys.exit(1)
    
    list_items = source.find_all('td')
    
    ver = re.compile("Version (\d+\.\d+(\.\d+)?)")
    
    for item in list_items:
        match = ver.search(item.text)
        if match:
            server['GA Firmware Version'] = match.group(1)

    if not 'GA Firmware Version' in server:
        server['GA Firmware Version'] = None

    try:
        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(
                (By.XPATH,"/html/body/div[2]/div/div[5]/div/div[8]/div/div[2]/div/section[1]/div/div[6]/div[1]/table/tbody/tr/td[6]/button")
            )
        )
        dropdown = driver.find_element_by_xpath("/html/body/div[2]/div/div[5]/div/div[8]/div/div[2]/div/section[1]/div/div[6]/div[1]/table/tbody/tr/td[6]/button")
        dropdown.click()

        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(
                (By.XPATH,"/html/body/div[2]/div/div[5]/div/div[8]/div/div[2]/div/section[1]/div/div[6]/div[1]/table/tbody/tr[2]/td[2]/section/p[3]/a")
            )
        )
        older_ver_link = driver.find_element_by_xpath("/html/body/div[2]/div/div[5]/div/div[8]/div/div[2]/div/section[1]/div/div[6]/div[1]/table/tbody/tr[2]/td[2]/section/p[3]/a")
        older_ver_link.click()

        WebDriverWait(driver, timeout).until(
            EC.visibility_of_element_located(
                (By.XPATH,"//*[@id='oldVersionBody']")
            )
        )

        source = BeautifulSoup(driver.page_source, 'html.parser')

        app_ver_table = source.find('table', class_="table mb-0 w-100")
        if app_ver_table == None:
            print("Could not locate the table")
            print(source.prettify())
        app_ver_link = app_ver_table.find_next('a') #.find_next('a')

        if app_ver_link:
            server['N-1 Approved Firmware'] = app_ver_link.text
        else:
            print("Did not find the link")
            print(source.prettify())
            server['N-1 Approved Firmware'] = None
    except Exception as e:
        print(e)
        driver.quit()
        sys.exit(1)


    return server


def dell_model(name):
    return name.strip().replace(" ", "-").lower()


def main():
    args = get_args()
    options = Options()
    if args.debug:
        options.headless = False
    else:
        options.headless = True
        #display = Display(visible=0, size=(1366, 1037))
        #display.start()

    profile = FirefoxProfile()
    profile.set_preference("browser.privatebrowsing.autostart", True)
    
    try:
        driver = webdriver.Firefox(firefox_profile=profile, options=options)
    except:
        print("Failed to initiate web driver")
        sys.exit(1)

    driver.set_window_size(952, 1047)

    if args.debug:
        print(driver.get_window_size())

    models = read_json(args.input)

#    models = [
#        {
#            'Model': 'Poweredge R630',
#            'Vendor': 'Dell',
#        }, 
#        {
#            'Model': 'Poweredge R330',
#            'Vendor': 'Dell',
#        }, 
#        {
#            'Model': 'Poweredge R730',
#            'Vendor': 'Dell',
#        }, 
#        {
#            'Model': 'Poweredge R930',
#            'Vendor': 'Dell',
#        }, 
#        {
#            'Model': 'ProLiant DL380 Gen9',
#            'Vendor': 'HP',
#        }, 
#        {
#            'Model': 'ProLiant DL360 Gen10',
#            'Vendor': 'HP',
#        }, 
#        {
#            'Model': 'T5-4',
#            'Vendor': 'Oracle',
#        }, 
#        {
#            'Model': 'T5-2',
#            'Vendor': 'Oracle',
#        }, 
#    ]
    
    out_dat = []

    for model in models:
        if model['Vendor'].lower() == 'dell':
            out_dat.append(get_dell(driver, model))
        elif model['Vendor'].lower() == 'hp':
            out_dat.append(get_hp(driver, model))
        elif model['Vendor'].lower() == 'oracle':
            out_dat.append(get_oracle(model))
    
    if not args.debug:
        driver.quit()

    if args.output:
        write_json(out_dat, args.output)
    else:
        print(out_dat)

if __name__ == '__main__':
    main()
