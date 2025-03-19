import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables and initialize Supabase client
load_dotenv()
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

def save_concatenated_pages():
    """
    Fetch all records and their pages from Supabase,
    concatenate page contents in order, and save to files
    """
    # Create output directory if it doesn't exist
    output_dir = Path("ocr-text")
    output_dir.mkdir(exist_ok=True)
    
    # Get all records
    records = supabase.table('record').select('*').execute()
    
    for record in records.data:
        record_id = record['id']
        record_number = record['record_number']
        # Strip .pdf from filename for output
        output_filename = record_number.replace('.pdf', '') if record_number else str(record_id)
        output_path = output_dir / f"{output_filename}.txt"
        
        # Skip if output file already exists
        if output_path.exists():
            print(f"✓ {record_number}: Output file already exists")
            continue
            
        # Get count of all pages in database for this record
        pages = supabase.table('page')\
            .select('*')\
            .eq('parent_record_id', record_id)\
            .execute()
            
        db_page_count = len(pages.data)
        
        # Update record record if num_pages is None
        if record['num_pages'] is None:
            supabase.table('record')\
                .update({'num_pages': db_page_count})\
                .eq('id', record_id)\
                .execute()
            print(f"Updated {record_number} with correct page count: {db_page_count}")
        # Skip only if page counts don't match and num_pages is not None
        elif db_page_count != record['num_pages']:
            print(f"Skipping {record_number}: Have {db_page_count} pages, expected {record['num_pages']}")
            continue
            
        # Get all non-error pages for this record, ordered by page number
        valid_pages = supabase.table('page')\
            .select('*')\
            .eq('parent_record_id', record_id)\
            .eq('error', False)\
            .order('page_number')\
            .execute()
            
        if not valid_pages.data:
            print(f"No valid pages found for record {record_number}")
            continue
            
        # Concatenate page contents in order
        full_text = ""
        for page in valid_pages.data:
            # Remove ```text annotations if present
            cleaned_text = page['ocr_result'].replace('```text', '') if page['ocr_result'] else ''
            full_text += cleaned_text + "\n"
            
        # Save to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(full_text)
            
        print(f"Saved concatenated text for {record_number}")

if __name__ == "__main__":
    save_concatenated_pages()
