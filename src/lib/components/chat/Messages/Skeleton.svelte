<script lang="ts">
	export let size = 'md';
	export let label = '';
</script>

{#if label}
	<div class="flex items-center gap-2 my-2 mx-1">
		<span class="relative flex size-2.5">
			<span
				class="absolute inline-flex h-full w-full animate-pulse rounded-full bg-gray-700 dark:bg-gray-200 opacity-75"
			></span>
			<span class="relative inline-flex size-2.5 rounded-full bg-black dark:bg-white animate-size"
			></span>
		</span>
		<span class="text-sm shimmer">{label}</span>
	</div>
{:else}
	<span
		class="relative flex {size === 'md'
			? 'size-3 my-2'
			: size === 'xs'
				? 'size-1.5 my-1'
				: 'size-2 my-1'} mx-1"
	>
		<span
			class="absolute inline-flex h-full w-full animate-pulse rounded-full bg-gray-700 dark:bg-gray-200 opacity-75"
		></span>
		<span
			class="relative inline-flex {size === 'md'
				? 'size-3'
				: size === 'xs'
					? 'size-1.5'
					: 'size-2'} rounded-full bg-black dark:bg-white animate-size"
		></span>
	</span>
{/if}

<style>
	@keyframes size {
		0%,
		100% {
			transform: scale(1);
		}
		50% {
			transform: scale(1.25);
		}
	}

	.animate-size {
		animation: size 1.5s ease-in-out infinite;
	}
</style>
