import os
from PyPDF2 import PdfReader
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Supabase client setup
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Get all records from database
records = supabase.table("record").select("*").execute()

# Process each record
for record in records.data:
    # Skip if both record_number and num_pages are already set
    if record.get('record_number') and record.get('num_pages'):
        continue
        
    # Extract record number from pdf_link
    pdf_link = record['pdf_link']
    filename = pdf_link.split('/')[-1]
    record_number = filename.replace('.pdf', '')
    
    # Check if PDF exists locally
    filepath = os.path.join('downloaded-pdfs', filename)
    if not os.path.exists(filepath):
        print(f"Warning: PDF file not found for {filename}")
        continue
        
    try:
        # Get number of pages from PDF
        with open(filepath, 'rb') as f:
            pdf = PdfReader(f)
            num_pages = len(pdf.pages)
            
        # Update record in database
        updates = {}
        if not record.get('record_number'):
            updates['record_number'] = record_number
        if not record.get('num_pages'):
            updates['num_pages'] = num_pages
            
        if updates:
            supabase.table("record").update(updates).eq("id", record['id']).execute()
            print(f"Updated record {record_number}: {updates}")
            
    except Exception as e:
        print(f"Error processing {filename}: {str(e)}")

print("Finished updating records")

def fix_pdf_links():
    # Get records with null num_pages
    records = supabase.table("record").select("*").is_("num_pages", "null").execute()
    
    for record in records.data:
        pdf_link = record['pdf_link']
        if pdf_link.startswith('downloaded-pdfs/'):
            # Extract filename and construct correct URL
            filename = pdf_link.split('/')[-1]
            record_number = filename.replace('.pdf', '')
            correct_url = f"https://www.archives.gov/files/research/jfk/releases/2025/0318/{filename}"
            
            # Update record with correct PDF link
            supabase.table("record").update({
                "pdf_link": correct_url
            }).eq("id", record['id']).execute()
            
            print(f"Fixed PDF link for record {record_number}")

def fix_page_numbers():
    # Get pages with null page_number
    pages = supabase.table("page").select("*, record(pdf_link)").is_("page_number", "null").execute()
    
    for page in pages.data:
        try:
            # Get the parent record's pdf_link
            pdf_link = page['record']['pdf_link']
            if pdf_link:
                # Extract page number from the filename in downloaded-pages
                filename = pdf_link.split('/')[-1]
                record_number = filename.replace('.pdf', '')
                
                # Look up the file in downloaded-pages directory
                page_file = os.path.join('downloaded-pages', f"{record_number}-{page['id']}.jpg")
                if os.path.exists(page_file):
                    # Extract page number from filename
                    page_number = page_file.split('-')[-1].split('.')[0]
                    
                    # Update page with correct page number
                    supabase.table("page").update({
                        "page_number": page_number
                    }).eq("id", page['id']).execute()
                    
                    print(f"Fixed page number for page {page['id']} to {page_number}")
        except Exception as e:
            print(f"Error fixing page number for page {page['id']}: {str(e)}")

def fix_missing_records():
    # Get records that have pdf_link but no num_pages or record_number
    records = supabase.table("record").select("*").is_("num_pages", "null").execute()
    for record in records.data:
        pdf_link = record['pdf_link']
        if not pdf_link.startswith('https://www.archives.gov/files/research/jfk/releases/2025/0318/'):
            continue
            
        filename = pdf_link.split('/')[-1]
        record_number = filename.replace('.pdf', '')
        
        # Check if PDF exists locally
        filepath = os.path.join('downloaded-pdfs', filename)
        if not os.path.exists(filepath):
            print(f"Warning: PDF file not found for {filename}")
            continue
            
        try:
            # Get number of pages from PDF
            with open(filepath, 'rb') as f:
                pdf = PdfReader(f)
                num_pages = len(pdf.pages)
                
            # Update record in database
            updates = {}
            if not record.get('record_number'):
                updates['record_number'] = record_number
            if not record.get('num_pages'):
                updates['num_pages'] = num_pages
                
            if updates:
                supabase.table("record").update(updates).eq("id", record['id']).execute()
                print(f"Updated record {record_number}: {updates}")
                
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")

def fixLocalPDFLink():
    # Get all records that have downloaded-pdfs in their link
    records = supabase.table("record").select("*").like("pdf_link", "downloaded-pdfs%").execute()
    
    for record in records.data:
        try:
            # Extract filename from the local path
            filename = record['pdf_link'].split('/')[-1]
            
            # Construct the correct archives.gov URL
            correct_url = f"https://www.archives.gov/files/research/jfk/releases/2025/0318/{filename}"
            
            # Update the record with the correct URL
            supabase.table("record").update({
                "pdf_link": correct_url
            }).eq("id", record['id']).execute()
            
            print(f"Fixed local PDF link for record {record['id']}: {correct_url}")
            
        except Exception as e:
            print(f"Error fixing PDF link for record {record['id']}: {str(e)}")

fix_missing_records()
fixLocalPDFLink()
