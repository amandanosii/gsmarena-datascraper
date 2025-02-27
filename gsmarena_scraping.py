import csv
import time
from pathlib import Path
import os
import random

import requests
import pandas as pd
from bs4 import BeautifulSoup
from rich import print


class Gsmarena:

    def __init__(self, input_csv_path):
        self.url = "https://www.gsmarena.com/"
        self.new_folder_name = "GSMArenaDataset"
        self.absolute_path = Path.cwd() / self.new_folder_name
        self.features = [
            "Brand",
            "Model Name",
            #  ,"Model Image"
        ]

        self.target_brands = self.load_target_brands(input_csv_path)
        # Track existing devices to avoid duplicates
        self.existing_devices = self.load_existing_devices()

    def load_target_brands(self, csv_path):
        try:
            df = pd.read_csv(csv_path)

            if not all(col in df.columns for col in ["Brand"]):
                raise ValueError("Input CSV must contain 'Brand' column")

            brands = []
            for _, row in df.iterrows():
                brand = row["Brand"].strip().lower()
                brands.append(brand)

            return brands
        except Exception as e:
            print(f"Error loading target brands: {e}")
            exit(1)

    def load_existing_devices(self):
        """Load already scraped devices to avoid duplicates"""
        existing_devices = {}

        # Create the dataset directory if it doesn't exist
        if not self.absolute_path.exists():
            return existing_devices

        # Check all CSV files in the dataset directory
        for csv_file in self.absolute_path.glob("*.csv"):
            brand_name = csv_file.stem.lower()
            try:
                df = pd.read_csv(csv_file)
                if "Model Name" in df.columns:
                    # Create a dictionary with brand as key and list of models as values
                    if brand_name not in existing_devices:
                        existing_devices[brand_name] = []

                    # Add all models to the list
                    for model in df["Model Name"]:
                        existing_devices[brand_name].append(model.strip())

                    print(f"Loaded {len(df)} existing devices for {brand_name}")
            except Exception as e:
                print(f"Error loading existing devices from {csv_file}: {e}")

        return existing_devices

    def crawl_html_page(self, sub_url):
        url = self.url + sub_url
        header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        time.sleep(5)

        # Handling the connection error of the url.
        try:
            page = requests.get(url, timeout=5, headers=header)

            # if we got rate limited, sleep for a while
            if page.status_code == 429:
                print("Rate limited, sleeping for 30 seconds")
                time.sleep(30)
                self.crawl_html_page(sub_url)

            soup = BeautifulSoup(page.text, "html.parser")
            return soup
        except Exception as e:
            print(f"Error fetching page {url}")
            return None

    def crawl_phone_brands(self):
        """Get only the brands we're interested in from our input file"""
        phones_brands = []
        soup = self.crawl_html_page("makers.php3")
        if not soup:
            return phones_brands

        table = soup.find_all("table")[0]
        table_a = table.find_all("a")

        for a in table_a:
            brand_name = a.contents[0]

            # Only include brands that are in our target list
            if str(brand_name).lower() in self.target_brands:
                temp = [
                    a["href"].split("-")[0],
                    brand_name,
                    a["href"],
                ]
                phones_brands.append(temp)

        return phones_brands

    def crawl_phones_models(self, phone_brand_link, brand_name):
        """Crawl all models pages for a brand and filter out models we already have"""
        links = []
        model_links = {}  # Dictionary to store model name -> link mapping
        nav_link = []

        soup = self.crawl_html_page(phone_brand_link)
        if not soup:
            return links

        nav_data = soup.find(class_="nav-pages")
        if not nav_data:
            nav_link.append(phone_brand_link)
        else:
            nav_link = nav_data.find_all("a")
            nav_link = [link["href"] for link in nav_link]
            nav_link.append(phone_brand_link)
            nav_link.insert(0, nav_link.pop())

        # Collect all model links and names
        for link in nav_link:
            soup = self.crawl_html_page(link)
            if not soup:
                continue

            data = soup.find(class_="section-body")
            if data:
                for line1 in data.find_all("li"):
                    a_tag = line1.find("a")
                    if a_tag:
                        model_link = a_tag["href"]
                        # Extract model name from the listing
                        model_name_elem = line1.find("span")
                        if model_name_elem:
                            model_name = model_name_elem.text.strip()
                            # Check if we already have this model
                            brand_key = brand_name.lower()
                            if (
                                brand_key in self.existing_devices
                                and model_name in self.existing_devices[brand_key]
                            ):
                                print(f"Skipping already existing model: {model_name}")
                                continue
                            links.append(model_link)

        return links

    def crawl_phones_models_specification(self, link, phone_brand):
        """Same as original, crawl the specs for a specific phone"""
        phone_data = {}
        soup = self.crawl_html_page(link)
        if not soup:
            return phone_data

        model_name = soup.find(class_="specs-phone-name-title").text
        model_img_html = soup.find(class_="specs-photo-main")
        model_img = model_img_html.find("img")["src"] if model_img_html else ""

        phone_data.update({"Brand": phone_brand})
        phone_data.update({"Model Name": model_name})
        # phone_data.update({"Model Image": model_img})

        for data1 in range(len(soup.find_all("table"))):
            table = soup.find_all("table")[data1]
            for line in table.find_all("tr"):
                temp = []
                for l in line.find_all("td"):
                    text = l.getText().strip().replace("\n", "")
                    temp.append(text)

                if not temp:
                    continue
                else:
                    if "price" in str(temp[0]).lower():
                        self.features.append(temp[0])
                        phone_data.update({temp[0]: temp[1]})

        return phone_data

    def create_folder(self):
        """Create output folder if it doesn't exist"""
        if not self.absolute_path.exists():
            self.absolute_path.mkdir()
            print(f"Creating {self.new_folder_name} folder...")
            print("Folder created.")
        else:
            print(f"{self.new_folder_name} directory already exists")

    def save_specification_to_file(self):
        """Main function to save specifications, writes each device immediately after scraping"""
        phone_brands = self.crawl_phone_brands()
        self.create_folder()

        # Process each brand in our list
        for brand in phone_brands:
            brand_name = brand[1]
            brand_key = str(brand[0]).lower()
            output_file = self.absolute_path / f"{str(brand[0]).title()}.csv"

            print(f"Working on {brand_name} brand.")

            # Get new models for this brand (filtering out ones we already have)
            all_links = self.crawl_phones_models(brand[2], brand_name)
            if not all_links:
                print(f"No new models found for {brand_name}")
                continue

            # Check if output file exists to append or create
            file_exists = output_file.exists()

            # Create/append file and write header if needed
            if not file_exists:
                with open(output_file, 'w', encoding='utf-8', newline='') as file:
                    dict_writer = csv.DictWriter(file, fieldnames=self.features)
                    dict_writer.writeheader()

            # Process each model
            for i, link in enumerate(all_links, 1):
                print(f"Processing model {i}/{len(all_links)}: {link}")
                datum = self.crawl_phones_models_specification(link, brand_name)

                if datum:
                    # Check again if we already have this model
                    model_name = datum.get("Model Name", "")
                    if (
                        brand_key in self.existing_devices
                        and model_name in self.existing_devices[brand_key]
                    ):
                        print(f"Skipping duplicate model: {model_name}")
                        continue

                    # Clean data
                    datum = {
                        k: v.replace("\n", " ").replace("\r", " ")
                        for k, v in datum.items()
                    }

                    # Immediately write this device to the CSV file
                    with open(output_file, 'a', encoding='utf-8', newline='') as file:
                        dict_writer = csv.DictWriter(file, fieldnames=self.features)
                        dict_writer.writerow(datum)

                    # Add to existing devices to avoid duplicates in this run
                    if brand_key not in self.existing_devices:
                        self.existing_devices[brand_key] = []
                    self.existing_devices[brand_key].append(model_name)

                    print(f"Completed and saved {i}/{len(all_links)}")

            print(f"Completed processing {brand_name}")

def main():
    # Path to your input CSV file with brands to scrape
    input_csv_path = "target_devices.csv"

    try:
        scraper = Gsmarena(input_csv_path)
        scraper.save_specification_to_file()
        print("Scraping completed successfully!")
    except KeyboardInterrupt:
        print("Script stopped due to keyboard interruption.")
    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
