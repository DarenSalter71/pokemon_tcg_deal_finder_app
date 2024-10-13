import mysql.connector
from datetime import datetime
import json
from footer import get_footer

intervals = (
    ('weeks', 604800),  # 60 * 60 * 24 * 7
    ('days', 86400),    # 60 * 60 * 24
    ('hours', 3600),    # 60 * 60
    ('minutes', 60),
    ('seconds', 1),
)

def display_time(seconds, granularity=2):
    result = []

    for name, count in intervals:
        value = seconds // count
        if value:
            seconds -= value * count
            if value == 1:
                name = name.rstrip('s')
            result.append("{} {}".format(int(value), name))
    return ', '.join(result[:granularity])


def deal_page(request):

    #default

    region_both_selected = False
    region_US_selected = True
    region_UK_selected = False

    search_region = request.args.get("region")
    if search_region == 'Both':
        region_both_selected = True
        region_UK_selected = False
        region_US_selected = False
    if search_region == 'US':
        region_both_selected = False
        region_UK_selected = False
        region_US_selected = True

    if search_region == 'UK':
        region_both_selected = False
        region_UK_selected = True
        region_US_selected = False

    #default

    auction_type_auction_selected = False
    auction_type_buyitnow_selected = True
    auction_type_both_selected = False

    search_auction_type = request.args.get("auction_type")
    if search_auction_type == 'Both':
        auction_type_auction_selected = False
        auction_type_buyitnow_selected = False
        auction_type_both_selected = True
    if search_auction_type == 'Buy it now':
        auction_type_auction_selected = False
        auction_type_buyitnow_selected = True
        auction_type_both_selected = False
    if search_auction_type == 'Auction':
        auction_type_auction_selected = True
        auction_type_buyitnow_selected = False
        auction_type_both_selected = False

    currency_usd_selected = True
    currency_gbp_selected = False
    search_currency = request.args.get("display_currency")
    if search_currency == 'USD':
        currency_usd_selected = True
    elif search_currency == 'GBP':
        currency_gbp_selected = True

    currency_gbp_selstring = ''
    currency_usd_selstring = ''

    region_UK_selstring = ''
    region_US_selstring = ''
    region_both_selstring = ''
    auction_type_auction_selstring = ''
    auction_type_buyitnow_selstring = ''
    auction_type_both_selstring = ''
    if region_US_selected:
        region_US_selstring = 'checked'
    elif region_UK_selected:
        region_UK_selstring = 'checked'
    elif region_both_selected:
        region_both_selstring = 'checked'
    if auction_type_buyitnow_selected:
        auction_type_buyitnow_selstring = 'checked'
    elif auction_type_auction_selected:
        auction_type_auction_selstring = 'checked'
    elif auction_type_both_selected:
        auction_type_both_selstring = 'checked'
    if currency_usd_selected:
        currency_usd_selstring = 'checked'
    if currency_gbp_selected:
        currency_gbp_selstring = 'checked'
    html = f'''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: Arial, sans-serif;
                font-size: 16px;
                margin: 20px;
            }}
            form {{

            }}
            label {{
                margin-top: 10px;
            }}
            .radio-group {{

            }}'''
    html += '''
                    table {
            width: 100%; /* Full width of the container */
            border-collapse: collapse; /* Merge borders of adjacent cells */
            margin-top: 20px; /* Space above the table */
        }

        th, td {
            border: 1px solid #ddd; /* Light gray border */
            padding: 12px; /* Padding for cells */
            text-align: left; /* Align text to the left */
        }

        th {
            background-color: #4CAF50; /* Green background for header */
            color: white; /* White text for header */
        }

        tr:nth-child(even) {
            background-color: #f2f2f2; /* Light gray for even rows */
        }

        tr:hover {
            background-color: #ddd; /* Light gray on hover */
        }

        caption {
            font-size: 1.5em; /* Larger font size for the caption */
            margin: 10px; /* Margin around the caption */
        }
        '''
    search_keywords = request.args.get("search_query")
    if search_keywords is None:
        search_keywords = ''
    search_sort = request.args.get("sort")

    html += f'''
        </style>
    </head>
    <body>
    <center>
    <h1>Jimmy's Pokemon Deal Finder</h1>
    <h2>Search</h2>
    <form action="/pokemondeals" method="GET">
        <input type="hidden" name="sort" value="{search_sort}">
        Keywords: <input type="text" name="search_query" placeholder="Enter search term" style="width: 350px" value="{search_keywords}">
        <div class="radio-group">
            <label>Region:</label>
            <label>
                <input type="radio" name="region" value="Both" {region_both_selstring}> Both
            </label>
            <label>
                <input type="radio" name="region" value="US" {region_US_selstring}> US (ebay.com)
            </label>
            <label>
                <input type="radio" name="region" value="UK" {region_UK_selstring}> UK (ebay.co.uk)
            </label>
        </div>
        <div class="radio-group" style="width:500px">
            <label>Auction type:</label>
            <label>
                <input type="radio" name="auction_type" value="Both" {auction_type_both_selstring}> Both
            </label>
            <label>
                <input type="radio" name="auction_type" value="Buy it now" {auction_type_buyitnow_selstring}> Buy it now
            </label>
            <label>
                <input type="radio" name="auction_type" value="Auction" {auction_type_auction_selstring}> Auction
            </label>
        </div>
        <div class="currency" style="width:500px">
            <label>Display currency:</label>
            <label>
                <input type="radio" name="display_currency" value="USD" {currency_usd_selstring}> $ USD
            </label>
            <label>
                <input type="radio" name="display_currency" value="GBP" {currency_gbp_selstring}> £ GBP
            </label>
        </div>
        <button type="submit" style="width:450px">Search</button>
    </form>
    '''

    # build search query

    search_region = request.args.get("region")
    valid_regions = ["Both", "US", "UK"]
    if search_region not in valid_regions:
        search_region = 'US'
    search_auction_type = request.args.get("auction_type")
    valid_values = ["Both", "Buy it now", "Auction"]
    if search_auction_type not in valid_values:
        search_auction_type = 'Buy it now'
    search_keywords = request.args.get("search_query")

    with open('/home/jimmyrustles/mysite/sql_login_pa.json', 'r') as config_file:
        config = json.load(config_file)

    connection = mysql.connector.connect(
        host=config['host'],
        user=config['user'],
        password=config['password'],
        database=config['database'],
        auth_plugin=config['auth_plugin']  # Specify the authentication plugin
    )
    cursor = connection.cursor()
    query = '''SELECT COUNT(*) AS total_rows FROM listings;'''
    cursor.execute(query)
    results = cursor.fetchall()
    tot_listings = 0
    for row in results:
        tot_listings = row[0]
    html += f'''
            <br>Total listings: {tot_listings:,}<br>
            '''
    query = '''SELECT COUNT(*) AS total_rows FROM listings WHERE valuation > total_price;'''
    cursor.execute(query)
    results = cursor.fetchall()
    tot_deals = 0
    for row in results:
        tot_deals = row[0]
    html += f'''
            <br>Potential deals (valuation > price + postage): {tot_deals:,}<br>
            '''

    # Define the query
    query = '''SELECT created_at FROM listings
            WHERE auction_type = 'Buy it now'
            ORDER BY price_diff_percent DESC LIMIT 1'''

    # Execute the query with parameters
    cursor.execute(query)

    # Fetch all results
    results = cursor.fetchall()
    created_at = results[0][0]
    past_time = datetime.strptime(str(created_at), "%Y-%m-%d %H:%M:%S")

    # Get current datetime
    current_time = datetime.now()

    # Calculate the duration in seconds
    duration_seconds = (current_time - past_time).total_seconds()
    html += f'''<br>Listings updated: {display_time(duration_seconds)} ago<br>'''

    html += '''
            <br>
            <a href="javascript:void(0)" class="toggleLink" onclick="toggleText()">Roadmap</a>

            <div id="toggleText" style="width: 400px; display: none; font-family: verdana; font-size:16px">
                <ul>
                    <li>Pages</li>
                    <li>Search improvements</li>
                    <ul>
                        <li>Search by keywords</li>
                        <li>Region (US/UK)</li>
                        <li>Auction type (Auction/Buy it now)</li>
                        <li>Search by Card ID and set name</li>
                    </ul>
                    <li>Display currency in £GBP or $USD</li>
                </ul>
            </div>

            <script>
                function toggleText() {
                    var textElement = document.getElementById("toggleText");
                    if (textElement.style.display === "none") {
                        textElement.style.display = "block"; // Show the text
                    } else {
                        textElement.style.display = "none"; // Hide the text
                    }
                }
            </script>
            '''# Start with the base query

    page_num = cur_page_num = request.args.get("page_num")
    if page_num is None:
        page_num = 1
    page_num = int(page_num)
    orig_page_num = page_num

    search_sort = request.args.get("sort")
    order_string = " ORDER BY price_diff_percent DESC"
    if search_sort == 'price_diff_percent_desc':
        order_string = " ORDER BY price_diff_percent DESC"
    if search_sort == 'price_diff_percent_asc':
        order_string = " ORDER BY price_diff_percent ASC"
    if search_sort == 'price_diff_raw_desc':
        order_string = " ORDER BY price_diff_raw DESC"
    if search_sort == 'price_diff_raw_asc':
        order_string = " ORDER BY price_diff_raw ASC"
    if search_sort == 'price_desc':
        order_string = " ORDER BY price DESC"
    if search_sort == 'price_asc':
        order_string = " ORDER BY price ASC"
    if search_sort == 'valuation_desc':
        order_string = " ORDER BY valuation DESC"
    if search_sort == 'valuation_asc':
        order_string = " ORDER BY valuation ASC"

    query = '''SELECT title, identified_as, set_name, price, valuation, auction_type, price_diff_percent, link, image, price_diff_raw, postage, region, seller_info FROM listings'''

    # List to store query conditions and parameters
    conditions = []
    params = []

    # Check if the search_region is not "Both" and add the region condition
    if search_region != "Both":
        conditions.append("region = %s")
        params.append(search_region)

    # Check if the search_auction_type is not "Both" and add the auction_type condition
    if search_auction_type != "Both":
        conditions.append("auction_type = %s")
        params.append(search_auction_type)
    if search_keywords is not None:
        for word in search_keywords.split(" "):
            conditions.append("LOWER(title) like %s")
            like_pattern = f"%{word.lower()}%"
            params.append(like_pattern)

    # If there are any conditions, add them to the query
    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    # Add the ORDER BY and LIMIT clauses
    query += order_string
    query += " LIMIT 1500 "
    query += " OFFSET " + str((page_num - 1) * 25)
    #html += '<b>' + query + '<b>'
    #return html
    #return html
    # Execute the query with the parameters
    cursor.execute(query, params)

    # Fetch all results
    results = cursor.fetchall()
    html += '<br><br>Page: '
    cur_page_num = request.args.get("page_num")
    if cur_page_num is None:
        cur_page_num = 1
    cur_page_num = int(cur_page_num)
    for page_num in range(50):
        if (page_num) * 25 > len(results) + 25 * orig_page_num - 25: break
        page_url = f'pokemondeals?search_query={search_keywords}&region={search_region}&auction_type={search_auction_type}&sort={search_sort}'
        page_url += '&page_num=' + str(page_num + 1)
        if page_num + 1 != cur_page_num:
            html += f'<a href="{page_url}">{page_num+1}</a> '
        else:
            html += f'[<a href="{page_url}">{page_num+1}</a>] '

    html += '<br>'

    if search_sort is None:
        search_sort = 'None'
    price_diff_percent_page_url = f'pokemondeals?search_query={search_keywords}&region={search_region}&auction_type={search_auction_type}&display_currency={search_currency}&sort=price_diff_percent_desc'
    if search_sort == 'price_diff_percent_desc':
        price_diff_percent_page_url = f'pokemondeals?search_query={search_keywords}&region={search_region}&auction_type={search_auction_type}&display_currency={search_currency}&sort=price_diff_percent_asc'
    price_diff_raw_page_url = f'pokemondeals?search_query={search_keywords}&region={search_region}&auction_type={search_auction_type}&display_currency={search_currency}&sort=price_diff_raw_desc'
    if search_sort == 'price_diff_raw_desc':
        price_diff_raw_page_url = f'pokemondeals?search_query={search_keywords}&region={search_region}&auction_type={search_auction_type}&display_currency={search_currency}&sort=price_diff_raw_asc'
    price_page_url = f'pokemondeals?search_query={search_keywords}&region={search_region}&auction_type={search_auction_type}&display_currency={search_currency}&sort=price_desc'
    if search_sort == 'price_desc':
        price_page_url = f'pokemondeals?search_query={search_keywords}&region={search_region}&auction_type={search_auction_type}&display_currency={search_currency}&sort=price_asc'
    valuation_page_url = f'pokemondeals?search_query={search_keywords}&region={search_region}&auction_type={search_auction_type}&display_currency={search_currency}&sort=valuation_desc'
    if search_sort == 'valuation_desc':
        valuation_page_url = f'pokemondeals?search_query={search_keywords}&region={search_region}&auction_type={search_auction_type}&display_currency={search_currency}&sort=valuation_asc'

    html += f'''
            <table border="1">
            <tr><td>Region</td><td>Image</td><td>Title</td><td>Identified as</td><td>Set</td><td><a href="{price_page_url}">Price</a></td><td><a href="{valuation_page_url}">Valuation</a></td><td>Auction type</td><td><a href="{price_diff_percent_page_url}">Price difference %</a></td><td><a href="{price_diff_raw_page_url}">Price difference raw</a></td></tr>
    '''
    results_limit = 25
    i = 1
    for row in results:
        if i >= results_limit: break
        i += 1
        title = row[0]
        identified_as = row[1]
        set_name = row[2].title()
        price = round(row[3],2)
        valuation = round(row[4],2)
        auction_type = row[5]
        price_difference_percent = round(row[6], 2)
        link = row[7]
        image = row[8]
        price_difference_raw = round(row[9],2)
        postage = round(row[10],2)
        region = row[11]
        seller_info = row[12]
        USD_GBP = 0.77
        currency_sign = '$'
        if search_currency == 'GBP':
            price = price * USD_GBP
            postage = postage * USD_GBP
            price_difference_raw *= USD_GBP
            valuation *= USD_GBP
            currency_sign = '£'
        cell_style = ''
        if price_difference_percent > 0:
            shade = (price_difference_percent / 250) * (255)
            if shade > 255: shade = 255
            if shade < 90: shade = 90
            shade = int(shade)
            hex_val = hex(shade)[2:]
            cell_style = f"style='background-color: #00{hex_val}00'"
        elif price_difference_percent < 0:
            cell_style = "style='background-color: red'"
        pc_link = 'pokemon-' + set_name.replace(" ", "-").lower() + "/" + identified_as.replace("#","").replace("[","").replace("]","").replace(" ","-").lower()
        pc_link = 'https://pricecharting.com/game/' + pc_link
        html += f'''
                <tr><td>{region}</td><td><img src="{image}" width="100"></td><td><a href="{link}">{title}</a><br><br>Seller: {seller_info}</td><td><a href="{pc_link}">{identified_as}</a></td><td>{set_name}</td><td>{currency_sign}{price:.2f} <br><br>({currency_sign}{postage:.2f} postage)<br><br>Total: {currency_sign}{postage+price:.2f}</td><td>{currency_sign}{valuation:.2f}</td><td>{auction_type}</td>
                <td {cell_style}>{price_difference_percent}%</td><td {cell_style}>{currency_sign}{price_difference_raw:.2f}</tr>
                '''
    html += '</table>'

    html += '<br><br>Page: '
    cur_page_num = request.args.get("page_num")
    if cur_page_num is None:
        cur_page_num = 1
    cur_page_num = int(cur_page_num)
    for page_num in range(50):
        if (page_num) * 25 > len(results) + 25 * orig_page_num - 25: break
        page_url = f'pokemondeals?search_query={search_keywords}&region={search_region}&auction_type={search_auction_type}&sort={search_sort}'
        page_url += '&page_num=' + str(page_num + 1)
        if page_num + 1 != cur_page_num:
            html += f'<a href="{page_url}">{page_num+1}</a> '
        else:
            html += f'[<a href="{page_url}">{page_num+1}</a>] '

    html += get_footer()
    html += '</body></html>'
    return html