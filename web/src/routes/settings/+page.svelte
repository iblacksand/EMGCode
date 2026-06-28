<script lang="ts">
	import { onMount } from 'svelte';

	let recoveryImprovement = $state(20);
	let poorThresholdPercent = $state(70);
	let loading = $state(true);
	let saving = $state(false);
	let message = $state<string | null>(null);

	async function loadSettings() {
		try {
			loading = true;
			const response = await fetch('/api/settings');
			if (!response.ok) throw new Error('Failed to load settings');
			const data = await response.json();

			recoveryImprovement = (data.good_threshold_multiplier - 1.0) * 100;
			poorThresholdPercent = data.poor_threshold_multiplier * 100;
		} catch (e) {
			message = e instanceof Error ? e.message : 'Error loading settings';
		} finally {
			loading = false;
		}
	}

	async function saveSettings() {
		try {
			saving = true;
			message = null;

			const response = await fetch('/api/update_settings', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					recovery_improvement: recoveryImprovement / 100
				})
			});

			if (!response.ok) throw new Error('Failed to save settings');

			message = 'Settings saved successfully!';
		} catch (e) {
			message = e instanceof Error ? e.message : 'Error saving settings';
		} finally {
			saving = false;
		}
	}

	onMount(() => {
		loadSettings();
	});
</script>

<main class="container">
	<h1>EMG Settings</h1>

	{#if loading}
		<p>Loading settings...</p>
	{:else}
		<!-- <article>
			<p>
				The EMG system uses <strong>calibration</strong> to determine your baseline "normal" flex strength.
				When you start a new session, the Arduino will ask you to perform 3 normal flexes, then calculate
				the average peak value.
			</p>
			<p>Based on this calibrated baseline, the system classifies each flex:</p>
			<ul>
				<li><strong>Good Flex:</strong> Peak ≥ Normal × Good Multiplier</li>
				<li><strong>Normal Flex:</strong> Peak between Poor and Good thresholds</li>
				<li><strong>Poor Flex:</strong> Peak &lt; Normal × Poor Multiplier</li>
			</ul>
		</article> -->

		<article>
			<h2>Good Flex Threshold</h2>
			<p>
				Percentage <strong>above</strong> the calibrated normal peak to be considered a "good" flex.
			</p>

			<label>
				Recovery Improvement (%)
				<input type="number" bind:value={recoveryImprovement} min="0" max="100" step="5" />
			</label>

			<p style="opacity: 0.7; font-size: 0.9rem;">
				Good threshold multiplier: {(1 + recoveryImprovement / 100).toFixed(2)}x
			</p>

			<p style="opacity: 0.7; font-size: 0.9rem;">
				<em>
					Example: If normal peak = 200 and improvement = 20%, then good flexes must be ≥ 240
				</em>
			</p>
		</article>

		<article>
			<h2>Poor Flex Threshold</h2>
			<p>
				Percentage of the calibrated normal peak <strong>below which</strong> a flex is considered "poor".
			</p>

			<label>
				Poor Threshold (%)
				<input type="number" bind:value={poorThresholdPercent} min="0" max="100" step="5" />
			</label>

			<p style="opacity: 0.7; font-size: 0.9rem;">
				Poor threshold multiplier: {(poorThresholdPercent / 100).toFixed(2)}x
			</p>

			<p style="opacity: 0.7; font-size: 0.9rem;">
				<em> Example: If normal peak = 200 and threshold = 70%, then poor flexes are &lt; 140 </em>
			</p>
		</article>

		<article>
			<h2>LED Indicator Colors</h2>
			<ul>
				<li>
					<span style="color: #00ff00;">Green</span> - Good flex (above improvement threshold)
				</li>
				<li>
					<span style="color: #daa520;">Gold</span> - Normal flex (between poor and good thresholds)
				</li>
				<li><span style="color: #ff3232;">Orange-Red</span> - Poor flex (below threshold)</li>
				<li><span style="color: #00ffff;">Cyan (blinking)</span> - Calibrating</li>
				<li><span style="color: #ff0000;">Red</span> - Error/Disconnected</li>
			</ul>
		</article>

		{#if message}
			<article class={message.includes('success') ? 'success' : 'error'}>
				<p>{message}</p>
			</article>
		{/if}

		<button onclick={saveSettings} disabled={saving}>
			{saving ? 'Saving...' : 'Save Settings'}
		</button>
	{/if}

	<nav>
		<a href="/" role="button" class="secondary">Back to Home</a>
	</nav>
</main>

<style>
	.success {
		background: var(--pico-ins-color);
		color: white;
	}

	.error {
		background: var(--pico-del-color);
		color: white;
	}

	nav {
		margin-top: 2rem;
	}

	ul {
		list-style: none;
		padding: 0;
	}

	ul li {
		padding: 0.5rem 0;
		font-size: 1.1rem;
	}
</style>
