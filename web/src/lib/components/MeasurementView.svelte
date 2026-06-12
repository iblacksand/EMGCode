<script lang="ts">
    let {open, measurementId} = $props();
	// let open = $state(false);
	// let measurementId = $state('');

	function close() {
		open = false;
	}
</script>

{#if open}
	<dialog open>
		<article>
			<header>
				<button
					aria-label="Close"
					rel="prev"
					onclick={close}
				></button>

				<p>
					<strong>EMG Measurement {measurementId}</strong>
				</p>
			</header>

			<p>
				This is dummy test data for the EMG dashboard.
			</p>

			<ul>
				<li>Muscle: Biceps Brachii</li>
				<li>Timestamp: 2026-06-05 09:14</li>
				<li>Strength (RMS μV): 84.2</li>
				<li>Dominant Frequency: 72 Hz</li>
				<li>Signal Quality: 98%</li>
				<li>Fatigue Index: 0.12</li>
				<li>Status: Normal</li>
			</ul>
		</article>
	</dialog>
{/if}