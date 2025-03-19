import { createClient } from '@supabase/supabase-js';
import Papa from 'papaparse';

// Create Supabase client
export const supabase = createClient(
	import.meta.env.VITE_SUPABASE_URL,
	import.meta.env.VITE_SUPABASE_KEY
);

/**
 * Fetches all records from the database
 * @returns A record mapping record IDs to record objects
 */
export async function getRecordsSupabase(): Promise<Record<string, any>> {
	try {
		// First try to get static records
		const response = await fetch('/records.csv');
		const csvText = await response.text();

		const parseResult = Papa.parse(csvText, {
			header: true,
			dynamicTyping: true
		});

		if (parseResult.data && parseResult.data.length > 0) {
			return parseResult.data.reduce(
				(acc, record) => {
					acc[record.id] = record;
					return acc;
				},
				{} as Record<string, any>
			);
		}

		// Fall back to Supabase if static records not available
		const { data: records, error } = await supabase
			.from('record')
			.select('*')
			.order('created_at', { ascending: false })
			.limit(1500);

		if (error) {
			console.error('Error fetching records from Supabase:', error);
			return {};
		}

		if (records) {
			console.log('Supabase Records:', records);
			return records.reduce(
				(acc, record) => {
					acc[record.id] = record;
					return acc;
				},
				{} as Record<string, any>
			);
		}

		return {};
	} catch (err) {
		console.error('Error fetching records:', err);
		return {};
	}
}

/**
 * Generates an embedding vector for the given text using Supabase Edge Function
 * @param input The text to generate an embedding for
 * @returns The embedding vector
 */
export async function supabaseEmbed(input: string): Promise<number[]> {
	console.log('generating embedding with supabase');
	try {
		const response = await fetch(`${import.meta.env.VITE_SUPABASE_URL}/functions/v1/embeddings`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				Authorization: `Bearer ${import.meta.env.VITE_SUPABASE_KEY}`
			},
			body: JSON.stringify({ input })
		});

		if (!response.ok) {
			throw new Error(`Embedding request failed: ${response.status} ${response.statusText}`);
		}

		const { embedding } = await response.json();
		return embedding;
	} catch (error) {
		console.error('Embedding error:', error);
		throw error;
	}
}

/**
 * Performs a semantic search using the Supabase Edge Function
 * @param query The search query
 * @param matchCount Number of results to return
 * @returns Array of search results
 */
export async function searchSupabaseEmbedSearch(
	query: string,
	matchCount: number = 30
): Promise<any[]> {
	try {
		const response = await fetch(`${import.meta.env.VITE_SUPABASE_URL}/functions/v1/embed-search`, {
			method: 'POST',
			headers: {
				Accept: 'application/json',
				Authorization: `Bearer ${import.meta.env.VITE_SUPABASE_KEY}`
			},
			body: JSON.stringify({
				query: query,
				match_count: matchCount
			})
		});

		if (!response.ok) {
			throw new Error(`Search request failed: ${response.status} ${response.statusText}`);
		}

		const data = await response.json();
		// Filter out any results with errors
		return data.filter((item: any) => !item?.error);
	} catch (error) {
		console.error('Search error:', error);
		throw error;
	}
}

/**
 * Fetches search results using a pre-computed embedding
 * @param queryText The original search text
 * @param embedding The embedding vector
 * @param matchCount Number of results to return
 * @returns Array of search results
 */
export async function supabaseResultsFromEmbedding(
	queryText: string,
	embedding: number[],
	matchCount: number = 30
): Promise<any[]> {
	try {
		console.log('Using supabase to fetch results with embedding:', {
			queryText,
			embeddingLength: embedding.length
		});

		// Use the Supabase client to call the RPC function directly
		const { data, error } = await supabase.rpc('hybrid_search', {
			query_text: queryText,
			query_embedding: embedding,
			match_count: matchCount
		});

		if (error) {
			console.error('Supabase RPC error:', error);
			throw error;
		}

		// Filter out any results with errors
		return data.filter((item: any) => !item?.error);
	} catch (error) {
		console.error('Search error details:', error);
		throw error;
	}
}
