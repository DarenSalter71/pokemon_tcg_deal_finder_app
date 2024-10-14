from concurrent.futures import ThreadPoolExecutor
import time
import mysql.connector
from selenium import webdriver
import asyncio
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import sshtunnel
import MySQLdb

class Value:
    def __init__(self):
        self.name = ""
        self.set = None
        self.ungraded = None
        self.psa9 = None
        self.psa10 = None
        self.card_id = None

async def fetch_all_values(urls):
    # Use ThreadPoolExecutor to run multiple fetches in parallel
    with ThreadPoolExecutor(max_workers=12) as executor:
        loop = asyncio.get_event_loop()
        # Run all tasks concurrently using asyncio and ThreadPoolExecutor
        tasks = [loop.run_in_executor(executor, fetch_values, url) for url in urls]
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
    SCROLL_PAUSE_TIME = 1
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument('--ignore-certificate-errors')
    chrome_options.add_argument('--ignore-ssl-errors')
    chrome_options.add_argument('--log-level=3')
    # Optional: Disable images and JavaScript if not necessary
    chrome_options.add_argument("--disable-images")
    #chrome_options.add_argument("--disable-javascript")
  #  chrome_options.add_argument("--window-size=600,400")
    chrome_options.add_argument("--window-position=-6000,-4000")
    #chrome_options.add_argument("--remote-debugging-port=9222")
    chrome_options.page_load_strategy = 'eager'
    #chrome_options.add_argument("--window-size=1024,768")
    browser = None
    for i in range(3):
        try:
            browser = webdriver.Chrome(options=chrome_options)
            time.sleep(1)
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
    max_items = 9999999
    lines = browser.page_source.split("\n")
    for i in range(800, 900):
        if i > len(lines) - 1: break
        line = lines[i]
        if 'items' in line and '<span class="phone-landscape-hidden">' in browser.page_source:
            # print(line)
            max_items = int(line.split("/")[1].split("<")[0].strip())
            #print(line)
            break
    last_time = time.time()
    while True:
        items_count = len(browser.page_source.split("<td class=\"title\" title="))
        if items_count >= max_items:
            print("escaped")
            break
        cur_len = len(browser.page_source)
        if cur_len == last_len:
            if time.time() - last_time > 5: break
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
        time.sleep(SCROLL_PAUSE_TIME)
    source = browser.page_source
    browser.close()
    browser.quit()
    return source

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
                break
        if 'booster box' in name.lower():
            value.card_id = 'booster box'
        elif 'booster pack' in name.lower():
            value.card_id = 'booster pack'
        if len(value.name.split(" ")) >= 2:
            values.append(value)
    return values

async def scrape_values():
    values = []
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
    i = 0
    for line in lines:
        set_name = line.strip().replace("Pokemon ", "")
        if set_name in excluded_sets: continue
        set_names.append(set_name)
        #if i >= 0: break
        i += 1
   # set_names = ['fusion strike','paradox rift']
  #  set_names = ['fusion strike']
    values = await get_set_values(set_names)
    write_values_to_db_local(values)
    write_values_to_db_remote(values)
    #print("Got", len(values),"values")
    duration = time.time() - start_time
    print("total cards:", len(values))
    print(f"Execution time: {duration:.2f} seconds")

def write_values_to_db_remote(values):
    file = 'sql_login_pa.json'
    with open(file, 'r') as config_file:
        config = json.load(config_file)
    with open('ssh_config.json', 'r') as config_file:
        ssh_config = json.load(config_file)

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
            db=config['database']
        )
        print(connection)
        # Create a cursor object to execute SQL commands
        cursor = connection.cursor()
        drop_table_query = 'DROP TABLE IF EXISTS card_values;'
        cursor.execute(drop_table_query)
        # Create a table
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS card_values (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100),
            set_name VARCHAR(100),
            ungraded_price FLOAT,
            psa9_price FLOAT,
            psa10_price FLOAT,
            card_id VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        '''
        cursor.execute(create_table_query)
        connection.ping(True)
        i = 0
        batch_size = 500  # You can set this to the desired batch size
        batch_data = []  # This will hold the data for the current batch
        i = 0  # Initialize a counter

        for value in values:
            i += 1
            if i % 50 == 0:
                print(i, "/", len(values))

            # Prepare the data as a tuple
            data = (
                value.name,
                value.set,
                value.ungraded,
                value.psa9,
                value.psa10,
                value.card_id
            )

            # Append the current row's data to the batch
            batch_data.append(data)

            # If we have enough data for a batch, execute the insert
            if len(batch_data) == batch_size:
                # Create the insert query with placeholders
                insert_query = '''
                INSERT INTO card_values (name, set_name, ungraded_price, psa9_price, psa10_price, card_id)
                VALUES (%s, %s, %s, %s, %s, %s);
                '''
                # Execute the batch insert
                cursor.executemany(insert_query, batch_data)
                batch_data.clear()  # Clear the batch for the next set of data
                connection.commit()
        # Check for any remaining data that didn't make a full batch
        if batch_data:
            insert_query = '''
                            INSERT INTO card_values (name, set_name, ungraded_price, psa9_price, psa10_price, card_id)
                            VALUES (%s, %s, %s, %s, %s, %s);
                            '''
            cursor.executemany(insert_query, batch_data)  # Insert remaining data
            connection.commit()
    #connection.commit()
    #connection.commit()
    cursor.close()
    connection.close()

def write_values_to_db_local(values):
    with open('sql_login.json', 'r') as config_file:
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
    drop_table_query = 'DROP TABLE IF EXISTS card_values;'
    cursor.execute(drop_table_query)
    # Create a table
    create_table_query = '''
    CREATE TABLE IF NOT EXISTS card_values (
        id INT AUTO_INCREMENT PRIMARY KEY,
        name VARCHAR(100),
        set_name VARCHAR(100),
        ungraded_price FLOAT,
        psa9_price FLOAT,
        psa10_price FLOAT,
        card_id VARCHAR(100),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    '''
    cursor.execute(create_table_query)
    i = 0
    for value in values:
        i += 1
        if i % 100 == 0: print(i,"/",len(values))
        # Create the insert query with placeholders
        insert_query = '''
        INSERT INTO card_values (name, set_name, ungraded_price, psa9_price, psa10_price, card_id)
        VALUES (%s, %s, %s, %s, %s, %s);
        '''
        # Prepare the data as a tuple
        data = (
            value.name,
            value.set,
            value.ungraded,
            value.psa9,
            value.psa10,
            value.card_id
        )

        #print(insert_query, data)
        # Execute the query with the data
        cursor.execute(insert_query, data)
        #print(cursor.rowcount)
    connection.commit()
    cursor.close()
    connection.close()


async def main():
    await scrape_values()
    '''
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
    #await get_all_pages('UK' , ['fusion strike'], 1)
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
    '''

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