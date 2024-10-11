import asyncio
from concurrent.futures import ThreadPoolExecutor
import requests
import time
import aiohttp
from selenium import webdriver
import asyncio
import sys
from bs4 import BeautifulSoup

class Value:
    def __init__(self):
        self.name = ""
        self.set = None
        self.ungraded = None
        self.psa9 = None
        self.psa10 = None
        self.card_id = None

async def fetch_values_old(url, session):
    text = []
    for i in range(1, 10):
        cursor_val = str((i - 1) * 50)
        myobj = {
            'sort': 'highest-price',
            'cursor': cursor_val
        }
        async with session.post(url, json=myobj) as response:
            response_text = await response.text()
            text.append(response_text + "\n")
    return text

async def fetch_all_values(urls):
    # Use ThreadPoolExecutor to run multiple fetches in parallel
    i = 0
    with ThreadPoolExecutor(max_workers=3) as executor:
        loop = asyncio.get_event_loop()
        # Run all tasks concurrently using asyncio and ThreadPoolExecutor
        tasks = [loop.run_in_executor(executor, fetch_values, url) for url in urls]
        i += 1
        print(i)
        # Gather results
        return await asyncio.gather(*tasks)

async def get_set_values(set_names):
    urls = []
    for set in set_names:
        url = 'https://www.pricecharting.com/console/pokemon-' + set.replace(" ", "-") + '?sort=highest-price'
        urls.append(url)
    results = await fetch_all_values(urls)
    #for result in results:
        #print("result:", result)
    return_values = []
    i = 0
    for result in results:
        new_values = get_values(set_names[i], result)
        for value in new_values:
            return_values.append(value)
        i += 1
    return return_values
    #print(results)

def fetch_values(url):
    print(url)
    SCROLL_PAUSE_TIME = 0
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")

    # Optional: Disable images and JavaScript if not necessary
    chrome_options.add_argument("--disable-images")
    chrome_options.add_argument("--disable-javascript")
    #chrome_options.add_argument("--window-size=1024,768")
    browser = None
    for i in range(3):
        try:
            browser = webdriver.Chrome(options=chrome_options)
            browser.set_page_load_timeout(30)
            break
        except Exception as e:
            print("except:", str(e))
    if browser is None: return ''

    browser.get(url)
    prevHeight = browser.execute_script("return document.body.scrollHeight")
    atBottom = False # occasionally selenium lags, this ensures that we are truly at the bottom
    last_len = 0
    cur_len = 0
    while True:
        cur_len = len(browser.page_source)
        if cur_len == last_len:
            if time.time() - last_time > 1.5: break
            continue
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        currHeight = browser.execute_script("return document.body.scrollHeight")
        if prevHeight == currHeight:
            if atBottom:
                break
            atBottom = True
        else:
            atBottom = False
        prevHeight = currHeight
        last_len = len(browser.page_source)
        last_time = time.time()
    source = browser.page_source
    browser.close()
    return source

def get_card_id(title):
    for word in title.split(" "):
        if '/' in word or '#' in word:
            word = word.replace('#','')
            if '/' in word:
                word = word.split("/")[0]
            word = word.lstrip('0')
            return word
    return None

#print(get_card_id("2021 Pokémon Fusion Strike Espeon Vmax 270/264 Alt Art Secret Ace 10"))
#sys.exit()
def get_values(set_name, text):
    i = 0
    values = []
    #print(text)
    page_text = text
    page_text_split = page_text.split("<td class=\"title\" title=")
    for item in page_text_split:
        item_split = item.split("</td>")
        if len(item_split) < 2: continue
        name = item_split[0].split(">")[2].split("<")[0].replace("\n", "").strip()
        ungraded_price = None
        psa9_price = None
        psa10_price = None
        if len(item_split) >= 2 and len(item_split[1].split(">")) >= 3:
            ungraded_price = item_split[1].split(">")[2].split("<")[0].replace("\n", "").strip()
        if len(item_split) >= 3 and len(item_split[2].split(">")) >= 3:
            psa9_price = item_split[2].split(">")[2].split("<")[0].replace("\n", "").strip()
        if len(item_split) >= 4 and len(item_split[3].split(">")) >= 3:
            psa10_price = item_split[3].split(">")[2].split("<")[0].replace("\n", "").strip()
        if ungraded_price == "": ungraded_price = None
        if psa9_price == "": psa9_price = None
        if psa10_price == "": psa10_price = None
        if ungraded_price is not None:
            ungraded_price = float(ungraded_price.replace("$", "").replace(",", ""))
        if psa9_price is not None:
            psa9_price = float(psa9_price.replace("$", "").replace(",", ""))
        if psa10_price is not None:
            psa10_price = float(psa10_price.replace("$", "").replace(",", ""))
        value = Value()
        value.set = set_name
        value.name = name
        value.ungraded = ungraded_price
        value.psa9 = psa9_price
        value.psa10 = psa10_price
        value.card_id = None
        for word in name.split(" "):
            if '#' in word:
                value.card_id = word.replace("#","")
        if 'booster box' in name.lower():
            value.card_id = 'booster box'
        elif 'booster pack' in name.lower():
            value.card_id = 'booster pack'
        if len(value.name.split(" ")) >= 2:
            values.append(value)
    return values

async def get_all_values(set_name):
    value_urls = []
    #for set_name in set_names:
    value_url = 'https://www.pricecharting.com/console/pokemon-' + set_name.replace(" ", "-") + '?sort=highest-price'
    value_urls.append((set_name, value_url))
    values = []
    async with aiohttp.ClientSession() as session:
        value_results = await asyncio.gather(*[fetch_values(url) for _, url in value_urls])
        for i, result in enumerate(value_results):
            set_name = value_urls[i][0]
            new_values = get_values(set_name, result)
            for value in new_values:
                values.append(value)
    return values

async def main():
    start_time = time.time()
    set_names = []
    excluded_sets = []
    with open('excluded_sets.txt', 'r') as f:
        lines = f.readlines()
    for line in lines:
        line = line.replace("\n","")
        excluded_sets.append(line)
    with open('sets.txt', 'r') as f:
        lines = f.readlines()
    for line in lines:
        set_name = line.strip().replace("Pokemon ", "")
        if set_name in excluded_sets: continue
        set_names.append(set_name)
    #set_names = [line.strip().replace("Pokemon ", "") for line in lines]

    # Get all values
    #await get_all_values(set_names)

    i = -1
    '''
    while i < len(set_names) - 1:
        current_set_names = []
        for j in range(50):
            i += 1
            if i >= len(set_names):
                break
            current_set_names.append(set_names[i])
        await get_all_pages('UK', current_set_names, 2)
    '''
    #await get_all_pages('UK' , ['fusion strike'], 1)
    #values = await get_all_values('fusion strike')
    #values = await get_all_values('paradox rift')
    #values = await get_all_values('team rocket')
    #values = await get_all_values('base set')
    #values = await get_all_values('astral radiance')
    values = await get_set_values(set_names)
    values_dict = {}
    for value in values:
        if value.set not in values_dict:
            values_dict[value.set.lower()] = {}
        if value.card_id is None: continue
        print(value.set, value.name)
        values_dict[value.set.lower()][value.card_id] = value
    duration = time.time() - start_time
    #await get_all_pages('UK', ['fusion strike'], 1, values_dict)
    print("total cards:", len(values))
    print(f"Execution time: {duration:.2f} seconds")

# Ensure we're only running asyncio.run() once and avoid nested loops
if __name__ == "__main__":
    try:
       # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except RuntimeError as e:
        if str(e).startswith("This event loop is already running"):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
        else:
            raise