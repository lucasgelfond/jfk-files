import { createClient } from '@supabase/supabase-js';

// Create Supabase client
export const supabase = createClient(
	import.meta.env.VITE_SUPABASE_URL,
	import.meta.env.VITE_SUPABASE_KEY
);

/**
 * Fetches all issues from the database
 * @returns A record mapping issue IDs to issue objects
 */
export async function getIssuesSupabase(): Promise<Record<string, any>> {
	try {
		// First try to get static issues
		const response = await fetch('/issues.json');
		const staticIssues = await response.json();

		// If we have static issues, use those
		if (staticIssues && staticIssues.length > 0) {
			// console.log('Using static issues');
			return staticIssues.reduce(
				(acc, issue) => {
					acc[issue.id] = issue;
					return acc;
				},
				{} as Record<string, any>
			);
		}

		// Fallback to Supabase if no static issues
		console.log('No static issues found, falling back to Supabase');
		const { data: issues, error } = await supabase
			.from('issue')
			.select('*')
			.order('created_at', { ascending: false });

		if (error) {
			console.error('Error fetching issues from Supabase:', error);
			return {};
		}

		if (issues) {
			console.log('Supabase Issues:', issues);
			return issues.reduce(
				(acc, issue) => {
					acc[issue.id] = issue;
					return acc;
				},
				{} as Record<string, any>
			);
		}

		return {};
	} catch (err) {
		console.error('Error fetching issues:', err);
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
