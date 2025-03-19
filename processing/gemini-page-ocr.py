import google.generativeai as genai
from pathlib import Path
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from pdf2image import convert_from_path
import uuid
from typing import List, Tuple
import time
import PyPDF2
import cloudinary
import cloudinary.uploader
import tempfile
from concurrent.futures import ThreadPoolExecutor, Future
import threading
from PIL import Image

# Load environment variables
load_dotenv()

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'), 
    api_secret=os.getenv('CLOUDINARY_API_SECRET')
)

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

genai.configure(api_key=os.getenv('GOOGLE_API_KEY'))


# Initialize Gemini model
model = genai.GenerativeModel('gemini-2.0-flash')

def record_exists(pdf_link: str) -> bool:
    """Check if a record already exists in the database"""
    result = supabase.table('record').select('id').eq('pdf_link', pdf_link).execute()
    return len(result.data) > 0

def page_exists(record_id: str, page_num: int) -> bool:
    """Check if a page already exists in the database"""
    result = supabase.table('page').select('id').eq('parent_record_id', record_id).eq('page_number', page_num).execute()
    return len(result.data) > 0

def create_record(pdf_link: str) -> str:
    """Create a record and return its ID"""
    data = supabase.table('record').insert({
        'pdf_link': pdf_link
    }).execute()
    return data.data[0]['id']

def get_record_id(pdf_link: str) -> str:
    """Get record ID from database, or create if doesn't exist"""
    result = supabase.table('record').select('id').eq('pdf_link', pdf_link).execute()
    if result.data:
        return result.data[0]['id']
    return create_record(pdf_link)

def get_processed_pages(record_id: str) -> set:
    """Get set of page numbers already processed for this record"""
    result = supabase.table('page').select('page_number').eq('parent_record_id', record_id).execute()
    return {int(page['page_number']) for page in result.data}

def upload_page_image(image: Image, filename: str) -> dict:
    """Upload image to Cloudinary"""
    thread_name = threading.current_thread().name
    print(f"{thread_name}: Uploading {filename} to Cloudinary...")
    
    # Create a temporary file
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp_file:
        try:
            # Convert to RGB and save as JPEG with compression
            rgb_image = image.convert('RGB')
            rgb_image.save(tmp_file.name, 'JPEG', quality=85, optimize=True)
            
            # Check file size and reduce quality if needed
            quality = 85
            while os.path.getsize(tmp_file.name) > 10_000_000:  # 10MB limit
                quality = int(quality * 0.9)  # Reduce quality by 10%
                if quality < 20:  # Set minimum quality threshold
                    print(f"{thread_name}: Could not reduce file size enough")
                    return None
                rgb_image.save(tmp_file.name, 'JPEG', quality=quality, optimize=True)
            
            # Upload the temporary file to Cloudinary
            result = cloudinary.uploader.upload(tmp_file.name, public_id=filename)
            print(f"{thread_name}: Cloudinary upload result: {result}")
            
            return result
        finally:
            # Clean up
            rgb_image.close()
            # Remove temporary file
            if os.path.exists(tmp_file.name):
                os.unlink(tmp_file.name)

def process_page(image: object, page_num: int, pdf_link: str, record_id: str) -> Tuple[int, str]:
    """Process a single page with Gemini"""
    prompt = f"""
    Extract and transcribe the text content from this page.
    Maintain the original structure but do not add any annotations.
    """
    
    max_retries = 3
    retry_delay = 1
    
    for attempt in range(max_retries):
        try:
            response = model.generate_content([prompt, image])
            
            # Check if we got a valid response
            if not response.text:
                error_msg = "Copyright detection or empty response"
                return page_num, error_msg, None
            
            return page_num, None, response.text
            
        except Exception as e:
            if attempt == max_retries - 1:
                return page_num, str(e), None
            time.sleep(retry_delay * (attempt + 1))

def process_pdf(pdf_path: str):
    """Process a PDF file page by page and store results in Supabase"""
    print(f"Processing {pdf_path}")
    
    # Get or create record
    pdf_link = pdf_path
    record_id = get_record_id(pdf_link)
    print(f"Using record ID: {record_id}")
    
    # Check total pages
    with open(pdf_path, 'rb') as pdf_file:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        pdf_page_count = len(pdf_reader.pages)
    
    processed_pages = get_processed_pages(record_id)
    if len(processed_pages) == pdf_page_count:
        print(f"✓ {pdf_link}: All {pdf_page_count} pages already processed")
        return
    
    print(f"Total pages in PDF: {pdf_page_count}")
    print(f"Pages already in database: {len(processed_pages)}")
    
    def process_single_page(page_num):
        thread_name = threading.current_thread().name
        print(f"{thread_name}: Converting page {page_num}/{pdf_page_count}")
        
        try:
            # Convert single page with lower DPI and memory optimization
            images = convert_from_path(
                pdf_path,
                dpi=300,  
                first_page=page_num,
                last_page=page_num,
                thread_count=1,  
            )
            
            if not images:
                print(f"{thread_name}: Failed to convert page {page_num}")
                return
            
            # First do OCR processing
            page_num, error, ocr_result = process_page(images[0], page_num, pdf_link, record_id)
            
            # Then do Cloudinary upload
            cloudinary_result = None
            if not error:
                cloudinary_result = upload_page_image(
                    images[0], 
                    f"{Path(pdf_path).stem}_page_{page_num}"
                )
            
            # Insert all results in one go
            page_data = {
                'parent_record_id': record_id,
                'page_number': page_num,
            }
            
            if error:
                page_data.update({
                    'ocr_result': f"ERROR: {error}",
                    'error': True
                })
            else:
                page_data.update({
                    'ocr_result': ocr_result,
                    'error': False
                })
                
            if cloudinary_result:
                page_data['cloudinary'] = cloudinary_result
                
            supabase.table('page').insert(page_data).execute()
            
            if error:
                print(f"{thread_name}: Error processing page {page_num}: {error}")
            else:
                print(f"{thread_name}: Successfully processed page {page_num}")
            
            # Clear the image from memory immediately
            images[0].close()
            del images
            
            # Force garbage collection
            import gc
            gc.collect()
            
        except Exception as e:
            print(f"{thread_name}: Error processing page {page_num}: {str(e)}")
            # Force garbage collection on error too
            gc.collect()
    
    # Get pages that need processing
    pages_to_process = [
        page_num for page_num in range(1, pdf_page_count + 1)
        if page_num not in processed_pages
    ]
    
    # Process pages with thread pool - increased max_workers since we're not doing concurrent operations per page
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(process_single_page, pages_to_process)
        
    print(f"Completed processing {pdf_link}")

def process_directory(directory: str = "downloaded-pdfs"):
    """Process all PDFs in a directory"""
    pdf_dir = Path(directory)
    if not pdf_dir.exists():
        print(f"Directory {directory} not found")
        return
    
    for pdf_file in sorted(pdf_dir.glob("*.pdf")):
        try:
            process_pdf(str(pdf_file))
            # Force garbage collection between PDFs
            import gc
            gc.collect()
        except Exception as e:
            print(f"Error processing PDF: {str(e)}")

if __name__ == "__main__":
    # Suppress MallocStackLogging warnings
    import sys
    import os
    
    # Redirect stderr to devnull for specific warnings
    stderr = sys.stderr
    devnull = open(os.devnull, 'w')
    sys.stderr = devnull
    
    # Make sure required environment variables are set:
    # GOOGLE_API_KEY, SUPABASE_URL, SUPABASE_KEY
    process_directory()
    
    # Restore stderr
    sys.stderr = stderr
    devnull.close()