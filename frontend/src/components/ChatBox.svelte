<script lang="ts">
  import { onMount } from 'svelte';
  import { createClient } from '@supabase/supabase-js';
  import { bind } from 'svelte-simple-modal';
  import ResultModal from './ResultModal.svelte';
  import { createEventDispatcher } from 'svelte';
  import { v4 as uuidv4 } from 'uuid';

  // Props
  export let modalStore: any;
  export let initialSearch: string | null = null;
  export let results: any[] = [];

  const supabase = createClient(
    import.meta.env.VITE_SUPABASE_URL,
    import.meta.env.VITE_SUPABASE_KEY
  );

  let messages: Array<{type: 'user' | 'assistant', content: string, sources?: any[]}> = [];
  let currentMessage = '';
  let loading = false;
  let recordMap: Record<string, any> = {};
  let sessionId = uuidv4();

  const dispatch = createEventDispatcher();

  async function fetchSourcePages(sources: any[]) {
    if (!sources.length) return;

    const recordNumbers = sources.map(source => source.title.replace('.txt', ''));

    const { data, error } = await supabase
      .from('record')
      .select(`
        id,
        record_number,
        pdf_link,
        num_pages,
        page!inner (
          id,
          page_number,
          ocr_result,
          cloudinary,
          parent_record_id
        )
      `)
      .in('record_number', recordNumbers)
      .eq('page.page_number', 1);

    if (!error && data) {
      data.forEach(record => {
        recordMap[record.record_number] = {
          ...record,
          page: record.page[0]
        };
      });
    }
  }

  function handleSourceClick(source: any) {
    if (!source.title) return;
    
    const recordNumber = source.title.replace('.txt', '');
    const record = recordMap[recordNumber];
    
    if (record) {
      modalStore.set(bind(ResultModal, { 
        item: record.page,
        record: record
      }));
    }
  }

  async function sendMessage() {
    if (!currentMessage.trim() || loading) return;
    
    results = [];
    
    loading = true;
    messages = [...messages, { type: 'user', content: currentMessage }];
    const userMessage = currentMessage;
    currentMessage = '';

    try {
        // not ideal but we leak API keys if not 
      const response = await fetch('https://jfk-files-production.up.railway.app/api/v1/chat', {
        method: 'POST',
        headers: {
          'accept': 'application/json', 
          'Content-Type': 'application/json',
          'credentials': 'include',
          'mode': 'cors'
        },
        body: JSON.stringify({
          message: userMessage,
          mode: 'query',
          sessionId: sessionId,
          attachments: []
        })
      });

      const data = await response.json();

      if (data.error) {
        throw new Error(data.error);
      }

      messages = [...messages, {
        type: 'assistant',
        content: data.textResponse,
        sources: data.sources
      }];

      // Fetch source pages when new message arrives
      if (data.sources) {
        await fetchSourcePages(data.sources);
      }

    } catch (error) {
      console.error('Chat error:', error);
      messages = [...messages, {
        type: 'assistant',
        content: 'Sorry, there was an error processing your request.'
      }];
    } finally {
      loading = false;
    }
  }

  function handleKeyPress(event: KeyboardEvent) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendMessage();
    }
  }

  onMount(() => {
    if (initialSearch) {
      currentMessage = initialSearch;
      sendMessage();
    }
  });
</script>

<div class="flex flex-col h-full w-full bg-black p-4">
  <div class="flex-1 overflow-y-auto mb-4 space-y-3 scrollbar-thin scrollbar-thumb-gray-400 scrollbar-track-transparent px-3">
    {#each messages as message}
      <div class="flex flex-col {message.type === 'user' ? 'items-end' : 'items-start'}">
        <div class="max-w-[85%] rounded-lg p-3 {message.type === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-black'}">
          <p class="whitespace-pre-wrap text-sm">{message.content}</p>
        </div>
        {#if message.sources}
          <div class="mt-2 text-xs md:text-sm text-gray-300">
            <p class="font-semibold">Sources:</p>
            {#each message.sources as source}
              <div 
                class="ml-2 mt-2 cursor-pointer hover:bg-gray-700 p-2 rounded-lg border border-white/20 hover:border-white/40 transition-colors"
                on:click={() => handleSourceClick(source)}
                on:keydown={(e) => e.key === 'Enter' && handleSourceClick(source)}
                role="button"
                tabindex="0"
              >
                <p class="font-medium text-sm md:text-xs">{source.title}</p>
                <p class="text-xs md:text-[10px] italic">{source.chunk}</p>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/each}
  </div>

  <div class="flex gap-2 mt-auto border-t border-white/20 pt-4">
    <textarea
      class="flex-1 border border-gray-300 rounded px-3 py-2 focus:outline-none focus:border-blue-500 bg-black text-white text-sm"
      placeholder="Type your message..."
      rows="2"
      bind:value={currentMessage}
      on:keydown={handleKeyPress}
      disabled={loading}
    ></textarea>
    <button
      class="px-4 py-2 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
      on:click={sendMessage}
      disabled={loading || !currentMessage.trim()}
    >
      {loading ? 'Loading...' : 'Send'}
    </button>
  </div>
</div>
