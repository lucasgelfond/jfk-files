import {
	pipeline,
	type FeatureExtractionPipeline,
	type ProgressCallback
} from '@huggingface/transformers';

// Use the Singleton pattern to enable lazy construction of the pipeline.
class PipelineSingleton {
	static task = 'feature-extraction' as const;
	static model = 'Supabase/gte-small';
	static instance: Promise<FeatureExtractionPipeline> | null = null;

	static async getInstance(progress_callback?: ProgressCallback) {
		if (this.instance === null) {
			// console.log('Creating new pipeline instance...');
			this.instance = pipeline(this.task, this.model, {
				progress_callback,
				dtype: 'fp32',
				device: 'wasm' // Default to wasm since WebGPU support is experimental
			});
			// console.log('Pipeline instance created');
		}
		return this.instance;
	}
}

// Listen for messages from the main thread
self.addEventListener('message', async (event: MessageEvent) => {
	// console.log('Received message:', event.data);

	// Signal that we're starting initialization
	self.postMessage({ status: 'initiate' });

	// Retrieve the classification pipeline. When called for the first time,
	// this will load the pipeline and save it for future use.
	const classifier = await PipelineSingleton.getInstance((progress) => {
		// We also add a progress callback to the pipeline so that we can
		// track model loading.
		// console.log('Pipeline loading progress:', progress);
		self.postMessage({ status: 'loading', progress });
	});

	// Signal that model is ready
	self.postMessage({ status: 'ready' });

	// Only proceed with embedding if we have text to process
	if (event.data.text) {
		// console.log('Processing text:', event.data.text);

		// Actually perform the classification
		const output = await classifier(event.data.text, {
			pooling: 'mean',
			normalize: true
		});

		// Extract the embedding output
		const embedding = Array.from(output.data);
		// console.log('Generated embedding of length:', embedding.length);

		// Send the output back to the main thread
		self.postMessage({
			status: 'complete',
			embedding
		});
		// console.log('Sent results back to main thread');
	}
});
