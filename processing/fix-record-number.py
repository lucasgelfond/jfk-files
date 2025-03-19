import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Supabase client setup
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

def fix_record_number():
    # Get all records
    records = supabase.table("record").select("*").is_("record_number", "null").execute()
    
    for record in records.data:
        try:
            pdf_link = record['pdf_link']
            
            # Skip if not a local PDF link
            if not pdf_link.startswith('downloaded-pdfs/'):
                continue
                
            # Extract filename and record number
            filename = pdf_link.split('/')[-1]
            record_number = filename.replace('.pdf', '')
            
            # Construct correct archives.gov URL
            correct_url = f"https://www.archives.gov/files/research/jfk/releases/2025/0318/{filename}"
            
            # Update record with correct URL and record number
            supabase.table("record").update({
                "pdf_link": correct_url,
                "record_number": record_number
            }).eq("id", record['id']).execute()
            
            print(f"Fixed record {record['id']}: {record_number} -> {correct_url}")
            
        except Exception as e:
            print(f"Error fixing record {record['id']}: {str(e)}")

if __name__ == "__main__":
    fix_record_number()
