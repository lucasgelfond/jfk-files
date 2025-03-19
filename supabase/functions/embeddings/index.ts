import "jsr:@supabase/functions-js/edge-runtime.d.ts";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const { input } = await req.json();

    if (!input) {
      throw new Error("Missing required 'input' parameter");
    }

    // Generate embedding using Supabase AI
    const session = new Supabase.ai.Session("gte-small");
    const embedding = await session.run(input, {
      mean_pool: true,
      normalize: true,
    });

    return new Response(JSON.stringify({ embedding }), {
      headers: { ...corsHeaders, "Content-Type": "application/json" },
      status: 200,
    });
  } catch (error) {
    console.error("Embedding error:", error);
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
