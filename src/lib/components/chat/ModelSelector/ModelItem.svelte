<script lang="ts">
	import { marked } from 'marked';

	import { getContext, tick } from 'svelte';
	import dayjs from '$lib/dayjs';

	import { mobile, settings, user } from '$lib/stores';
	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';

	import Tooltip from '$lib/components/common/Tooltip.svelte';
	import { copyToClipboard, sanitizeResponseContent } from '$lib/utils';
	import ArrowUpTray from '$lib/components/icons/ArrowUpTray.svelte';
	import ModelItemMenu from './ModelItemMenu.svelte';
	import EllipsisHorizontal from '$lib/components/icons/EllipsisHorizontal.svelte';
	import { toast } from 'svelte-sonner';
	import Tag from '$lib/components/icons/Tag.svelte';
	import Cloud from '$lib/components/icons/Cloud.svelte';
	import Computer from '$lib/components/icons/Computer.svelte';
	import UserCircle from '$lib/components/icons/UserCircle.svelte';
	import CodeBracket from '$lib/components/icons/CodeBracket.svelte';
	import Photo from '$lib/components/icons/Photo.svelte';
	import Eye from '$lib/components/icons/Eye.svelte';
	import Sparkles from '$lib/components/icons/Sparkles.svelte';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import BookOpen from '$lib/components/icons/BookOpen.svelte';

	const i18n = getContext('i18n');

	export let selectedModelIdx: number = -1;
	export let item: any = {};
	export let index: number = -1;
	export let value: string = '';
	export let selectionEnabled: boolean = true;
	export let inactive: boolean = false;

	export let isAgent: boolean = false;

	export let unloadModelHandler: (modelValue: string) => void = () => {};
	export let pinModelHandler: (modelId: string) => void = () => {};

	export let onClick: () => void = () => {};

	const copyLinkHandler = async (model) => {
		const baseUrl = window.location.origin;
		const res = await copyToClipboard(`${baseUrl}/?model=${encodeURIComponent(model.id)}`);

		if (res) {
			toast.success($i18n.t('Copied link to clipboard'));
		} else {
			toast.error($i18n.t('Failed to copy link'));
		}
	};

	let showMenu = false;

	const isLocalModel = (model: any) =>
		model?.owned_by === 'ollama' || model?.connection_type === 'local';

	const getCapabilityIcon = (model: any): string => {
		const id = (model?.id || '').toLowerCase();
		// Virtual GPTHub agents — map by capability
		if (id === 'gpthub:auto') return 'auto';
		if (id === 'gpthub:code') return 'code';
		if (id === 'gpthub:vision') return 'vision';
		if (id === 'gpthub:image') return 'image';
		if (id === 'gpthub:web') return 'web';
		if (id === 'gpthub:research') return 'research';
		const text = `${id} ${(model?.name || '').toLowerCase()}`;
		const caps = model?.info?.meta?.capabilities || {};
		if (caps.image_generation || /\b(image|flux|dall|sdxl|stable.diffusion)\b/.test(text))
			return 'image';
		if (caps.vision || /\b(vision|vl\b|multimodal)\b/.test(text)) return 'vision';
		if (caps.code || /\b(coder|code|program)\b/.test(text)) return 'code';
		return 'text';
	};
</script>

<button
	role="option"
	aria-selected={selectionEnabled && value === item.value}
	aria-label={$i18n.t('Select {{modelName}} model', { modelName: item.label })}
	class="flex group/item w-full text-left font-medium line-clamp-1 select-none items-center rounded-button py-2 pl-3 pr-1.5 text-sm text-gray-700 dark:text-gray-100 outline-hidden transition-all duration-75 {inactive
		? 'hover:bg-transparent dark:hover:bg-transparent'
		: 'hover:bg-gray-100 dark:hover:bg-gray-800'} rounded-xl cursor-pointer {inactive
		? ''
		: 'data-highlighted:bg-muted'} {index === selectedModelIdx && selectionEnabled
		? 'bg-gray-100 dark:bg-gray-800 group-hover:bg-transparent'
		: ''} {inactive ? 'opacity-70' : ''}"
	data-arrow-selected={selectionEnabled && index === selectedModelIdx}
	data-value={item.value}
	on:click={() => {
		onClick();
	}}
>
	<div class="flex flex-col flex-1 gap-1.5">
		<!-- {#if (item?.model?.tags ?? []).length > 0}
			<div
				class="flex gap-0.5 self-center items-start h-full w-full translate-y-[0.5px] overflow-x-auto scrollbar-none"
			>
				{#each item.model?.tags.sort((a, b) => a.name.localeCompare(b.name)) as tag}
					<Tooltip content={tag.name} className="flex-shrink-0">
						<div
							class=" text-xs font-semibold px-1 rounded-sm uppercase bg-gray-500/20 text-gray-700 dark:text-gray-200"
						>
							{tag.name}
						</div>
					</Tooltip>
				{/each}
			</div>
		{/if} -->

		<div class="flex items-center gap-2">
			{#if !isAgent}
				<div class="flex items-center min-w-fit">
					<Tooltip
						content={$user?.role === 'admin' ? (item?.value ?? '') : ''}
						placement="top-start"
					>
						<div
							class="size-5 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center shrink-0"
						>
							{#if getCapabilityIcon(item.model) === 'image'}
								<Photo className="size-3 text-gray-600 dark:text-gray-300" strokeWidth="1.8" />
							{:else if getCapabilityIcon(item.model) === 'vision'}
								<Eye className="size-3 text-gray-600 dark:text-gray-300" strokeWidth="1.8" />
							{:else if getCapabilityIcon(item.model) === 'code'}
								<CodeBracket
									className="size-3 text-gray-600 dark:text-gray-300"
									strokeWidth="1.8"
								/>
							{:else}
								<Sparkles className="size-3 text-gray-600 dark:text-gray-300" strokeWidth="1.8" />
							{/if}
						</div>
					</Tooltip>
				</div>
			{:else}
				<div
					class="size-5 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center shrink-0"
				>
					{#if getCapabilityIcon(item.model) === 'code'}
						<CodeBracket className="size-3 text-gray-600 dark:text-gray-300" strokeWidth="1.8" />
					{:else if getCapabilityIcon(item.model) === 'vision'}
						<Eye className="size-3 text-gray-600 dark:text-gray-300" strokeWidth="1.8" />
					{:else if getCapabilityIcon(item.model) === 'image'}
						<Photo className="size-3 text-gray-600 dark:text-gray-300" strokeWidth="1.8" />
					{:else if getCapabilityIcon(item.model) === 'web'}
						<GlobeAlt className="size-3 text-gray-600 dark:text-gray-300" strokeWidth="1.8" />
					{:else if getCapabilityIcon(item.model) === 'research'}
						<BookOpen className="size-3 text-gray-600 dark:text-gray-300" strokeWidth="1.8" />
					{:else}
						<Sparkles className="size-3 text-gray-600 dark:text-gray-300" strokeWidth="1.8" />
					{/if}
				</div>
			{/if}

			<div class="flex items-center">
				{#if isAgent}
					<div class="line-clamp-1">{item.label}</div>
				{:else}
					<Tooltip content={$user?.role === 'admin' ? item.value : ''} placement="top-start">
						<div class="line-clamp-1">{item.label}</div>
					</Tooltip>
				{/if}
			</div>

			<div class=" shrink-0 flex items-center gap-2">
				{#if item.model.owned_by === 'ollama'}
					{#if (item.model.ollama?.details?.parameter_size ?? '') !== ''}
						<div class="flex items-center translate-y-[0.5px]">
							<Tooltip
								content={`${
									item.model.ollama?.details?.quantization_level
										? item.model.ollama?.details?.quantization_level + ' '
										: ''
								}${
									item.model.ollama?.size
										? `(${(item.model.ollama?.size / 1024 ** 3).toFixed(1)}GB)`
										: ''
								}`}
								className="self-end"
							>
								<span class=" text-xs font-medium text-gray-600 dark:text-gray-400 line-clamp-1"
									>{item.model.ollama?.details?.parameter_size ?? ''}</span
								>
							</Tooltip>
						</div>
					{/if}
					{#if item.model.ollama?.expires_at && new Date(item.model.ollama?.expires_at * 1000) > new Date()}
						<div class="flex items-center translate-y-[0.5px] px-0.5">
							<Tooltip
								content={`${$i18n.t('Unloads {{FROM_NOW}}', {
									FROM_NOW: dayjs(item.model.ollama?.expires_at * 1000).fromNow()
								})}`}
								className="self-end"
							>
								<div class=" flex items-center">
									<span class="relative flex size-2">
										<span
											class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"
										/>
										<span class="relative inline-flex rounded-full size-2 bg-green-500" />
									</span>
								</div>
							</Tooltip>
						</div>
					{/if}
				{/if}

				<!-- {JSON.stringify(item.info)} -->

				{#if !isAgent && (item?.model?.tags ?? []).length > 0}
					{#key item.model.id}
						<Tooltip elementId="tags-{item.model.id}">
							<div slot="tooltip" id="tags-{item.model.id}">
								{#each item.model?.tags.sort((a, b) => a.name.localeCompare(b.name)) as tag}
									<Tooltip content={tag.name} className="flex-shrink-0">
										<div class=" text-xs font-medium rounded-sm uppercase text-white">
											{tag.name}
										</div>
									</Tooltip>
								{/each}
							</div>

							<div class="translate-y-[1px]">
								<Tag />
							</div>
						</Tooltip>
					{/key}
				{/if}

				{#if item.model?.info?.meta?.description}
					<Tooltip
						content={`${marked.parse(
							sanitizeResponseContent($i18n.t(item.model?.info?.meta?.description)).replaceAll(
								'\n',
								'<br>'
							)
						)}`}
					>
						<div class=" translate-y-[1px]">
							<svg
								xmlns="http://www.w3.org/2000/svg"
								fill="none"
								viewBox="0 0 24 24"
								stroke-width="1.5"
								stroke="currentColor"
								class="w-4 h-4"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z"
								/>
							</svg>
						</div>
					</Tooltip>
				{/if}
			</div>
		</div>
	</div>

	{#if !isAgent}
		<div class="ml-auto pl-2 pr-1 shrink-0 flex items-center gap-1.5">
			<Tooltip
				content={isLocalModel(item.model)
					? $i18n.t('Local model (runs on your machine)')
					: $i18n.t('Cloud model')}
			>
				<div class="w-4 text-gray-500 dark:text-gray-400 flex items-center justify-center">
					{#if isLocalModel(item.model)}
						<Computer className="size-3.5" strokeWidth="1.5" />
					{:else}
						<Cloud className="size-3.5" strokeWidth="1.5" />
					{/if}
				</div>
			</Tooltip>

			{#if $user?.role === 'admin' && item.model.owned_by === 'ollama' && item.model.ollama?.expires_at && new Date(item.model.ollama?.expires_at * 1000) > new Date()}
				<Tooltip
					content={`${$i18n.t('Eject')}`}
					className="flex-shrink-0 group-hover/item:opacity-100 opacity-0"
				>
					<button
						class="flex items-center justify-center w-4 h-4"
						aria-label={$i18n.t('Eject model')}
						on:click={(e) => {
							e.preventDefault();
							e.stopPropagation();
							unloadModelHandler(item.value);
						}}
					>
						<ArrowUpTray className="size-3" />
					</button>
				</Tooltip>
			{/if}

			<ModelItemMenu
				bind:show={showMenu}
				model={item.model}
				{pinModelHandler}
				copyLinkHandler={() => {
					copyLinkHandler(item.model);
				}}
			>
				<button
					aria-label={`${$i18n.t('More Options')}`}
					class="flex items-center justify-center w-4 h-4"
					on:click={(e) => {
						e.preventDefault();
						e.stopPropagation();
						showMenu = !showMenu;
					}}
				>
					<EllipsisHorizontal />
				</button>
			</ModelItemMenu>
		</div>
	{/if}
</button>
