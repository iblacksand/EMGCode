<script lang="ts">
	import MeasurementModal from '$lib/components/MeasurementView.svelte';

	let measurements = $state(128);
	let measurements_today = $state(12);
	let muscle_activation = $state(0.958);

	let modalOpen = $state(false);
	let selectedMeasurement = $state('');

	function openMeasurement(id: string) {
		selectedMeasurement = id;
		modalOpen = true;
	}
</script>

<main class="hero">
	<div>
		<h1>EMG Dashboard</h1>

		<div class="stats-grid">
			<article>
				<h3>{measurements}</h3>
				<p>Total Measurements</p>
			</article>

			<article>
				<h3>{`${Math.round(muscle_activation * 100)}`}%</h3>
				<p>Average Muscle Activation</p>
			</article>

			<article>
				<h3>{measurements_today}</h3>
				<p>{measurements_today > 1 ? 'Measurements' : 'Measurement'} Today</p>
			</article>
		</div>

		<table class="emg-table">
			<thead>
				<tr>
					<th>ID</th>
					<th>Muscle</th>
					<th>Timestamp</th>
					<th>Strength (RMS μV)</th>
					<th>Dominant Freq (Hz)</th>
					<th>Signal Quality</th>
					<th>Fatigue Index</th>
					<th>Status</th>
					<th></th>
				</tr>
			</thead>
			<tbody>
				<tr>
					<td>EMG-1024</td>
					<td>Biceps Brachii</td>
					<td>2026-06-05 09:14</td>
					<td>84.2</td>
					<td>72</td>
					<td>98%</td>
					<td>0.12</td>
					<td>Normal</td>
					<td><button class="outline" onclick={() => openMeasurement('1024')}> View </button></td>
				</tr>
			</tbody>
		</table>
	</div>
	<MeasurementModal open={modalOpen} measurementId={selectedMeasurement} />
</main>

<style>
	.hero {
		min-height: 100vh;
		display: grid;
		place-items: center;
		text-align: center;
		padding: 2rem;
	}

	.emg-table {
		/* margin-right: 5%; */
		padding: 15%;
	}

	.hero h1 {
		font-size: 30pt;
		margin-bottom: 0.5rem;
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(3, 1fr);
		gap: 1rem;
	}

	.stats-grid article {
		text-align: center;
	}

	.stats-grid h3 {
		margin-bottom: 0.25rem;
		font-size: 2rem;
	}

	.stats-grid p {
		margin: 0;
		opacity: 0.7;
	}

	@media (max-width: 768px) {
		.stats-grid {
			grid-template-columns: 1fr;
		}
	}

	/* .hero p {
        font-size: 1.25rem;
        opacity: 0.8;
        margin-bottom: 2rem;
    } */
</style>
