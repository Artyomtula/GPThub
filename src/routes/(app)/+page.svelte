<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';

	import Chat from '$lib/components/chat/Chat.svelte';
	import { page } from '$app/stores';

	onMount(() => {
		const errorParam = $page.url.searchParams.get('error');
		if (errorParam) {
			// Sanitize: truncate and strip HTML to prevent injection via URL params
			const sanitized = errorParam.replace(/<[^>]*>/g, '').slice(0, 200);
			toast.error(sanitized || 'An unknown error occurred.');
		}
	});
</script>

<Chat />
