<script lang="ts">
  import { supabase } from '../utils/supabase';
  import { onMount } from 'svelte';

  let pages: any[] = [];

  onMount(async () => {
    const { data, error } = await supabase
      .from('page')
      .select('*')
      .limit(20);

    if (error) {
      console.error('Error fetching pages:', error);
      return;
    }

    pages = data || [];
  });
</script>

<h1>Pages from Supabase</h1>
<pre>{JSON.stringify(pages, null, 2)}</pre>
