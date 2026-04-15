<script lang="ts">
	import { WEBUI_NAME } from '$lib/stores';
	import { getContext } from 'svelte';

	const i18n = getContext('i18n');
</script>

<div id="tab-about" class="flex flex-col h-full justify-between space-y-3 text-sm mb-6">
	<div class="space-y-3 overflow-y-auto scrollbar-hidden h-full">
		<div class="text-xs text-gray-400 dark:text-gray-500">
			Emoji graphics provided by
			<a href="https://github.com/jdecked/twemoji" target="_blank">Twemoji</a>, licensed under
			<a href="https://creativecommons.org/licenses/by/4.0/" target="_blank">CC-BY 4.0</a>.
		</div>
	</div>
</div>
