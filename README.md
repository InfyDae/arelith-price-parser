# arelith-price-parser
Parses out price data from Arelith shops for customers and sales data for shop owners.

## parse.py
Set the `INPUT_PATH` variable to your log folder, then run `parse.py` to read all your log files for price data. Data is written to `/output` or wherever you configure it.

Subsequent runs will only process new files and add them to the output file in `/output`.

## parse_sales.py
Set the `INPUT_PATH` variable to your log folder, then run `parse_sales.py` to read all shop owner sales logs. Data is written to `/output` or wherever you configure it.

Subsequent runs will process _all_ files and add them to the output Json filr in `/output`.