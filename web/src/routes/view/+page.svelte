<script lang="ts">

let measurements = $state(128);
let measurements_today = $state(12);
let muscle_activation = $state(0.958);

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
					<td><a href="/measurement/1024" class="view-btn">View</a></td>
				</tr>

				<tr>
					<td>EMG-1025</td>
					<td>Triceps Brachii</td>
					<td>2026-06-05 09:22</td>
					<td>61.7</td>
					<td>68</td>
					<td>95%</td>
					<td>0.18</td>
					<td>Normal</td>
					<td><a href="/measurement/1025" class="view-btn">View</a></td>
				</tr>

				<tr>
					<td>EMG-1026</td>
					<td>Forearm Flexors</td>
					<td>2026-06-05 09:31</td>
					<td>112.4</td>
					<td>81</td>
					<td>97%</td>
					<td>0.09</td>
					<td>High Activity</td>
					<td><a href="/measurement/1026" class="view-btn">View</a></td>
				</tr>

				<tr>
					<td>EMG-1027</td>
					<td>Quadriceps</td>
					<td>2026-06-05 10:02</td>
					<td>156.8</td>
					<td>95</td>
					<td>93%</td>
					<td>0.27</td>
					<td>Fatiguing</td>
					<td><a href="/measurement/1027" class="view-btn">View</a></td>
				</tr>

				<tr>
					<td>EMG-1028</td>
					<td>Hamstrings</td>
					<td>2026-06-05 10:15</td>
					<td>134.5</td>
					<td>88</td>
					<td>96%</td>
					<td>0.21</td>
					<td>Normal</td>
					<td><a href="/measurement/1028" class="view-btn">View</a></td>
				</tr>

				<tr>
					<td>EMG-1029</td>
					<td>Gastrocnemius</td>
					<td>2026-06-05 10:41</td>
					<td>92.6</td>
					<td>76</td>
					<td>89%</td>
					<td>0.35</td>
					<td>Review</td>
					<td><a href="/measurement/1029" class="view-btn">View</a></td>
				</tr>

				<tr>
					<td>EMG-1030</td>
					<td>Deltoid</td>
					<td>2026-06-05 11:08</td>
					<td>73.1</td>
					<td>70</td>
					<td>99%</td>
					<td>0.11</td>
					<td>Normal</td>
					<td><a href="/measurement/1030" class="view-btn">View</a></td>
				</tr>

				<tr>
					<td>EMG-1031</td>
					<td>Tibialis Anterior</td>
					<td>2026-06-05 11:32</td>
					<td>48.9</td>
					<td>62</td>
					<td>92%</td>
					<td>0.14</td>
					<td>Low Activity</td>
					<td><a href="/measurement/1031" class="view-btn">View</a></td>
				</tr>
			</tbody>
		</table>
	</div>
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
