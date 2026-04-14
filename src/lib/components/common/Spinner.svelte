<script lang="ts">
	// variant='spin'     — rotating dash (original, used for page/UI loading)
	// variant='progress' — circular fill ring (used for file uploads)
	//   progress: 0-100 → determinate; null → indeterminate traveling arc
	export let className: string = 'size-4';
	export let variant: 'spin' | 'progress' = 'spin';
	export let progress: number | null = null;

	const R = 10;
	const CIRC = 2 * Math.PI * R; // ≈ 62.83

	$: dashOffset = progress !== null ? CIRC * (1 - progress / 100) : 0;
</script>

<div class="flex justify-center text-center">
	{#if variant === 'spin'}
		<svg
			aria-hidden="true"
			class={className}
			viewBox="0 0 24 24"
			fill="currentColor"
			xmlns="http://www.w3.org/2000/svg"
			><style>
				.spinner_ajPY {
					transform-origin: center;
					animation: spinner_AtaB 0.75s infinite linear;
				}
				@keyframes spinner_AtaB {
					100% {
						transform: rotate(360deg);
					}
				}
			</style><path
				d="M12,1A11,11,0,1,0,23,12,11,11,0,0,0,12,1Zm0,19a8,8,0,1,1,8-8A8,8,0,0,1,12,20Z"
				opacity=".25"
			/><path
				d="M10.14,1.16a11,11,0,0,0-9,8.92A1.59,1.59,0,0,0,2.46,12,1.52,1.52,0,0,0,4.11,10.7a8,8,0,0,1,6.66-6.61A1.42,1.42,0,0,0,12,2.69h0A1.57,1.57,0,0,0,10.14,1.16Z"
				class="spinner_ajPY"
			/></svg
		>
	{:else}
		<!-- Circular progress ring -->
		<svg
			aria-hidden="true"
			class={className}
			viewBox="0 0 24 24"
			fill="none"
			xmlns="http://www.w3.org/2000/svg"
		>
			<!-- Background track -->
			<circle cx="12" cy="12" r={R} stroke="currentColor" stroke-width="2.5" opacity="0.2" />

			{#if progress !== null}
				<!-- Determinate: fills from top clockwise -->
				<circle
					cx="12"
					cy="12"
					r={R}
					stroke="currentColor"
					stroke-width="2.5"
					stroke-linecap="round"
					stroke-dasharray={CIRC}
					stroke-dashoffset={dashOffset}
					transform="rotate(-90 12 12)"
					style="transition: stroke-dashoffset 0.25s ease;"
				/>
			{:else}
				<!-- Indeterminate: traveling arc that goes around the circle -->
				<circle
					cx="12"
					cy="12"
					r={R}
					stroke="currentColor"
					stroke-width="2.5"
					stroke-linecap="round"
					class="progress_arc"
				/>
			{/if}
		</svg>
	{/if}
</div>

<style>
	/* Indeterminate arc: a ~30% arc that travels clockwise */
	.progress_arc {
		stroke-dasharray: 20 42.83;
		transform-origin: 12px 12px;
		animation: arc_travel 1.2s linear infinite;
	}
	@keyframes arc_travel {
		from {
			transform: rotate(-90deg);
		}
		to {
			transform: rotate(270deg);
		}
	}
</style>
