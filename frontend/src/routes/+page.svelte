<script lang="ts">
  import { onMount } from 'svelte';
  import { writable } from 'svelte/store';
  import Modal from 'svelte-simple-modal';
  import SearchResults from '../components/SearchResults.svelte';
  import { getRecordsSupabase, searchSupabaseEmbedSearch, supabaseResultsFromEmbedding } from '../utils/supabase';

  let input = '';
  let result: any[] = [];
  let loading = false;
  let worker: Worker;
  const recordMap = writable<Record<string, any>>({});
  const modalStore = writable<any>(null);

  // Device capability flags and store
  const capabilities = writable({
    webAssembly: false,
    webWorkers: false,
    transformersReady: true,
    embeddingOnDevice: false
  });

  let embeddingOnDevice = false;

  async function fetchIssues() {
    const records = await getRecordsSupabase();
    recordMap.set(records);
  }

  async function handleSearch(query: string) {
    if (loading) return;
    if (!embeddingOnDevice) {
      loading = true;
      const results = await searchSupabaseEmbedSearch(query);
      result = results;
      loading = false;
      return;
    }
    
    loading = true;
    try {
      worker.postMessage({ text: query });
    } catch (error) {
      console.error('Search error:', error);
      loading = false;
    }
  }

  function handleKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      handleSearch(input);
    }
  }

  async function checkDeviceCapabilities() {
    try {
      const hasWasm = typeof WebAssembly === 'object';
      const hasWorkers = typeof Worker !== 'undefined';
      const isSmallScreen = window.innerWidth < 500;
      
      embeddingOnDevice = hasWasm && hasWorkers && !isSmallScreen;
      
      capabilities.set({
        webAssembly: hasWasm,
        webWorkers: hasWorkers,
        transformersReady: true,
        embeddingOnDevice
      });

      console.log('Device capabilities:', {
        webAssembly: hasWasm,
        webWorkers: hasWorkers,
        embeddingOnDevice,
        windowWidth: window.innerWidth
      });
    } catch (error) {
      console.error('Error checking device capabilities:', error);
      embeddingOnDevice = false;
    }
  }

  async function init() {
    await checkDeviceCapabilities();
    
    if (!worker && embeddingOnDevice) {
      console.log('Initializing worker');
      worker = new Worker(new URL('../utils/worker.ts', import.meta.url), {
        type: 'module'
      });
      worker.postMessage({ type: 'init' });
    }
    await fetchIssues();

    const onMessageReceived = async (e: MessageEvent) => {
      if (e.data.status === 'complete') {
        try {
          console.log('Received embedding from worker:', {
            inputLength: input.length,
            embeddingLength: e.data.embedding.length,
            embeddingSample: e.data.embedding.slice(0, 5)
          });
          
          result = await supabaseResultsFromEmbedding(input, e.data.embedding);
        } catch (error) {
          console.error('Search error:', error);
          if (error instanceof Error) {
            console.error('Error details:', {
              name: error.name,
              message: error.message,
              stack: error.stack
            });
          }
          capabilities.update(c => ({...c, transformersReady: false}));
          embeddingOnDevice = false;
          await handleSearch(input);
        } finally {
          loading = false;
        }
      }
    };

    if (embeddingOnDevice) {
      worker.addEventListener('message', onMessageReceived);
      return () => worker.removeEventListener('message', onMessageReceived);
    }
  }

  onMount(() => {
    init();
  });
</script>

<Modal 
  show={$modalStore}
  styleWindow={{ width: '90vw', height: '80vh', maxWidth: 'none', marginBottom: '15vh', backgroundColor: 'black', color: 'white', border: '1px solid white', borderRadius: '0.5rem', overflow: 'hidden' }}
  styleContent={{ height: '100%' }}
  styleBg={{ backgroundColor: 'rgba(0, 0, 0, 0.5)' }}
  styleCloseButton={{ 
    color: 'white',
    backgroundColor: 'transparent', 
    border: 'none',
    opacity: '1',
    fontSize: '24px',
    position: 'absolute',
    top: '1rem',
    right: '1rem',
    width: '24px',
    height: '24px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    'aria-label': 'Close modal',
    type: 'button',
    content: '"×"'
  }}
>
  <div class="flex flex-col w-full h-full min-h-full flex-grow text-white bg-black">
    <div class="sticky top-0 bg-black px-4 md:px-20 pt-8 md:pt-12 pb-4 z-10">
      <h1 class="text-4xl md:text-5xl font-bold mb-6 text-white">
        The Searchable JFK Files 
      </h1>
    </div>

    <div class="flex flex-row flex-1 bg-black text-white">
      <div class="flex-1 px-4 md:px-20">
        <h2 class="text-sm mb-3 text-gray-300 max-w-[60vh] leading-relaxed">
          Original documents sourced from the <a href="https://www.archives.gov/research/jfk/release-2025" class="text-blue-400 hover:underline">National Archives</a>. Site built by <a href="https://lucasgelfond.online" class="text-blue-400 hover:underline">Lucas Gelfond</a>, and you can view the source <a href="https://github.com/lucasgelfond/jfk-files" class="text-blue-400 hover:underline">here</a>.
        </h2>

        <div class="flex gap-2">
          <div class="py-2">
            <input 
              type="text"
              class="border border-white rounded px-2 py-1 bg-black text-white"
              placeholder="Enter text to search..."
              bind:value={input}
              on:keypress={handleKeyPress}
              disabled={loading}
            />
            <button 
              class="border border-white text-white px-4 py-1 rounded hover:bg-white hover:text-black transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              on:click={() => handleSearch(input)}
              disabled={loading}
            >
              {#if loading}
                <span class="inline-block animate-spin mr-1">⟳</span>
                Searching...
              {:else}
                Search
              {/if}
            </button>
          </div>
        </div>

        <div class="overflow-y-auto pb-8 max-h-[400px] md:pb-40">
          <SearchResults 
            results={result} 
            recordMap={$recordMap} 
            modalStore={modalStore} 
          />
        </div>
      </div>
    </div>
  </div>
</Modal>
