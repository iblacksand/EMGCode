<script lang="ts">
	import { onMount } from 'svelte';

	interface Session {
		session_id: string;
		created_datetime: string;
		batch_count: number;
		sample_count: number;
		calibrated: boolean;
		calibration_normal_peak: number | null;
		good_flex_count: number;
		normal_flex_count: number;
		poor_flex_count: number;
	}

	let sessions = $state<Session[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);

	async function loadSessions() {
		try {
			loading = true;
			const response = await fetch('/api/list_sessions');
			if (!response.ok) throw new Error('Failed to load sessions');
			sessions = await response.json();
			error = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		loadSessions();
	});

	function formatDateTime(isoString: string | null): string {
		if (!isoString) return 'N/A';
		return new Date(isoString).toLocaleString();
	}
</script>

<main class="container">
	<h1>EMG Sessions</h1>

	{#if loading}
		<p>Loading sessions...</p>
	{:else if error}
		<article class="error">
			<h2>Error</h2>
			<p>{error}</p>
			<button onclick={loadSessions}>Retry</button>
		</article>
	{:else if sessions.length === 0}
		<article>
			<p>No sessions found. Start a new session from your Arduino device.</p>
		</article>
	{:else}
		<table>
			<thead>
				<tr>
					<th>Date</th>
					<th>Status</th>
					<th>Normal Peak</th>
					<th>Good Flexes</th>
					<th>Normal Flexes</th>
					<th>Poor Flexes</th>
					<th>Samples</th>
					<th>Actions</th>
				</tr>
			</thead>
			<tbody>
				{#each sessions as session}
					<tr>
						<td>{formatDateTime(session.created_datetime)}</td>
						<td>
							{#if session.calibrated}
								<span style="color: var(--pico-ins-color);">Calibrated</span>
							{:else}
								<span style="color: var(--pico-del-color);">Not Calibrated</span>
							{/if}
						</td>
						<td>{session.calibration_normal_peak?.toFixed(2) ?? 'N/A'}</td>
						<td>{session.good_flex_count}</td>
						<td>{session.normal_flex_count}</td>
						<td>{session.poor_flex_count}</td>
						<td>{session.sample_count.toLocaleString()}</td>
						<td>
							<a href="/sessions/{session.session_id}/" role="button" class="secondary">View</a>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}

	<nav>
		<a href="/" role="button" class="secondary">Back to Home</a>
		<button onclick={loadSessions}>Refresh</button>
	</nav>
</main>

<style>
	.error {
		background: var(--pico-del-color);
		color: white;
	}

	table {
		font-size: 0.9rem;
	}

	nav {
		display: flex;
		gap: 1rem;
		margin-top: 2rem;
	}
</style>
