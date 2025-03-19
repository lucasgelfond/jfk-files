import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv
import requests

# Load environment variables and initialize Supabase client
load_dotenv()
supabase: Client = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_KEY')
)

IS_PRODUCTION = not os.getenv('IS_DEV', 'false').lower() == 'true'
BASE_URL ="https://anythingllm-production-047a.up.railway.app"
ANYTHING_LLM_AUTH = os.getenv('ANYTHING_LLM_AUTHORIZATION')

def upload_pending_files():
    # Get records that haven't been uploaded to AnythingLLM
    records = supabase.table('record')\
        .select('*')\
        .is_('in_anything_llm', 'null')\
        .execute()

    if not records.data:
        print("No pending files to upload")
        return

    ocr_dir = Path("ocr-text")
    
    for record in records.data:
        record_number = record['record_number']
        filename = f"{record_number.replace('.pdf', '')}"
        file_path = ocr_dir / f"{filename}.txt"
        
        if not file_path.exists():
            print(f"File not found for {record_number}, skipping...")
            continue
            
        print(f"Uploading {filename} to AnythingLLM...")
        
        try:
            # Prepare the file upload
            files = {
                'file': (filename, open(file_path, 'rb'), 'text/plain')
            }
            
            # Make the upload request
            response = requests.post(
                f"{BASE_URL}/api/v1/document/upload",
                files=files,
                headers={
                    'Authorization': f'Bearer {ANYTHING_LLM_AUTH}'
                }
            )
            
            if response.status_code == 200:
                # Update the database to mark as uploaded
                supabase.table('record')\
                    .update({'in_anything_llm': True})\
                    .eq('id', record['id'])\
                    .execute()
                print(f"Successfully uploaded {filename}")
            else:
                print(f"Failed to upload {filename}: {response.status_code}")
                print(response.json())
                
        except Exception as e:
            print(f"Error uploading {filename}: {str(e)}")

if __name__ == "__main__":
    upload_pending_files()
