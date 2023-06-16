import os
import re
import json

# Configure these vars
# Set to your log folder wherever it exists
INPUT_PATH = 'CHANGE ME'
OUTPUT_PATH = 'output'

# Don't need to change any other vars
DEBUG = 0

class Item:
    def __init__(self, item_name, count, price, date, date_fr, hour, minute, day, month, year, store_name):
        self.item_name = item_name
        self.count = int(count)
        self.price = int(price.replace(",", ""))
        self.date = date
        self.date_fr = date_fr
        self.hour = int(hour)
        self.minute = int(minute)
        self.day = int(day)
        self.month = int(month)
        self.year = int(year)
        self.price_per_count = float(self.price / self.count)
        self.store_name = store_name
        self.key = f"{item_name}{count}{price}{date_fr}"
    
    def __str__(self):
        return f"{self.count} x {self.item_name} sold for {self.price} gold ({self.price_per_count} gold per count), at {self.date_fr}"

# Create dictionary to hold all items seen
items_dict = {}

# Set path to folder containing files
path = INPUT_PATH
store_name = ''

# Iterate over all files ending in .txt in the folder
for filename in os.listdir(path):
    if filename.endswith(".txt"):
        with open(os.path.join(path, filename), "r", encoding="utf-8", errors='ignore') as file:
            for line in file:
                # Search for shop info. Use it until we see another valid shop name.
                shop_regex = r"^.*(?=: \[Talk\] This is a record of this shop's most recent sales, after applicable settlement taxes)"
                shop_matches = re.findall(shop_regex, line)
                if shop_matches:
                    store_name = shop_matches[0] or store_name

                # Search for item info
                item_regex = r"(\d+) x (.+) sold for ([\d,]+) gold, at ([\w\s:]+)\."
                item_matches = re.findall(item_regex, line)

                # Don't record items without a valid shop name
                if not store_name:
                    continue

                # Iterate over matches and add to items_dict
                for match in item_matches:
                    count = match[0]
                    item_name = match[1]
                    price = match[2]
                    date_fr = match[3]

                    date_pattern = r"(\d+):(\d+) on Day (\d+) Month (\d+) (\d+) AR"
                    date_match = re.match(date_pattern, date_fr)
    
                    if date_match:
                        hour = date_match.group(1) or 0
                        minute = date_match.group(2) or 0
                        day = date_match.group(3) or 0
                        month = date_match.group(4) or 0
                        year = date_match.group(5) or 0

                    # Ignore dates before Kai started working for Myon
                    if int(year) < 179:
                        continue

                    date = f"{year}-{month}-{day}"
                    item = Item(item_name, count, price, date, date_fr, hour, minute, day, month, year, store_name)

                    if item.key not in items_dict:
                        items_dict[item.key] = item

# Write items to JSON file
output_file_path = os.path.join(OUTPUT_PATH, 'sales.json')
with open(output_file_path, 'w') as output_file:
    json.dump([item.__dict__ for item in items_dict.values()], output_file, indent=2)
