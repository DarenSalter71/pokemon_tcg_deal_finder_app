import asyncio
from concurrent.futures import ThreadPoolExecutor
import requests
import time
import aiohttp
from selenium import webdriver
import asyncio
import sys
from bs4 import BeautifulSoup
import value_scraper

class Value:
    def __init__(self):
        self.name = ""
        self.set = None
        self.ungraded = None
        self.psa9 = None
        self.psa10 = None
        self.card_id = None

async def fetch(url, session):
    async with session.get(url) as response:
        return await response.text()

def get_card_id(title):
    for word in title.split(" "):
        if '/' in word or '#' in word:
            word = word.replace('#','')
            if '/' in word:
                word = word.split("/")[0]
            word = word.lstrip('0')
            return word
    return None

async def get_all_pages(region, set_names, num_pages, values_dict):
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
            count = get_listings(search_query, region, set_name, result, values_dict)
            tot_listings += count
            print("Total listings:", tot_listings)
            print("Page:", i + 1)

def get_listings(search, region, set_name, result, values_dict):
    soup = BeautifulSoup(result, 'lxml')
    tot_listings = 0
    title_images = {img_tag.get('alt'): img_tag['src'] for img_tag in soup.find_all('img') if 'https://i.ebayimg.com/images/g/' in img_tag['src']}
    item_title = ''
    item_link = ''
    item_image = ''
    item_price = ''
    item_postage = ''
    item_seller_info = ''
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
            if span_tag.get('class') == ['s-item__seller-info-text']:
                item_seller_info = text
            if span_tag.get('class') == ['s-item__shipping', 's-item__logisticsCost']:
                item_postage = text
            if span_tag.get('class') == ['s-item__space_bar']:
                if " to " in item_price or set_name.lower() not in item_title.lower():
                    continue
                item_image = title_images.get(item_title, 'None')
                for word in item_postage.split(" "):
                    if '£' in word or '$' in word:
                        item_postage = word
                        break
                if 'Free' in item_postage:
                    item_postage = 'Free'
                print("---")
                print('Title:', item_title)
                print('Set name:', set_name)
                print('Link:', item_link)
                print('Image:', item_image)
                print('Price:', item_price)
                print('Postage:', item_postage)
                print('Seller info:', item_seller_info)
                # get card id
                card_id = get_card_id(item_title)
                if card_id is None: continue
                if set_name not in values_dict: continue
                #print(set_name)
                print(card_id)
                if card_id not in values_dict[set_name]: continue
                value_info = values_dict[set_name][card_id]
                ungraded_price = value_info.ungraded
                print('Identified as:', value_info.name)
                print('Ungraded:', ungraded_price)
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
    #values = await get_all_values('fusion strike')
    #values = await get_all_values('paradox rift')
    #values = await get_all_values('team rocket')
    #values = await get_all_values('base set')
    #values = await get_all_values('astral radiance')
    #values = await get_set_values(['astral radiance','fusion strike', 'base set', 'team rocket', 'paradox rift',
    #'astral radiance','fusion strike', 'base set', 'team rocket', 'paradox rift'])
    values = await value_scraper.get_set_values(['fusion strike'])

    values_dict = {}
    for value in values:
    #    print(value.set, value.name)
        if value.set not in values_dict:
            values_dict[value.set] = {}
        if value.card_id is None: continue
        values_dict[value.set.lower()][value.card_id] = value
   # print(values_dict['fusion strike']['28'])
   # sys.exit()
    start_time = time.time()
    await get_all_pages('UK' , ['fusion strike'], 10, values_dict)
    duration = time.time() - start_time
    #await get_all_pages('UK', ['fusion strike'], 1, values_dict)
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