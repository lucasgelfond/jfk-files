<script lang="ts">
    // Props
    export let item: any;
    export let recordMap: Record<string, any> = {};
    
    // Dispatch click event to parent
    import { createEventDispatcher } from 'svelte';
    const dispatch = createEventDispatcher();
    
    function handleClick() {
      dispatch('select', item);
    }
  </script>
  
  <button 
    type="button"
    class="text-left border border-white rounded p-4 grid grid-cols-[1fr] min-[350px]:grid-cols-[80px_1fr] md:grid-cols-[100px_220px_1fr] gap-3 md:gap-4 cursor-pointer hover:bg-gray-800 w-full text-white bg-black"
    on:click={handleClick}
  >
    <!-- Image column - only show above 350px width -->
    <div class="hidden min-[350px]:block w-[80px] md:w-[100px] self-start">
      {#if item.cloudinary}
        <img 
          src={item.cloudinary?.secure_url} 
          alt="Page preview" 
          class="w-full h-auto max-h-[100px] md:max-h-[150px] object-contain" 
        />
      {/if}
    </div>
    
    <!-- Mobile: Combined metadata and content, Desktop: Just metadata -->
    <div class="flex flex-col md:hidden">
      {#if recordMap[item.parent_record_id]}
        <div class="text-xs text-white">
          <div class="font-bold">
            Record Number: {recordMap[item.parent_record_id].record_number}
          </div>
          <div>Page {item.page_number}/{recordMap[item.parent_record_id].num_pages}</div>
        </div>
        <div class="flex gap-2 mt-1 text-xs">
          <a 
            href={recordMap[item.parent_record_id].pdf_link} 
            class="text-blue-400 hover:underline" 
            target="_blank"
            on:click|stopPropagation
          >
            PDF
          </a>
        </div>
        <!-- OCR content for mobile -->
        <div class="mt-1 text-xs h-[60px] overflow-y-auto text-white">
          {item.ocr_result}
        </div>
      {/if}
    </div>
    
    <!-- Desktop only: Metadata column -->
    <div class="hidden md:flex flex-col">
      {#if recordMap[item.parent_record_id]}
        <div class="text-sm text-white">
          <div class="font-bold">Record Number: {recordMap[item.parent_record_id].record_number}</div>
          <div>Page {item.page_number}/{recordMap[item.parent_record_id].num_pages}</div>
        </div>
        <div class="flex gap-2 mt-2 text-sm">
          <a 
            href={recordMap[item.parent_record_id].pdf_link} 
            class="text-blue-400 hover:underline" 
            target="_blank"
            on:click|stopPropagation
          >
            PDF
          </a>
        </div>
      {/if}
    </div>
    
    <!-- Desktop only: OCR content column -->
    <div class="hidden md:block h-[150px] overflow-y-auto text-sm text-white">
      {item.ocr_result}
    </div>
  </button>