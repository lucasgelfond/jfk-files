<script lang="ts">
    import { bind } from 'svelte-simple-modal';
    import ResultModal from './ResultModal.svelte';
    import SearchResult from './SearchResult.svelte';
  
    // Props
    export let results: any[] = [];
    export let recordMap: Record<string, any> = {};
    export let modalStore: any;
    
    // Function to show the result modal
    function showResultModal(item: any) {
      const record = recordMap[item.parent_record_id];
      modalStore.set(bind(ResultModal, { item, record }));
    }


</script>
  
  {#if results.length}
    <div class="mt-4 h-full">
      <h3 class="font-bold mb-3">Search Results:</h3>
      <div class="grid gap-4 max-w-3xl">
        {#each results as item}
          <SearchResult 
            {item} 
            {recordMap} 
            on:select={(event) => showResultModal(event.detail)}
          />
        {/each}
      </div>
    </div>
  {/if}