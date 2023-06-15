import os
from pathlib import Path
from datetime import datetime
from dateutil.relativedelta import relativedelta
import time as Time
import hashlib
import glob
import json
import re
import sys

# Configure these vars
# Set to your log folder wherever it exists
INPUT_PATH = 'CHANGE ME'
# Writes a separate file containing only price data for the last X months
RECENT_MONTHS = 3

# Don't need to change any other vars
DEBUG = 0
OUTPUT_PATH = 'output'
OUTPUT_FILE = 'prices.json'
READ_FILES_FILE = 'metadata/read_files.txt'

# Log parsing vars
CHAT_WINDOW_TEXT_PREFIX = "[CHAT WINDOW TEXT]"
SHOP_OWNER_IDENT = "'s shop''"
SHOP_ITEM_INDENT = "Do you want to buy the article "

# Metadata folder locations
METADATA_MERCHANT = 'metadata\merchant_list.json'
METADATA_MERCHANT_LOCATION = 'metadata\merchant_location_list.json'

# TODO: convert from IRL dates to approximate Arelith dates
DATE_ARELITH_EXAMPLE = "Day 12, Month 8 (Elasias (Highsun)) 176 AR. The time is currently 10:15"
DATE_IRL_EXAMPLE = "2022-05-25:09:40"

data = []
properties = ["date", "url", "type", "message"]

RE_TIME = re.compile("(\w{3} \w{3} \d{2} \d{2}:\d{2}:\d{2})")
RE_STORE_NAME = re.compile("[]] ([^:]*): Do you want to buy the article")
RE_STORE_OWNER = re.compile("[]] ([^:]*): ''(.*)'s shop''")
RE_ITEM_NAME = re.compile("Do you want to buy the article (.+) [(]Stack")
RE_STACK_SIZE = re.compile("Stack Size: (\d+)")
RE_PRICE = re.compile("for (\d+)?")

price_list_dict = {}
price_list = []
merchant_dict = {}
merchant_dict_parsed = {}
merchant_location_dict = {}
read_file_dict = {}

print(f'{datetime.now().strftime("%Y-%m-%d %H-%M-%S")} Starting ...')

def hash_str(input: str) -> int:
    return int(hashlib.sha1(input.encode("utf-8")).hexdigest(), 16) % (10 ** 8)

## Setup log metadata enrichers
# Setup harcoded merchant location list
try:
    with open(os.path.join(os.getcwd(), METADATA_MERCHANT)) as json_file:
        merchant_dict = json.load(json_file)

        if DEBUG: print(json.dumps(merchant_dict, indent = 4, sort_keys=True) )
except FileNotFoundError:
    print(f"File {METADATA_MERCHANT} not found. No hardcoded merchant data loaded.", file=sys.stderr)

# Setup generated merchant list
try:
    with open(os.path.join(os.getcwd(), METADATA_MERCHANT_LOCATION)) as json_file:
        merchant_location_dict = json.load(json_file)
    
        if DEBUG: print(json.dumps(merchant_location_dict, indent = 4, sort_keys=True) )
except FileNotFoundError:
    print(f"File {METADATA_MERCHANT_LOCATION} not found. No derived merchant list loaded.", file=sys.stderr)

# Setup file ignore list
if os.path.exists(os.path.join(os.getcwd(), READ_FILES_FILE)):
    with open(os.path.join(os.getcwd(), READ_FILES_FILE)) as json_file:
        for line in json_file:
            value = line.strip()
            read_file_dict[value] = True

        if DEBUG: print(json.dumps(read_file_dict, indent = 4, sort_keys=True) )

# Record the read file unless it's already been parsed
read_file = open(f"{READ_FILES_FILE}", "a")

## Read all input files out of /input
for filename in glob.glob(os.path.join(INPUT_PATH, '*.txt')):
   # 220310_2031.txt
   stripped_name = Path(filename).stem
   date = datetime.strptime(stripped_name, '%y%m%d_%H%M')
   item_count = 0

   # Skip files we've already read
   if stripped_name in read_file_dict:
        if DEBUG: print(f'Skipping {stripped_name}. Already read')
        continue

   with open(os.path.join(os.getcwd(), filename), 'r', encoding="utf8", errors='ignore') as file:
        for line in file.readlines():
            # Chat window text gets logged twice. Ignore the one without the prefix
            if CHAT_WINDOW_TEXT_PREFIX not in line: continue

            line = line.strip()
            line = re.sub(r'[^\x00-\x7F]','', line)

            if SHOP_OWNER_IDENT in line:
                store_owner = RE_STORE_OWNER.search(line)

                if store_owner: store_name = store_owner.group(1).strip()
                if store_owner: store_owner = store_owner.group(2).strip()

                if store_owner is None:
                    continue

                store = {
                    "shop_name": store_name,
                    "owner": store_owner,
                    "location": "",
                    "description": ""
                    }

                if store_name in merchant_location_dict:
                    store["location"]    = merchant_location_dict[store_name]["location"]
                    store["description"] = merchant_location_dict[store_name]["description"]

                if store_owner not in merchant_dict_parsed:
                    merchant_dict_parsed[store_name] = store

                continue

            if SHOP_ITEM_INDENT in line:       
                time = RE_TIME.search(line)
                store_name = RE_STORE_NAME.search(line)
                item_name = RE_ITEM_NAME.search(line)
                stack_size = RE_STACK_SIZE.search(line)
                price = RE_PRICE.search(line)
                owner = None
                location = None
                description = None
        
                if time: time = time.group(1).strip()
                if store_name: store_name = store_name.group(1).strip()
                if item_name: item_name = item_name.group(1).strip()
                if stack_size: stack_size = stack_size.group(1)
                if price: price = price.group(1)

                hash = hash_str(f"{date}{store_name}{item_name}{stack_size}{price}")

                if time != None:
                    time = f"{date.strftime('%Y')} {time}"
                    time = datetime.strptime(time, '%Y %a %b %d %H:%M:%S')
                    time = datetime.strftime(time, '%Y-%m-%dT%H:%M:%SZ')

                stack_size = int(stack_size) if stack_size else None
                price = int(price) if price else None
                price_per_item = None
                if price != None and stack_size != None:
                    price_per_item = int(price/stack_size)

                if store_name in merchant_dict:
                    merchant = merchant_dict[store_name]
                    owner = merchant["owner"]
                    location = merchant["location"] or None
                    description = merchant["description"]

                price_dict = {
                  "date": date.strftime("%Y-%m-%d"),
                  "time": time,
                  "time_unix": int(Time.mktime(date.timetuple())),
                  "stock": stack_size,
                  "price": price_per_item,
                  "item_name": item_name,
                  "store_name": store_name,
                  "owner": owner,
                  "location": location,
                  "description": description,
                  "hash": hash
                }

                key = item_name

                if key in price_list_dict:
                    duplicate_found = 0

                    for dict in price_list_dict[key]:
                        if dict["hash"] == price_dict["hash"]:
                            if DEBUG: print(f"Dupe found: {hash}. Skipping ...")
                            if DEBUG: print(hash)
                            duplicate_found = 1
                            break

                    if not duplicate_found:
                        price_list_dict[key].append(price_dict)
                        price_list.append(price_dict)
                else:
                    price_list_dict[key] = [price_dict]
                    price_list.append(price_dict)

                item_count += 1

   if item_count:
      if DEBUG: print(f"{item_count} item(s) found in log file '{filename}'")

   # Write the file as having been read
   read_file.writelines(f"{stripped_name}\n")

read_file.close()

# Read old files so we don't wipe out the old data
price_list_old = []
try:
    with open(os.path.join(os.getcwd(), f"{OUTPUT_FILE}")) as json_file:
        price_list_old = json.load(json_file)
except FileNotFoundError:
    print(f"File {OUTPUT_FILE} not found. No previous prices loaded.", file=sys.stderr)

merchant_dict_old = []
try:
    with open(os.path.join(os.getcwd(), f"{METADATA_MERCHANT}")) as json_file:
        merchant_dict_old = json.load(json_file)
except FileNotFoundError:
    print(f"File {METADATA_MERCHANT} not found. No merchants loaded.", file=sys.stderr)

# Combine the old dicts with the new
if(len(price_list) <= 0): price_list = []
if(len(price_list_old) <= 0): price_list_old = []
price_list = price_list + price_list_old

if(len(merchant_dict_parsed) <= 0): merchant_dict_parsed = {}
if(len(merchant_dict_old) <= 0): merchant_dict_old = {}
merchant_dict_parsed = merchant_dict_parsed | merchant_dict_old

# Grab only the most recent {RECENT_MONTHS} months of data
price_list_recent = []

for item in price_list:
    if datetime.strptime(item.get('date'), '%Y-%m-%d') >= (date.today() + relativedelta(months=-RECENT_MONTHS)):
        price_list_recent.append(item)

# Write out contents of all files
price_list_json = json.dumps(price_list, indent = 4, sort_keys=True)
price_list_recent_json = json.dumps(price_list_recent, indent = 4, sort_keys=True)
merchant_dict_json = json.dumps(merchant_dict_parsed, indent = 4, sort_keys=True)

if DEBUG: print(price_list)
if DEBUG: print(merchant_dict_json)

f = open(f"{OUTPUT_PATH}/{OUTPUT_FILE}", "w")
f.write(price_list_json)
f.close()

f = open(f"{OUTPUT_PATH}/prices_last_{RECENT_MONTHS}_months.json", "w")
f.write(price_list_recent_json)
f.close()

f = open(f"{OUTPUT_PATH}/merchant_list.json", "w")
f.write(merchant_dict_json)
f.close()
