<script lang="ts">
  import { onMount } from 'svelte';
  import { createClient } from '@supabase/supabase-js';
  import { bind } from 'svelte-simple-modal';
  import ResultModal from './ResultModal.svelte';

  // Props
  export let modalStore: any;

  const supabase = createClient(
    import.meta.env.VITE_SUPABASE_URL,
    import.meta.env.VITE_SUPABASE_KEY
  );

  let messages: Array<{type: 'user' | 'assistant', content: string, sources?: any[]}> = [];
  let currentMessage = '';
  let loading = false;
  let recordMap: Record<string, any> = {};

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
    
    loading = true;
    messages = [...messages, { type: 'user', content: currentMessage }];
    const userMessage = currentMessage;
    currentMessage = '';

    try {
      const response = await fetch('https://anythingllm-production-047a.up.railway.app/api/v1/workspace/jfk/chat', {
        method: 'POST',
        headers: {
          'accept': 'application/json',
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${import.meta.env.VITE_ANYTHINGLLM_KEY}`
        },
        body: JSON.stringify({
          message: userMessage,
          mode: 'chat',
          sessionId: 'default-session',
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
</script>

<div class="flex flex-col h-full max-w-2xl mx-auto p-4">
  <div class="flex-1 overflow-y-auto mb-4 space-y-4">
    {#each messages as message}
      <div class="flex flex-col {message.type === 'user' ? 'items-end' : 'items-start'}">
        <div class="max-w-[80%] rounded-lg p-3 {message.type === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-200 text-black'}">
          <p class="whitespace-pre-wrap">{message.content}</p>
        </div>
        {#if message.sources}
          <div class="mt-2 text-sm text-gray-500">
            <p class="font-semibold">Sources:</p>
            {#each message.sources as source}
              <div 
                class="ml-2 cursor-pointer hover:bg-gray-100 p-1 rounded"
                on:click={() => handleSourceClick(source)}
              >
                <p class="font-medium">{source.title}</p>
                <p class="text-xs italic">{source.chunk}</p>
              </div>
            {/each}
          </div>
        {/if}
      </div>
    {/each}
  </div>

  <div class="flex gap-2">
    <textarea
      class="flex-1 border border-gray-300 rounded px-3 py-2 focus:outline-none focus:border-blue-500"
      placeholder="Type your message..."
      rows="1"
      bind:value={currentMessage}
      on:keydown={handleKeyPress}
      disabled={loading}
    />
    <button
      class="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
      on:click={sendMessage}
      disabled={loading || !currentMessage.trim()}
    >
      {loading ? 'Sending...' : 'Send'}
    </button>
  </div>
</div>
