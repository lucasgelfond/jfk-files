import os
from pathlib import Path
from supabase import create_client, Client
from dotenv import load_dotenv
import requests
import time

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
    records = supabase.table('record')\
        .select('*')\
        .is_('in_anything_llm', 'null')\
        .execute()

    if not records.data:
        return

    ocr_dir = Path("ocr-text")
    
    for record in records.data:
        record_number = record['record_number']
        filename = f"{record_number.replace('.pdf', '')}"
        file_path = ocr_dir / f"{filename}.txt"
        
        if not file_path.exists():
            continue
            
        try:
            files = {
                'file': (filename, open(file_path, 'rb'), 'text/plain')
            }
            
            upload_response = requests.post(
                f"{BASE_URL}/api/v1/document/upload",
                files=files,
                headers={
                    'Authorization': f'Bearer {ANYTHING_LLM_AUTH}'
                }
            )
            if upload_response.status_code == 200:
                try:
                    upload_result = upload_response.json()
                    document = upload_result['documents'][0]
                    document_path = f"custom-documents/{document['id']}.json"
                except (ValueError, KeyError, IndexError):
                    continue
                
                update_payload = {
                    "adds": [document_path],
                    "deletes": []
                }
                
                embeddings_response = requests.post(
                    f"{BASE_URL}/api/v1/workspace/jfk/update-embeddings",
                    json=update_payload,
                    headers={
                        'Authorization': f'Bearer {ANYTHING_LLM_AUTH}',
                        'Content-Type': 'application/json'
                    }
                )
                
                if embeddings_response.status_code == 200:
                    supabase.table('record')\
                        .update({'in_anything_llm': True})\
                        .eq('id', record['id'])\
                        .execute()
                    print(f"Successfully uploaded and embedded {filename}")
                    time.sleep(10)
                else:
                    print(f"Failed to upload and embed {filename}")
            else:
                print(f"Failed to upload and embed {filename}")
                
        except Exception as e:
            print(f"Failed to upload and embed {filename}")

if __name__ == "__main__":
    upload_pending_files()
