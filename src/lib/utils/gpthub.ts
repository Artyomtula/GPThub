/**
 * GPTHub shared frontend utilities
 * =================================
 * Centralises constants and helper functions that were previously
 * duplicated across multiple Svelte components.
 */

// ---------------------------------------------------------------------------
// Virtual model IDs — canonical source of truth
// ---------------------------------------------------------------------------

export const VIRTUAL_MODEL_PREFIX = 'gpthub:';

export const VIRTUAL_MODEL_IDS = {
	AUTO: 'gpthub:auto'
} as const;

// ---------------------------------------------------------------------------
// Capability icon resolver
// ---------------------------------------------------------------------------

export type CapabilityIcon = 'auto' | 'code' | 'vision' | 'web' | 'image' | 'text';

/**
 * Determine the capability icon category for a model object.
 * Works with both virtual (gpthub:*) and regular models.
 */
export function getCapabilityIcon(model: any): CapabilityIcon {
	const id = (model?.id || '').toLowerCase();

	if (id === VIRTUAL_MODEL_IDS.AUTO) return 'auto';

	const text = `${id} ${(model?.name || '').toLowerCase()}`;
	const caps = model?.info?.meta?.capabilities || {};

	if (caps.image_generation || /\b(image|flux|dall|sdxl|stable.diffusion)\b/.test(text))
		return 'image';
	if (caps.vision || /\b(vision|vl\b|multimodal)\b/.test(text)) return 'vision';
	if (caps.code || /\b(coder|code|program)\b/.test(text)) return 'code';

	return 'text';
}

// ---------------------------------------------------------------------------
// Custom scheme helpers
// ---------------------------------------------------------------------------

export const GPTHUB_SCHEME = 'gpthub:';
export const MODEL_SELECT_EVENT = 'gpthub:model-select';

/**
 * Check if a URL is a model-select deep link (gpthub://select-model?model=...).
 */
export function isModelSelectUrl(href: string | null | undefined): boolean {
	if (!href) return false;
	return href.startsWith('gpthub://select-model');
}
