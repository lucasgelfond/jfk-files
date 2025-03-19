// Follow this setup guide to integrate the Deno language server with your editor:
// https://deno.land/manual/getting_started/setup_your_environment
// This enables autocomplete, go to definition, etc.

// Setup type definitions for built-in Supabase Runtime APIs
import "jsr:@supabase/functions-js/edge-runtime.d.ts";

import { createClient, SupabaseClient } from "jsr:@supabase/supabase-js@2";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

async function performSearch(
  supabaseClient: SupabaseClient,
  query: string,
  match_count: number = 10
) {
  try {
    // Generate embedding using Supabase embeddings API
    const embeddingResponse = await supabaseClient.functions.invoke(
      "embeddings",
      {
        body: { input: query },
      }
    );

    if (embeddingResponse.error) {
      throw new Error(
        `Embedding generation failed: ${embeddingResponse.error.message}`
      );
    }

    const embedding = embeddingResponse.data.embedding;

    // Call hybrid search function
    const { data, error } = await supabaseClient.rpc("hybrid_search", {
      query_text: query,
      query_embedding: embedding,
      match_count: match_count || 10,
    });

    if (error) {
      console.error("Search error:", error);
      throw error;
    }

    return data;
  } catch (error) {
    console.error("Search function error:", error);
    throw error;
  }
}

Deno.serve(async (req) => {
  // Handle CORS preflight
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    // Create client with Auth context of the user
    const supabaseClient = createClient(
      Deno.env.get("SUPABASE_URL") ?? "",
      Deno.env.get("SUPABASE_ANON_KEY") ?? "",
      {
        global: {
          headers: { Authorization: req.headers.get("Authorization")! },
        },
      }
    );

    if (req.method === "POST") {
      const { query, match_count } = await req.json();

      if (!query) {
        throw new Error("Missing required 'query' parameter");
      }

      const results = await performSearch(supabaseClient, query, match_count);

      return new Response(JSON.stringify(results), {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: 200,
      });
    }

    return new Response("Method not allowed", {
      headers: corsHeaders,
      status: 405,
    });
  } catch (error) {
    console.error("Request error:", error);
    return new Response(
      JSON.stringify({
        error: error.message,
        details: error.details,
        hint: error.hint,
      }),
      {
        headers: { ...corsHeaders, "Content-Type": "application/json" },
        status: error.status || 500,
      }
    );
  }
});

/* To invoke locally:

  1. Run `supabase start` (see: https://supabase.com/docs/reference/cli/supabase-start)
  2. Make an HTTP request:

  curl -i --location --request POST 'http://127.0.0.1:54321/functions/v1/embed-search' \
    --header 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0' \
    --header 'Content-Type: application/json' \
    --data '{"query": "Your search query here"}'

*/
