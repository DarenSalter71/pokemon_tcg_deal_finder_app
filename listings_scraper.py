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
import mysql.connector
import json
import re
import sshtunnel
import MySQLdb

class Listing:
    def __init__(self):
        self.title = ''
        self.set = None
        self.link = None
        self.price = None
        self.valuation = None
        self.price_gbp = None
        self.seller_info = None
        self.identified_as = None
        self.price_diff_percent = None
        self.price_diff_raw = None
        self.postage = None
        self.auction_type = None
        self.total_price = None

class Value:
    def __init__(self):
        self.name = ""
        self.set = None
        self.ungraded = None
        self.psa9 = None
        self.psa10 = None
        self.card_id = None

GBP_USD = 1.31


def strip_unsupported_characters(input_string):
    # Remove any character that is not a valid ASCII character
    return re.sub(r'[^\x00-\x7F]+', '', input_string)

async def fetch(url, session):
    async with session.get(url) as response:
        return await response.text()

def get_card_id(title):
    if 'booster pack' in title: return 'booster pack'
    if 'booster box' in title: return 'booster box'
    for word in title.split(" "):
        if '/' in word or '#' in word:
            word = word.replace('#','')
            if '/' in word:
                word = word.split("/")[0]
            word = word.lstrip('0')
            return word
    return None

async def get_all_listings(region, set_names, num_pages, values_dict, full_set_names):
    urls = []
    url_batches = []
    already_scraped = []
    i = 0
    for set_name in set_names:
        search = 'pokemon tcg ' + set_name
        for page_num in range(1, num_pages + 1):
            i += 1
            site = 'ebay.com'
            if region == 'UK': site = 'www.ebay.co.uk'
            if region == 'CA': site = 'ebay.ca'
            search_query = search.replace(" ", "+")
            url = 'https://' + site + '/sch/i.html?_nkw=' + search_query + '&_dmd=1&_ipg=240&_pgn=' + str(page_num)
            urls.append((set_name, url))
            if i % 15 == 0:
                url_batches.append(urls)
                urls = list([])
    if len(urls) > 0:
        url_batches.append(urls)
    all_listings = []
    async with aiohttp.ClientSession() as session:
        j = 0
        tot_listings = 0
        #all_listings = []
        for urls in url_batches:
            j += 1
            results = await asyncio.gather(*[fetch(url, session) for _, url in urls])
            print(len(results), len(urls))
            #sys.exit()
            for i, result in enumerate(results):
                url = urls[i][1]
                set_name = urls[i][0]
                if set_name not in values_dict: continue
                search_query = 'pokemon tcg ' + set_name
                count, already_scraped, new_listings = get_listings(search_query, region, set_name, result, values_dict[set_name], already_scraped, full_set_names)
                for listing in new_listings:
                    all_listings.append(listing)
                tot_listings += count
                print("Total listings:", tot_listings)
                print("Page:", i + 1)
                print("Progress:", j, "/", len(url_batches))
         #       print(urls)
    return all_listings

def is_card_match(title, card_name):
    bracket_text = ''
    if "[" in card_name and "]":
        bracket_text = card_name.split("[")[1].split("]")[0]
    pokemon_text = card_name
    if "[" in card_name:
        pokemon_text = card_name.split("[")[0]
    if "#" in pokemon_text:
        pokemon_text = pokemon_text.split("#")[0]
    pokemon_text = pokemon_text.strip()
    if pokemon_text.lower() in title.lower() and bracket_text.lower() in title.lower():
        return True
    return False

def get_listings(search, region, set_name, result, set_values, already_scraped, full_set_names):
    soup = BeautifulSoup(result, 'lxml')
    all_listings = []
    tot_listings = 0
    title_images = {img_tag.get('alt'): img_tag['src'] for img_tag in soup.find_all('img') if 'https://i.ebayimg.com/images/g/' in img_tag['src']}
    item_title = ''
    item_link = ''
    item_image = ''
    item_price = ''
    item_postage = ''
    item_seller_info = ''
    item_auction_type = ''
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
            if span_tag.get('class') == ['s-item__dynamic', 's-item__formatBuyItNow']:
                item_auction_type = 'Buy it now'
            if span_tag.get('class') == ['s-item__dynamic', 's-item__formatBestOfferEnabled']:
                item_auction_type = 'Auction'
            if span_tag.get('class') == ['s-item__bids', 's-item__bidCount']:
                item_auction_type = 'Auction'
            if ' bids' in text:
                item_auction_type = 'Auction'
            if span_tag.get('class') == ['s-item__space_bar']:
                if " to " in item_price or set_name.lower() not in item_title.lower():
                    continue
                item_image = title_images.get(item_title, 'None')
                for word in item_postage.split(" "):
                    if '£' in word or '$' in word:
                        item_postage = word
                        break
                item_postage = item_postage.replace("+",'')
                if 'Free' in item_postage:
                    item_postage = 'Free'
                do_continue = False
                for cur_set in full_set_names:
                    if cur_set.lower() in item_title.lower() and cur_set.lower() != set_name.lower(): do_continue = True # avoid reprints in other sets
                banned_words = ['custom', 'opened', 'poster', 'sticker', 'german', 'japanese', 'korean', 'chinese', 'spanish', 'open', 'empty']
                for word in banned_words:
                    if word in item_title.lower().split(" "): do_continue = True
                if do_continue: continue
                if 'not card' in item_title.lower(): continue
                if "no card" in item_title.lower(): continue
                print("---")
                print('Title:', item_title)
                print('Type:', item_auction_type)
                print('Set name:', set_name)
                print('Link:', item_link)
                print('Image:', item_image)
                print('Price:', item_price)
                print('Postage:', item_postage)
                print('Seller info:', item_seller_info)
                if item_link in already_scraped:
                    continue
                already_scraped.append(item_link)
                # get card id
                card_id = get_card_id(item_title)
                if card_id is None: continue
                if card_id not in set_values: continue
                value_info = set_values[card_id]
                if len(value_info) == 1:
                    value_info = value_info[0]
                    is_match = is_card_match(item_title, value_info.name)
                    if not is_match: continue
                else:
                    matches = []
                    for info in value_info:
                        is_match = is_card_match(item_title,info.name)
                        if is_match:
                            matches.append(info)
                    if len(matches) > 1:
                        biggest_name = 0
                        winner = None
                        for match in matches:
                            if len(match.name) > biggest_name:
                                winner = match
                                biggest_name = len(match.name)
                        value_info = winner
                    else:
                        if len(matches) == 1: value_info = matches[0]
                        else:
                            continue # doesn't match card in values list
                ungraded_price = value_info.ungraded
                print('Identified as:', value_info.name)
                print('Ungraded:', ungraded_price)
                orig_price = item_price
                item_price = item_price.replace("£", "").replace("$", "").replace(",", "")
                item_price = float(item_price)
                if "£" in orig_price:
                    item_price *= GBP_USD
                    print("adjusted price")

                item_price = float(item_price)
                listing = Listing()
                listing.title = item_title
                listing.set = set_name
                if value_info.ungraded is None or value_info.ungraded == 'None': value_info.ungraded = 0
                listing.valuation = float(value_info.ungraded)
                listing.link = item_link
                listing.image = item_image
                postage = item_postage.replace("£", "").replace("$", "").replace(",", "").replace("+","")
                if item_postage == 'Free' or item_postage == 'Postage not specified':
                    postage = 0
                if isinstance(postage, str):
                    postage = float(0)
                postage = float(postage)
                listing.postage = postage
                item_price = float(item_price)
                listing.price = float(item_price)
                listing.identified_as = value_info.name
                listing.seller_info = item_seller_info
                listing.total_price = postage + item_price
                listing.price_diff_raw = float(value_info.ungraded) - float(item_price + postage)
                listing.price_diff_percent = round((listing.price_diff_raw / (item_price + postage)) * 100,1)
                listing.auction_type = item_auction_type
                all_listings.append(listing)
                tot_listings += 1

    print(set_name + ":", tot_listings)
    return tot_listings, already_scraped, all_listings

def get_values_from_db():
    with open('sql_login.json', 'r') as config_file:
        config = json.load(config_file)

    connection = mysql.connector.connect(
        host=config['host'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        auth_plugin=config['auth_plugin']  # Specify the authentication plugin
    )

    cursor = connection.cursor()

    # Define the query
    query = "SELECT * FROM card_values"

    # Execute the query with parameters
    cursor.execute(query)

    # Fetch all results
    results = cursor.fetchall()
    values_dict = {}
    # Print the results
    for row in results:
        card_id = row[6]
        if card_id is None: continue
        set_name = row[2]
        if set_name.lower() not in values_dict:
            values_dict[set_name.lower()] = {}
        if card_id not in values_dict[set_name.lower()]:
            values_dict[set_name.lower()][card_id] = []
        value = Value()
        value.name = row[1]
        value.set = row[2]
        value.card_id = card_id
        value.ungraded = row[3]
        value.psa9 = row[4]
        value.psa10 = row[5]
        values_dict[set_name.lower()][card_id].append(value)
    return values_dict

def write_listings_to_db_remote(listings):
    file = 'sql_login_pa.json'
    with open(file, 'r') as config_file:
        config = json.load(config_file)
    with open('ssh_config.json', 'r') as config_file:
        ssh_config = json.load(config_file)
    retries = 3
    for attempt in range(retries):
        try:
            with sshtunnel.SSHTunnelForwarder(
                    ('ssh.pythonanywhere.com'),
                    ssh_username=ssh_config['user'],
                    ssh_password=ssh_config['password'],
                    remote_bind_address=(
                    ssh_config['host'], 3306)
            ) as tunnel:
                connection = MySQLdb.connect(
                    user=config['user'],
                    passwd=config['password'],
                    host='127.0.0.1', port=tunnel.local_bind_port,
                    db=config['database'],
                )
                '''
                # Establish a connection to the MySQL server
                connection = mysql.connector.connect(
                    host=config['host'],
                    user=config['user'],
                    password=config['password'],
                    database=config['database'],
                    auth_plugin=config['auth_plugin']  # Specify the authentication plugin
                )
                '''
                # Create a cursor object to execute SQL commands
                cursor = connection.cursor()
                drop_table_query = 'DROP TABLE IF EXISTS listings;'
                cursor.execute(drop_table_query)

                create_table_query = '''
                CREATE TABLE IF NOT EXISTS listings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(100),
                    set_name VARCHAR(100),
                    valuation FLOAT,
                    price FLOAT,
                    image VARCHAR(100),
                    postage FLOAT,
                    link VARCHAR(100),
                    seller_info VARCHAR(100),
                    price_diff_raw FLOAT,
                    price_diff_percent FLOAT,
                    identified_as VARCHAR(100),
                    auction_type VARCHAR(100),
                    total_price FLOAT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                '''
                cursor.execute(create_table_query)
                i = 0
                batch_size = 500
                batch_data = []
                for listing in listings:
                    i += 1
                    if i % 50 == 0: print(i)
                    insert_query = '''
                    INSERT INTO listings (title, set_name, valuation, price, image, postage, link, seller_info, price_diff_raw, price_diff_percent, identified_as, auction_type,
                    total_price)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    '''
                    # Prepare the data as a tuple
                    data = (
                        strip_unsupported_characters(listing.title),
                        listing.set,
                        listing.valuation,
                        listing.price,
                        listing.image,
                        listing.postage,
                        listing.link,
                        listing.seller_info,
                        listing.price_diff_raw,
                        listing.price_diff_percent,
                        listing.identified_as,
                        listing.auction_type,
                        listing.total_price
                    )
                    # Append the current row's data to the batch
                    batch_data.append(data)

                    # If we have enough data for a batch, execute the insert
                    if len(batch_data) == batch_size:
                        cursor.executemany(insert_query, batch_data)
                        batch_data.clear()  # Clear the batch for the next set of data
                        connection.commit()
                    # print(insert_query, data)
                    # Execute the query with the data
                    #cursor.execute(insert_query, data)
                if batch_data:
                    cursor.executemany(insert_query, batch_data)  # Insert remaining data
                    connection.commit()
                connection.commit()
                cursor.close()
                connection.close()
        except:
            wait_time = 2 ** attempt
            print("Exception occured, trying again in", wait_time, "seconds")
            time.sleep(wait_time)


def write_listings_to_db_local(listings):
    file = 'sql_login.json'
    with open(file, 'r') as config_file:
        config = json.load(config_file)

        # Establish a connection to the MySQL server
        connection = mysql.connector.connect(
            host=config['host'],
            user=config['user'],
            password=config['password'],
            database=config['database'],
            auth_plugin=config['auth_plugin']  # Specify the authentication plugin
        )
        # Create a cursor object to execute SQL commands
        cursor = connection.cursor()
        drop_table_query = 'DROP TABLE IF EXISTS listings;'
        cursor.execute(drop_table_query)

        create_table_query = '''
        CREATE TABLE IF NOT EXISTS listings (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(100),
            set_name VARCHAR(100),
            valuation FLOAT,
            price FLOAT,
            image VARCHAR(100),
            postage FLOAT,
            link VARCHAR(100),
            seller_info VARCHAR(100),
            price_diff_raw FLOAT,
            price_diff_percent FLOAT,
            identified_as VARCHAR(100),
            auction_type VARCHAR(100),
            total_price FLOAT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        '''
        cursor.execute(create_table_query)
        i = 0
        for listing in listings:
            i += 1
            if i % 50 == 0: print(i)
            insert_query = '''
            INSERT INTO listings (title, set_name, valuation, price, image, postage, link, seller_info, price_diff_raw, price_diff_percent, identified_as, auction_type,
            total_price)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
            '''
            # Prepare the data as a tuple
            data = (
                strip_unsupported_characters(listing.title),
                listing.set,
                listing.valuation,
                listing.price,
                listing.image,
                listing.postage,
                listing.link,
                listing.seller_info,
                listing.price_diff_raw,
                listing.price_diff_percent,
                listing.identified_as,
                listing.auction_type,
                listing.total_price
            )

            # print(insert_query, data)
            # Execute the query with the data
            cursor.execute(insert_query, data)
        connection.commit()
        cursor.close()
        connection.close()

async def scrape_listings():
    set_names = []
    excluded_sets = []
    with open('excluded_sets.txt', 'r') as f:
        lines = f.readlines()
    for line in lines:
        line = line.replace("\n", "")
        excluded_sets.append(line)
    with open('sets.txt', 'r') as f:
        lines = f.readlines()
    i = 0
    for line in lines:
        set_name = line.strip().replace("Pokemon ", "")
        if set_name in excluded_sets: continue
        i += 1
       # if i > 2: break
        set_names.append(set_name.lower())
    all_set_names = list(set_names)
    #set_names = ['pop series 5']
    values_dict = get_values_from_db()
    start_time = time.time()
    all_listings = await get_all_listings('UK', set_names, 10, values_dict, all_set_names)
    write_listings_to_db_local(all_listings)
    write_listings_to_db_remote(all_listings)
    print(len(all_listings))

async def main():
    start_time = time.time()
    await scrape_listings()
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