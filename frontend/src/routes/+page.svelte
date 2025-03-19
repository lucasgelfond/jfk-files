<script lang="ts">
  import { onMount } from 'svelte';
  import { writable } from 'svelte/store';
  import Modal from 'svelte-simple-modal';
  import SearchResults from '../components/SearchResults.svelte';
  import { getRecordsSupabase, searchSupabaseEmbedSearch, supabaseResultsFromEmbedding } from '../utils/supabase';
import {supabase} from '../utils/supabase';
	import ChatBox from '../components/ChatBox.svelte';

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

  // Add this new state
  let showChat = false;

  // Add initialSearch prop for ChatBox
  let initialSearch: string | null = null;

  // Modify toggleChat to handle search input
  function toggleChat() {
    result = [];
    showChat = !showChat;
  }

  async function fetchIssues() {
    const records = await getRecordsSupabase();
    recordMap.set(records);
  }
  async function handleSearch(query: string) {
    if (loading) return;
    
    // Hide chat when searching
    showChat = false;
    initialSearch = null;

    if (!embeddingOnDevice) {
      loading = true;
      const results = await searchSupabaseEmbedSearch(query);
      result = results;
      
      // Log search usage
      const browserInfo = {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        cookieEnabled: navigator.cookieEnabled,
        screenResolution: {
          width: window.screen.width,
          height: window.screen.height
        },
        viewport: {
          width: window.innerWidth,
          height: window.innerHeight
        },
        timestamp: new Date().toISOString(),
        embeddingOnDevice: false
      };
      loading = false;

      try {
        await supabase
          .from('usage_log')
          .insert([{ 
            info: browserInfo,
            query: query
          }]);
      } catch (error) {
        console.error('Error logging usage:', error);
      }

      return;
    }
    
    loading = true;
    try {
      worker.postMessage({ text: query });

      // Log search usage
      const browserInfo = {
        userAgent: navigator.userAgent,
        platform: navigator.platform,
        language: navigator.language,
        cookieEnabled: navigator.cookieEnabled,
        screenResolution: {
          width: window.screen.width,
          height: window.screen.height
        },
        viewport: {
          width: window.innerWidth,
          height: window.innerHeight
        },
        timestamp: new Date().toISOString(),
        embeddingOnDevice: true
      };

      try {
        await supabase
          .from('usage_log')
          .insert([{ 
            info: browserInfo,
            query: query
          }]);
      } catch (error) {
        console.error('Error logging usage:', error);
      }

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
  styleWindow={{ 
    width: '90vw', 
    height: 'min(80vh, 100vh)', 
    maxWidth: 'none',
    backgroundColor: 'black', 
    color: 'white', 
    border: '1px solid white', 
    borderRadius: '0.5rem', 
    overflow: 'hidden',
    margin: '0'
  }}
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
  <div class="flex flex-col w-full h-full min-h-full flex-grow text-white bg-black max-w-[100%]">
    <div class="sticky top-0 bg-black px-4 md:px-20 pt-8 md:pt-12 pb-4 z-10">
      <h1 class="text-4xl md:text-5xl font-bold mb-6 text-wrap text-white">
        The JFK Files 
      </h1>
      <h2 class="text-sm mb-5 text-gray-300 max-w-[60vh] leading-relaxed italic">
        <a href="http://jfkfiles.exposed" class="underline">www.jfkfiles.exposed</a>
      </h2>

      <h3 class="text-sm mb-5 text-gray-300 max-w-[60vh] leading-relaxed">
        Original documents sourced from the <a href="https://www.archives.gov/research/jfk/release-2025" class="text-blue-400 hover:underline">National Archives</a>. Site built by <a href="https://lucasgelfond.online" class="text-blue-400 hover:underline">Lucas Gelfond</a>. You can view the source <a href="https://github.com/lucasgelfond/jfk-files" class="text-blue-400 hover:underline">here</a>.
      </h3>

      <div class="max-w-[60vh]">
        <div class="flex w-full gap-2">
          <input 
            type="text"
            class="flex-1 border border-white rounded px-2 py-1 bg-black text-white"
            placeholder="Enter text to search..."
            bind:value={input}
            on:keypress={handleKeyPress}
            disabled={loading}
          />
          <button 
            class="border border-white text-white px-4 py-1 rounded hover:bg-white hover:text-black transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
            on:click={() => handleSearch(input)}
            disabled={loading}
          >
            {#if loading}
              <span class="inline-block animate-spin">⟳</span>
            {:else}
              Search
            {/if}
          </button>
          <button 
            class="border border-white text-white px-4 py-1 rounded hover:bg-white hover:text-black transition-colors"
            on:click={toggleChat}
          >
            Open Chat
          </button>
        </div>
      </div>
    </div>

    <div class="flex flex-row flex-1 bg-black text-white overflow-hidden">
      <div class="flex-1 px-4 md:px-20 overflow-y-auto">
        <SearchResults 
          results={result} 
          recordMap={$recordMap} 
          modalStore={modalStore} 
        />
      </div>
    </div>
  </div>
</Modal>

<!-- Update the chat container -->
{#if showChat}
  <div class="fixed bottom-8 right-4 z-50 w-[400px] h-[500px] bg-black rounded-lg shadow-lg overflow-hidden border border-white">
    <div class="flex justify-between items-center p-2 border-b border-white/20">
      <h3 class="text-white font-semibold">Chat</h3>
      <button 
        class="text-white hover:text-gray-300"
        on:click={toggleChat}
      >
        ×
      </button>
    </div>
    <div class="h-[calc(500px-40px)]">
      <ChatBox 
        modalStore={modalStore} 
        initialSearch={input}
      />
    </div>
  </div>
{/if}

<!-- Add floating chat button when chat is not open -->
{#if !showChat}
  <button
    class="fixed bottom-4 right-4 z-50 bg-blue-500 text-white p-4 rounded-full shadow-lg hover:bg-blue-600 transition-colors"
    on:click={() => {input = ''; toggleChat(); }}
  >
    Chat 
  </button>
{/if}

<!-- Add the AnythingLLM script -->
<svelte:head>
  <script
    data-embed-id="c2a28c27-f820-468e-b5f9-0c58022db635"
    data-base-api-url="https://anythingllm-production-047a.up.railway.app/api/embed"
    src="https://anythingllm-production-047a.up.railway.app/embed/anythingllm-chat-widget.min.js">
  </script>
</svelte:head>
