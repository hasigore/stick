import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd
import os

class Stick:
    def __init__(self, ticker_id):
        self.ticker_id = ticker_id
        self.ticker = yf.Ticker(ticker_id)
        self.ticker_info = self.ticker.info


    def get_price_on_date(self, date_str):
        date = datetime.strptime(date_str, "%Y-%m-%d")
        next_day_str = (date + timedelta(days=1)).strftime("%Y-%m-%d")
        hist = self.ticker.history(start=date_str, end=next_day_str)
        if hist.empty:
            raise ValueError(f"No trading data available for {self.ticker_id} on {date_str}")
        
        return hist['Close'].iloc[0]


    def get_euro_to_usd_rate_on_date(self, date_str):
        date = datetime.strptime(date_str, "%Y-%m-%d")
        eur_usd_ticker = yf.Ticker("EURUSD=X")
        next_day_str = (date + timedelta(days=1)).strftime("%Y-%m-%d")
        eur_usd_history = eur_usd_ticker.history(start=date_str, end=next_day_str)
        if eur_usd_history.empty:
            raise ValueError("No data for EURUSD=X")
        euro_to_usd_rate_on_date = float(eur_usd_history['Close'].iloc[0])
        return euro_to_usd_rate_on_date
    

    def get_usd_to_euro_rate_on_date(self, date_str):
        return 1.0 / self.get_euro_to_usd_rate_on_date(date_str)


    def get_company_name(self):
         return self.ticker_info.get("longName") or self.ticker_info.get("shortName") or "Unknown"
    

    def get_currency(self):
        return self.ticker_info.get('currency', 'Unknown')


def myprint(output_filpath, *args, **kwargs):
    print(*args, **kwargs)
    with open(output_filpath, "a") as f:
        print(*args, file=f, **kwargs)


def clear_output_file(output_filpath):
    with open(output_filpath, "w") as f:
        pass


def days_between_dates(date1_str, date2_str):
    date1 = datetime.strptime(date1_str, "%Y-%m-%d")
    date2 = datetime.strptime(date2_str, "%Y-%m-%d")
    days_between = (date2 - date1).days
    return days_between


def profit_update(stock_filepath, sell_date_str, existing_ticker_ids):
    try:
        ticker_ids = []
        ticker_ids = _profit_update(stock_filepath, sell_date_str, existing_ticker_ids)
        return ticker_ids
    except Exception as e:
        print(f"Error processing {stock_filepath} for date {sell_date_str}: {e}")


def _profit_update(stock_filepath, sell_date_str, existing_ticker_ids):
    stock_filename = os.path.splitext(os.path.basename(stock_filepath))[0]
    stock_file_folder = os.path.dirname(stock_filepath)
    stock_base_folder = os.path.dirname(stock_file_folder)
    print(f"Stock base folder: {stock_base_folder}")
    
    report_path = os.path.join(stock_base_folder, "reports")
    report_path = os.path.join(report_path, stock_filename)
    
    os.makedirs(report_path, exist_ok=True)
    
    report_filename = f"investment-report-{sell_date_str}.txt"
    report_filepath = os.path.join(report_path, report_filename)
    print(f"Generating report: {report_filepath}")

    investment_table  = pd.read_csv(stock_filepath, sep=";", comment="#")
    total_invested_amount_in_euro = 0.0
    total_profit_in_usd = 0.0
    total_invested_amount_in_usd = 0.0
    total_percentage_increased = 0.0

    clear_output_file(report_filepath)

    usd_to_euro_rate_on_sell_date = 0.0
    
    stock_count = 0
    performances = []
    for i, row in investment_table.iterrows():
        try:
            ticker_id = row["ticker_id"]
            if not ticker_id:
                raise ValueError(f"Missing ticker_id in row {i}.")

            existing_ticker_ids = add_unique_key(existing_ticker_ids, ticker_id)
            
            buy_date_str = row["buy_date"]
            if not buy_date_str:
                raise ValueError(f"Missing buy_date for ticker {ticker_id} in row {i}.")
            
            invested_amount_in_euro = float(row["investment_eur"])
            if pd.isna(invested_amount_in_euro):
                raise ValueError(f"Missing investment_eur for ticker {ticker_id} in row {i}.")
            
            stock = Stick(ticker_id)
            
            euro_to_usd_rate_on_buy_date = stock.get_euro_to_usd_rate_on_date(date_str=buy_date_str)
            usd_to_euro_rate_on_sell_date = stock.get_usd_to_euro_rate_on_date(date_str=sell_date_str)

            total_invested_amount_in_euro = total_invested_amount_in_euro + invested_amount_in_euro
            invested_amount_in_usd = invested_amount_in_euro * euro_to_usd_rate_on_buy_date
            total_invested_amount_in_usd = total_invested_amount_in_usd + invested_amount_in_usd
        
            company_name = stock.get_company_name()
            buy_stock_price = stock.get_price_on_date(buy_date_str)
            sell_stock_price = stock.get_price_on_date(sell_date_str)

            stock_currency = stock.get_currency()
            if stock_currency != 'USD':
                raise ValueError(f"Unsupported currency {stock_currency} for ticker {ticker_id}. Only USD is supported.")

            sell_amount_in_usd = invested_amount_in_usd * sell_stock_price / buy_stock_price
        
            profit_in_usd = sell_amount_in_usd - invested_amount_in_usd
            total_profit_in_usd = total_profit_in_usd + profit_in_usd

            increased_percentage_of_stock = (sell_stock_price / buy_stock_price - 1.0) * 100.0
            performances.append((ticker_id, increased_percentage_of_stock))
            total_percentage_increased = total_percentage_increased + increased_percentage_of_stock
            myprint(report_filepath, f"Ticker: {ticker_id}, Company: \"{company_name}\", Currency: {stock_currency}, euro_to_usd_rate_on_buy_date: {euro_to_usd_rate_on_buy_date:.2f}, buy_stock_price: {buy_stock_price:.2f}, sell_stock_price: {sell_stock_price:.2f}, Increased Percentage: {increased_percentage_of_stock:.0f}%, Profit: {profit_in_usd:.0f}$")
            stock_count = stock_count + 1
        
        except Exception as e:
            myprint(report_filepath,  f"{e}")
            continue

    sorted_perf = sorted(performances, key=lambda x: x[1], reverse=True)
    best_3 = sorted_perf[:3]
    worst_3 = sorted_perf[-3:]
    best_str = ", ".join(f"{ticker}({change:+.1f}%)" for ticker, change in best_3)
    worst_str = ", ".join(f"{ticker}({change:+.1f}%)" for ticker, change in worst_3)

    days = days_between_dates(buy_date_str, sell_date_str)
    myprint(report_filepath, f"\nTotal number of stocks: {stock_count}")
    myprint(report_filepath, f"Best performers: {best_str}")
    myprint(report_filepath, f"Worst performers: {worst_str}")
    myprint(report_filepath, f"Total invested: {total_invested_amount_in_usd:.0f}$ ({total_invested_amount_in_euro:.0f}€)")
    myprint(report_filepath, f"Total average percentage: {(total_percentage_increased / stock_count):.2f}%")
    total_worth_today_in_usd = total_invested_amount_in_usd + total_profit_in_usd
    total_workth_today_in_euro = total_worth_today_in_usd * usd_to_euro_rate_on_sell_date
    myprint(report_filepath, f"Total Investments today: {total_worth_today_in_usd:.0f}$ ({total_workth_today_in_euro:.0f}€)")
    total_profit_in_euro = total_profit_in_usd * usd_to_euro_rate_on_sell_date
    myprint(report_filepath, f"\nTotal profit in {days} days: {total_profit_in_usd:.0f}$ ({total_profit_in_euro:.0f}€)")
    return existing_ticker_ids


def add_unique_keys(existing_keys, new_keys):
    return_keys = []
    existing_set = set(existing_keys)
    new_set = set(new_keys)
    
    duplicates = existing_set.intersection(new_set)
    if duplicates:
        raise ValueError(f"Duplicate keys found: {duplicates}")
    
    return_keys.extend(existing_keys)
    return_keys.extend(new_keys)
    return return_keys


def add_unique_key(existing_keys, new_key):
    return_keys = []
    existing_set = set(existing_keys)
    new_set = set([new_key])
    
    duplicates = existing_set.intersection(new_set)
    if duplicates:
        raise ValueError(f"Duplicate keys found: {duplicates}")
    
    return_keys.extend(existing_keys)
    return_keys.append(new_key)
    return return_keys


# Main script to generate stock investment report
now = datetime.now()
#date_today_str = now.strftime("%Y-%m-%d")
date_yesterday_str = (now - timedelta(days=1)).strftime("%Y-%m-%d")

existing_ticker_ids = []

stock_filepaths_filepath = "//chaos.informatik.uni-rostock.de/~/ntfolders/My Documents/privat/stocks/stock-files.txt"
with open(stock_filepaths_filepath, "r") as stock_filepaths_file:
    
    for line in stock_filepaths_file:
        if not line:
            continue

        stock_filepath = line.strip()  # Removes newline and spaces

        if line.startswith("#") or not os.path.exists(stock_filepath):
            continue

        print(f"Processing Stockfile: {stock_filepath}")
        
        existing_ticker_ids = profit_update(stock_filepath=stock_filepath, sell_date_str=date_yesterday_str, existing_ticker_ids=existing_ticker_ids)