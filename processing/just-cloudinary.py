import os
from dotenv import load_dotenv
from supabase import create_client, Client
from pdf2image import convert_from_path
import cloudinary
import cloudinary.uploader
import tempfile
from pathlib import Path
from PIL import Image
from datetime import datetime

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

def upload_page_image(image: Image, filename: str) -> dict:
    """Upload image to Cloudinary"""
    print(f"Uploading {filename} to Cloudinary...")
    
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
                    print(f"Could not reduce file size enough")
                    return None
                rgb_image.save(tmp_file.name, 'JPEG', quality=quality, optimize=True)
            
            # Upload the temporary file to Cloudinary
            result = cloudinary.uploader.upload(tmp_file.name, public_id=filename)
            print(f"Cloudinary upload result: {result}")
            
            return result
        finally:
            rgb_image.close()
            if os.path.exists(tmp_file.name):
                os.unlink(tmp_file.name)

def process_error_pages():
    """Process pages with errors"""
    # Get all pages with errors
    result = supabase.table('page').select(
        'id',
        'page_number',
        'parent_record_id',
        'record:record(pdf_link)'
    ).eq('error', True).execute()

    if not result.data:
        print("No error pages found")
        return

    for page in result.data:
        try:
            # Extract filename from pdf_link
            pdf_link = page['record']['pdf_link']
            filename = pdf_link.split('/')[-1]
            pdf_path = f"downloaded-pdfs/{filename}"

            if not os.path.exists(pdf_path):
                print(f"PDF file not found: {pdf_path}")
                continue

            print(f"Processing page {page['page_number']} from {filename}")

            # Convert single page
            images = convert_from_path(
                pdf_path,
                dpi=300,
                first_page=page['page_number'],
                last_page=page['page_number'],
                thread_count=1
            )

            if not images:
                print(f"Failed to convert page {page['page_number']}")
                continue

            # Upload to Cloudinary
            cloudinary_result = upload_page_image(
                images[0],
                f"{Path(pdf_path).stem}_page_{page['page_number']}"
            )

            if cloudinary_result:
                # Update page record with cloudinary data and updated_at timestamp
                supabase.table('page').update({
                    'cloudinary': cloudinary_result,
                    'updated_at': datetime.utcnow().isoformat()
                }).eq('id', page['id']).execute()
                print(f"Successfully uploaded page {page['page_number']}")

            # Cleanup
            images[0].close()
            del images

        except Exception as e:
            print(f"Error processing page {page['page_number']}: {str(e)}")

        # Force garbage collection
        import gc
        gc.collect()

if __name__ == "__main__":
    process_error_pages()

