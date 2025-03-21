<script lang="ts">
    import { onMount } from 'svelte';
    import { writable } from 'svelte/store';
    import type { PageMap, PageData } from '$lib/pageUtils';
    import { fetchAllPages } from '$lib/pageUtils';
    
    export let item: PageData;
    export let record: any;
  
    const currentPageNumber = writable(Number(item.page_number) || 1);
    const allPages = writable<PageMap>({});
    const loading = writable(false);
  
    async function loadAllPages() {
      loading.set(true);
      try {
        const pages = await fetchAllPages(record.id);
        allPages.set(pages);
      } finally {
        loading.set(false);
      }
    }
  
   
    function changePage(newPageNumber: number) {
      if ($loading) return;
      newPageNumber = Number(newPageNumber);
      if (newPageNumber < 1 || newPageNumber > record.num_pages) return;
      if (!$allPages[newPageNumber]) return;
      
      currentPageNumber.set(newPageNumber);
    }
  
    // Handle keyboard and touch navigation
    function handleKeydown(event: KeyboardEvent) {
      if (event.key === 'ArrowLeft' && $currentPageNumber > 1) {
        changePage($currentPageNumber - 1);
      } else if (event.key === 'ArrowRight' && $currentPageNumber < record.num_pages) {
        changePage($currentPageNumber + 1);
      }
    }
  
    let touchStart: number;
    function handleTouchStart(event: TouchEvent) {
      touchStart = event.touches[0].clientX;
    }
  
    function handleTouchEnd(event: TouchEvent) {
      const touchEnd = event.changedTouches[0].clientX;
      const diff = touchStart - touchEnd;
  
      if (Math.abs(diff) > 50) { // Minimum swipe distance
        if (diff > 0 && $currentPageNumber < record.num_pages) {
          changePage($currentPageNumber + 1);
        } else if (diff < 0 && $currentPageNumber > 1) {
          changePage($currentPageNumber - 1);
        }
      }
    }
  
    let cleanup: () => void;
  
    onMount(() => {
  
      allPages.set({ [item.page_number]: item });
      window.addEventListener('keydown', handleKeydown);
      cleanup = () => window.removeEventListener('keydown', handleKeydown);
      loadAllPages();
      return cleanup;
    });
  
  </script>
  <!-- Desktop Layout -->
  <div class="hidden md:flex bg-black text-white">
    <!-- Image column - flexible width to accommodate full-width image -->
    <div class="flex-1 overflow-y-auto">
      <div 
        class="relative inline-block"
        on:touchstart={handleTouchStart}
        on:touchend={handleTouchEnd}
      >
        {#if $allPages[$currentPageNumber]?.cloudinary.secure_url}
          <img 
            src={$allPages[$currentPageNumber].cloudinary.secure_url} 
            alt="Page {$currentPageNumber}" 
            class="w-full h-auto" 
          />
          
          <div class="absolute inset-y-0 left-0 right-0 flex justify-between items-center">
            <button 
              class="bg-black/70 text-white p-6 text-3xl rounded-full hover:bg-black/90 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
              disabled={$currentPageNumber <= 1 || $loading || !$allPages[$currentPageNumber - 1]}
              on:click={() => changePage($currentPageNumber - 1)}
            >
              ←
            </button>
            <button 
              class="bg-black/70 text-white p-6 text-3xl rounded-full hover:bg-black/90 disabled:opacity-30 disabled:cursor-not-allowed flex items-center justify-center"
              disabled={$currentPageNumber >= record.num_pages || $loading || !$allPages[$currentPageNumber + 1]}
              on:click={() => changePage($currentPageNumber + 1)}
            >
              →
            </button>
          </div>
        {/if}
      </div>
    </div>
  
    <!-- Content column - fixed width for readability -->
    <div class="w-[500px] flex-none flex flex-col p-6 border-l border-white/20">
      <div class="flex-none">
        <div class="text-2xl font-bold mb-4">Record {record.record_number}</div>
        <div class="flex justify-between items-center">
          <a href={record.pdf_link} class="text-blue-400 hover:underline" target="_blank">Download PDF</a>
          <div>Page {$currentPageNumber} of {record.num_pages}</div>
        </div>
      </div>
      
      <div class="flex-1 overflow-y-auto mt-6 h-full">
        <div class="text-lg leading-relaxed">
          {$allPages[$currentPageNumber]?.ocr_result}
        </div>
      </div>
    </div>
  </div>
  <!-- Mobile Layout -->
  <div class="md:hidden flex flex-col h-full bg-black text-white">
    <div 
      class="flex-none relative max-h-[35vh]"
      on:touchstart={handleTouchStart}
      on:touchend={handleTouchEnd}
    >
      {#if $allPages[$currentPageNumber]?.cloudinary.secure_url}
        <img 
          src={$allPages[$currentPageNumber].cloudinary.secure_url} 
          alt="Page {$currentPageNumber}" 
          class="w-full h-full object-contain" 
        />
        
        <div class="absolute inset-y-0 left-0 flex items-center">
          <button
            class="bg-black/70 text-white p-2 rounded-r-lg hover:bg-black/90 disabled:opacity-30 disabled:cursor-not-allowed"
            disabled={$currentPageNumber <= 1 || $loading || !$allPages[$currentPageNumber - 1]}
            on:click={() => changePage($currentPageNumber - 1)}
          >
            <div class="w-6 h-12 flex items-center">←</div>
          </button>
        </div>
  
        <div class="absolute inset-y-0 right-0 flex items-center">
          <button
            class="bg-black/70 text-white p-2 rounded-l-lg hover:bg-black/90 disabled:opacity-30 disabled:cursor-not-allowed"
            disabled={$currentPageNumber >= record.num_pages || $loading || !$allPages[$currentPageNumber + 1]}
            on:click={() => changePage($currentPageNumber + 1)}
          >
            <div class="w-6 h-12 flex items-center">→</div>
          </button>
        </div>
      {/if}
    </div>
  
    <div class="p-4 flex-none border-b">
      <div class="mt-2 flex justify-between items-center">
        <a href={record.pdf_link} class="text-blue-400 hover:underline" target="_blank">Download PDF</a>
        <div>Page {$currentPageNumber} of {record.num_pages}</div>
      </div>
    </div>
  
    <div class="flex-1 overflow-y-auto p-4 min-h-0">
      <div class="text-base h-full">
        {$allPages[$currentPageNumber]?.ocr_result}
      </div>
    </div>
  </div>