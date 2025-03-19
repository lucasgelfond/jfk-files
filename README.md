Broad notes about this repo:

![demo](https://github.com/user-attachments/assets/44299cda-8bf0-4fa0-8c76-2262cf56d735)


- the `frontend/` directory is a standard Svelte webapp with (fairly) self-explanatory structure
- the `processing/` directory contains all of the Python scripts I used for processing. `scrape-and-download` got the files from the National Archives, `gemini-page-ocr` was to upload the images and OCR them, `make-pages` gets me .txt files well-suited for RAG, and `upload-pages-to-anything-llm` uploads them. The other files are just helpers.
- the `supabase/` directory contains several edge functions I used separate from the backend to do embeddings and hybrid search
- the `backend/` directory simply wraps an AnythingLLM instance on Railway to not leak keys to the configuration. This is admittedly not my proudest work of engineering because of how much latency it adds, but there are no IAM roles for AnythingLLM's API and thus I can't do this straight on the client safely. If I had more time I'd make a bunch of changes on their server and nuke most of the APIs but - need to ship! 

Feel free to open issues / ask questions / leave PRs!
