import { createClient } from '@supabase/supabase-js';
import { pipeline } from '@huggingface/transformers';
import { createWorker } from 'tesseract.js';
import * as dotenv from 'dotenv';

// Load environment variables
dotenv.config();

// Initialize Supabase client
const supabaseUrl = process.env.SUPABASE_URL;
const supabaseKey = process.env.SUPABASE_KEY;
const supabase = createClient(supabaseUrl, supabaseKey);

async function processRow(row) {
	try {
		// Get full page data including cloudinary and ocr_result
		const { data: pageData, error: pageError } = await supabase
			.from('page')
			.select('cloudinary,ocr_result')
			.eq('id', row.id)
			.single();

		if (pageError) {
			throw new Error(`Error fetching page data: ${pageError.message}`);
		}

		// Skip if ocr_result doesn't start with ERROR
		if (!pageData.ocr_result?.startsWith('ERROR')) {
			console.log(`Skipping row ${row.id} - no ERROR in ocr_result`);
			return;
		}

		// Debug cloudinary object
		console.log('Cloudinary data:', pageData.cloudinary);

		// Skip if cloudinary is null
		if (!pageData.cloudinary) {
			console.log(`Skipping row ${row.id} - cloudinary is null`);
			return;
		}

		if (!pageData.cloudinary.secure_url) {
			throw new Error('Missing cloudinary secure_url');
		}

		// Initialize Tesseract worker - updated for newer Tesseract.js API
		const worker = await createWorker('eng');

		// Perform OCR on image
		console.log(`Processing OCR for row ${row.id}...`);
		const result = await worker.recognize(pageData.cloudinary.secure_url);
		const text = result.data.text;
		console.log('OCR Result:', text);

		// Initialize the embedding pipeline
		const classifier = await pipeline('feature-extraction', 'Supabase/gte-small', {
			dtype: 'fp32',
			device: 'cpu'
		});

		// Generate embedding
		const output = await classifier(text, {
			pooling: 'mean',
			normalize: true
		});
		const embedding = Array.from(output.data);
		console.log('Generated embedding:', embedding.slice(0, 5), '...');

		// Update row in Supabase
		const { data, error: updateError } = await supabase
			.from('page')
			.update({
				ocr_result: text,
				embedding: embedding,
				updated_at: new Date().toISOString(),
				error: false
			})
			.eq('id', row.id);

		console.log('Update response:', { data, error: updateError });

		if (updateError) {
			console.error('Update error details:', {
				message: updateError.message,
				details: updateError.details,
				hint: updateError.hint
			});
			throw updateError;
		}

		await worker.terminate();
		console.log(`Successfully processed row ${row.id}`);
	} catch (error) {
		console.error(`Error processing row ${row.id}:`, error);

		// Set error flag if processing failed
		const { data: flagData, error: flagError } = await supabase
			.from('page')
			.update({
				error: true,
				updated_at: new Date().toISOString()
			})
			.eq('id', row.id);

		console.log('Error flag update response:', { data: flagData, error: flagError });

		if (flagError) {
			console.error('Error setting error flag:', flagError);
		}
	}
}

async function getErrorRows() {
	const { data: errorRows, error } = await supabase
		.from('page')
		.select('*')
		.eq('error', true)
		.limit(1000);

	if (error) {
		console.error('Error fetching error rows:', error);
		return [];
	}

	return errorRows;
}

// Main execution
(async () => {
	while (true) {
		const errorRows = await getErrorRows();
		console.log(`Found ${errorRows.length} rows with errors`);

		if (errorRows.length === 0) {
			console.log('No more error rows to process');
			break;
		}

		for (const row of errorRows) {
			await processRow(row);
		}

		console.log('Finished processing batch of error rows');
	}

	console.log('Finished processing all error rows');
})().catch(console.error);
