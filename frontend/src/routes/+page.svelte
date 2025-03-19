<script lang="ts">
  import { onMount } from 'svelte';
  let input = '';
  let result: number[] = [];
  let loading = false;
  let worker: Worker;

  onMount(() => {
    worker = new Worker(new URL('../utils/worker.ts', import.meta.url), {
      type: 'module'
    });

    worker.addEventListener('message', (e) => {
      if (e.data.status === 'complete') {
        result = e.data.embedding;
        loading = false;
      }
    });
  });

  function handleSearch() {
    if (!loading) {
      loading = true;
      worker.postMessage({ text: input });
    }
  }

  function handleKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      handleSearch();
    }
  }
</script>

<div class="flex gap-2">
  <input 
    type="text"
    class="border rounded px-2 py-1"
    placeholder="Enter text..."
    bind:value={input}
    on:keypress={handleKeyPress}
    disabled={loading}
  />
  <button 
    class="border px-4 py-1 rounded"
    on:click={handleSearch}
    disabled={loading}
  >
    {#if loading}
      Loading...
    {:else}
      Generate Embedding
    {/if}
  </button>
</div>

{#if result.length > 0}
  <h3>Embedding Result:</h3>
  <pre>{JSON.stringify(result, null, 2)}</pre>
{/if}
