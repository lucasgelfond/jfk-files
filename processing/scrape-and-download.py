import os
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import urljoin
from queue import Queue
from threading import Thread
from supabase import create_client, Client
from dotenv import load_dotenv
import time
from PyPDF2 import PdfReader

# Load environment variables from .env file
load_dotenv()

# Create downloaded-pdfs directory if it doesn't exist
if not os.path.exists('downloaded-pdfs'):
    os.makedirs('downloaded-pdfs')

# Initialize queue for URLs
url_queue = Queue()

# Set up headless Chrome driver
options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')
options.add_argument('--disable-gpu')
options.add_argument('--disable-software-rasterizer')
options.add_argument('--ignore-certificate-errors')
options.add_argument('--ignore-ssl-errors')
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# Create a driver pool
NUM_WORKERS = 3  # Number of parallel workers
drivers = []
try:
    for _ in range(NUM_WORKERS):
        drivers.append(webdriver.Chrome(options=options))
except Exception as e:
    print(f"Error initializing Chrome driver: {str(e)}")
    for d in drivers:
        d.quit()
    exit(1)

# Supabase client setup
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def process_url(driver, url, parent_page_num):
    try:
        print(f"Processing URL: {url}")
        
        # Extract record number from the URL
        filename = url.split('/')[-1]
        record_number = filename.replace('.pdf', '')
        
        # Check if the record already exists in the database
        existing_records = supabase.table("record").select("record_number").eq("record_number", record_number).execute()
        if existing_records.data:
            print(f"Record {record_number} already exists in the database. Skipping download.")
            return
        
        # Check if the PDF already exists in the downloaded-pdfs directory
        filepath = os.path.join('downloaded-pdfs', filename)
        
        if os.path.exists(filepath):
            print(f"File {filename} exists but not in database. Adding to database...")
            
        # Always try to download if not in database
        response = requests.get(url, stream=True)
        if response.status_code == 200:
            if not os.path.exists(filepath):
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                print(f"Downloaded: {filename}")
            
            # Get the number of pages in the PDF
            with open(filepath, 'rb') as f:
                pdf = PdfReader(f)
                num_pages = len(pdf.pages)
            
            # Save to Supabase
            data = {
                "record_number": record_number,
                "pdf_link": url,
                "result_page": parent_page_num,
                "parent_page_num": parent_page_num,
                "num_pages": num_pages
            }
            try:
                supabase.table("record").insert(data).execute()
                print(f"Added {record_number} to database")
            except Exception as e:
                print(f"Error adding to database: {str(e)}")
        else:
            print(f"Failed to download {url}: Status code {response.status_code}")
        
    except Exception as e:
        print(f"Error processing {url}: {str(e)}")

def process_page(driver, page_url, parent_page_num):
    driver.get(page_url)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Find all relevant links
    for tag in soup.find_all('a'):
        href = tag.get('href')
        if href and href.endswith('.pdf'):  # Only process URLs ending with '.pdf'
            full_url = urljoin(page_url, href)
            url_queue.put((full_url, parent_page_num))
            print(f"Added to queue: {full_url}")  # Debug logging

def process_files():
    main_url = 'https://www.archives.gov/research/jfk/release-2025'
    driver = webdriver.Chrome(options=options)
    driver.get(main_url)
    
    current_page_number = 1
    while True:
        try:
            # Wait for table to load
            table = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.ID, "DataTables_Table_0"))
            )
            
            # Find all PDF links in the current page and add to queue
            for link in driver.find_elements(By.TAG_NAME, "a"):
                href = link.get_attribute('href')
                if href and href.endswith('.pdf'):
                    url_queue.put((href, current_page_number))
                    print(f"Added to queue: {href}")
            
            # Wait for all downloads from this page to complete
            url_queue.join()
            
            # Try to find and click the next button
            next_button = driver.find_element(By.ID, "DataTables_Table_0_next")
            if "disabled" in next_button.get_attribute("class"):
                print("Reached the last page")
                break
                
            next_button.find_element(By.TAG_NAME, "a").click()
            time.sleep(2)  # Wait for page transition
            current_page_number += 1
            
        except Exception as e:
            print(f"Error processing page {current_page_number}: {str(e)}")
            break

    driver.quit()

def worker(driver_index):
    driver = drivers[driver_index]
    while True:
        item = url_queue.get()
        if item is None:
            break
        url, parent_page_num = item
        process_url(driver, url, parent_page_num)
        url_queue.task_done()
        # Reduced sleep time
        time.sleep(1)

# Start multiple worker threads
worker_threads = []
for i in range(NUM_WORKERS):
    thread = Thread(target=worker, args=(i,))
    thread.start()
    worker_threads.append(thread)

# Start processing files indefinitely
process_files()

# Add sentinel value for each worker
for _ in range(NUM_WORKERS):
    url_queue.put(None)

# Wait for all tasks to complete
url_queue.join()
for thread in worker_threads:
    thread.join()

# Clean up all drivers
for driver in drivers:
    driver.quit()
