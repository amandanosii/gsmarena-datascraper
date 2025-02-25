import csv
import time
from pathlib import Path

import requests
import pandas as pd
from bs4 import BeautifulSoup
from rich import print


class Gsmarena:
    def __init__(self, input_csv_path):
        self.url = "https://www.gsmarena.com/"
        self.new_folder_name = "GSMArenaDataset"
        self.absolute_path = Path.cwd() / self.new_folder_name
        self.features = ["Brand", "Model Name", "Model Image"]

        # Load the input CSV with desired brands and models
        self.target_devices = self.load_target_devices(input_csv_path)

    def load_target_devices(self, csv_path):
        """Load the brands and models from CSV file"""
        try:
            df = pd.read_csv(csv_path)
            # Ensure the CSV has the required columns
            if not all(col in df.columns for col in ["Brand", "Model"]):
                raise ValueError("Input CSV must contain 'Brand' and 'Model' columns")

            # Create a dictionary with brands as keys and list of models as values
            devices = {}
            for _, row in df.iterrows():
                brand = row["Brand"].strip().lower()
                model = row["Model"].strip()

                if brand not in devices:
                    devices[brand] = []
                devices[brand].append(model)

            return devices
        except Exception as e:
            print(f"Error loading target devices: {e}")
            exit(1)

    def crawl_html_page(self, sub_url):
        url = self.url + sub_url
        header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        time.sleep(2)

        # Handling the connection error of the url.
        try:
            page = requests.get(url, timeout=5, headers=header)
            soup = BeautifulSoup(page.text, "html.parser")
            return soup
        except Exception as e:
            print(f"Error fetching page {url}: {e}")
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
            target_devices_keys = self.target_devices.keys()

            # Only include brands that are in our target list
            if str(brand_name).lower() in target_devices_keys:
                temp = [
                    a["href"].split("-")[0],
                    brand_name,
                    a["href"],
                ]
                phones_brands.append(temp)

        return phones_brands

    def crawl_phones_models(self, phone_brand_link):
        """Crawl all models pages for a brand"""
        links = []
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

        for link in nav_link:
            soup = self.crawl_html_page(link)
            if not soup:
                continue

            data = soup.find(class_="section-body")
            if data:
                for line1 in data.find_all("a"):
                    links.append(line1["href"])

        return links

    def filter_models_by_name(self, links, brand):
        """Filter device links to only those models we want"""
        filtered_links = []
        target_models = self.target_devices.get(brand.lower(), [])

        for link in links:
            # Extract model name from link
            model_name = str(link.split("-")[0].replace("_", " ")).upper()

            # Check if this model is in our target list (partial match)
            for target_model in target_models:
                if target_model.lower() in model_name.lower():
                    filtered_links.append(link)
                    print(f"Found matching model: {model_name}")
                    break

        return filtered_links

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
        phone_data.update({"Model Image": model_img})

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
                    # Handle duplicate keys
                    if temp[0] in phone_data.keys():
                        temp[0] = temp[0] + "_1"
                    if temp[0] not in self.features:
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
        """Main function to save specifications, modified to use our target list"""
        phone_brands = self.crawl_phone_brands()
        self.create_folder()

        # Process each brand in our list
        for brand in phone_brands:
            brand_name = brand[1]
            output_file = self.absolute_path / f"{brand[0].title()}.csv"

            print(f"Working on {brand_name} brand.")

            # Get all models for this brand
            all_links = self.crawl_phones_models(brand[2])

            # Filter to only the models we want
            filtered_links = self.filter_models_by_name(all_links, brand_name)

            if not filtered_links:
                print(f"No matching models found for {brand_name}")
                continue

            # Process each model
            phones_data = []
            for i, link in enumerate(filtered_links, 1):
                print(f"Processing model {i}/{len(filtered_links)}: {link}")
                datum = self.crawl_phones_models_specification(link, brand_name)

                if datum:
                    # Clean data
                    datum = {
                        k: v.replace("\n", " ").replace("\r", " ")
                        for k, v in datum.items()
                    }
                    phones_data.append(datum)
                    print(f"Completed {i}/{len(filtered_links)}")

            # Save to CSV
            if phones_data:
                with open(output_file, "w", encoding="utf-8") as file:
                    dict_writer = csv.DictWriter(file, fieldnames=self.features)
                    dict_writer.writeheader()
                    for dicti in phones_data:
                        dict_writer.writerow(dicti)
                print(f"Data saved to {output_file}")
            else:
                print(f"No data collected for {brand_name}")


def main():
    # Path to your input CSV file with brands and models to scrape
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
