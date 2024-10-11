import requests
import time
import aiohttp
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

async def fetch(url, session):
    async with session.get(url) as response:
        return await response.text()

async def fetch_values(url, session):
    text = []
    for i in range(1, 10):
        cursor_val = str((i - 1) * 50)
        myobj = {
            'sort': 'highest-price',
            'cursor': cursor_val
        }
        async with session.post(url, json=myobj) as response:
            response_text = await response.text()
            text.append(response_text)
    return text

def get_values(set_names, text):
    i = 0
    values = []
    for set_name in set_names:
        if i > len(text) - 1: break
        page_text = text[i]
        i += 1
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
            if len(value.name.split(" ")) >= 2:
                values.append(value)

async def get_all_values(set_names):
    value_urls = []
    for set_name in set_names:
        value_url = 'https://www.pricecharting.com/console/pokemon-' + set_name.replace(" ", "-") + '?sort=highest-price'
        value_urls.append((set_name, value_url))

    async with aiohttp.ClientSession() as session:
        value_results = await asyncio.gather(*[fetch_values(url, session) for _, url in value_urls])
        for i, result in enumerate(value_results):
            set_name = value_urls[i][0]
            get_values(set_name, result)

async def get_all_pages(region, set_names, num_pages):
    urls = []
    for set_name in set_names:
        search = 'pokemon tcg ' + set_name
        for page_num in range(1, num_pages + 1):
            site = 'ebay.com'
            if region == 'UK': site = 'www.ebay.co.uk'
            if region == 'CA': site = 'ebay.ca'
            search_query = search.replace(" ", "+")
            url = 'https://' + site + '/sch/i.html?_nkw=' + search_query + '&_dmd=1&_ipg=240&_pgn=' + str(page_num)
            urls.append((set_name, url))

    async with aiohttp.ClientSession() as session:
        results = await asyncio.gather(*[fetch(url, session) for _, url in urls])
        tot_listings = 0
        for i, result in enumerate(results):
            url = urls[i][1]
            set_name = urls[i][0]
            search_query = 'pokemon tcg ' + set_name
            count = get_listings(search_query, region, set_name, result)
            tot_listings += count
            print("Total listings:", tot_listings)
            print("Page:", i + 1)

    print(len(results))

def get_listings(search, region, set_name, result):
    soup = BeautifulSoup(result, 'lxml')
    tot_listings = 0
    title_images = {img_tag.get('alt'): img_tag['src'] for img_tag in soup.find_all('img') if 'https://i.ebayimg.com/images/g/' in img_tag['src']}

    for span_tag in soup.find_all('span'):
        text = span_tag.get_text().replace('New listing', '').replace('New Listing', '')
        if span_tag.get('role') == 'heading':
            item_title = text
            if item_title.lower() == "shop on ebay" or set_name.lower() not in item_title.lower():
                continue
            previous_a_tag = span_tag.find_previous('a')
            item_link = previous_a_tag.get('href').split("?")[0] if previous_a_tag else None
        if span_tag.get('class') is not None:
            if span_tag.get('class') == ['s-item__price']:
                item_price = text
            if span_tag.get('class') == ['s-item__space_bar']:
                if " to " in item_price or set_name.lower() not in item_title.lower():
                    continue
                item_image = title_images.get(item_title, 'None')
                print("---")
                print('Title:', item_title)
                print('Link:', item_link)
                print('Image:', item_image)
                print('Price:', item_price)
                tot_listings += 1

    print(set_name + ":", tot_listings)
    return tot_listings

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
    await get_all_pages('UK' , ['fusion strike'], 1)
    duration = time.time() - start_time
    print(f"Execution time: {duration:.2f} seconds")

# Ensure we're only running asyncio.run() once and avoid nested loops
if __name__ == "__main__":
    try:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main())
    except RuntimeError as e:
        if str(e).startswith("This event loop is already running"):
            loop = asyncio.get_event_loop()
            loop.run_until_complete(main())
        else:
            raise