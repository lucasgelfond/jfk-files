import { writable } from 'svelte/store';

export const resultMap = writable<Record<string, any>>({});
