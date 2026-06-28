<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import * as echarts from 'echarts';

	interface SessionData {
		session_id: string;
		created_datetime: string;
		batch_count: number;
		sample_count: number;
		batches: Array<{
			id: number;
			start_micros: number;
			sample_period_us: number;
			sample_count: number;
		}>;
	}

	interface BatchData {
		batch_id: number;
		start_micros: number;
		sample_period_us: number;
		values: number[];
	}

	interface FlexEvent {
		id: number;
		timestamp_micros: number;
		peak_value: number;
		quality: string;
		batch_id: number | null;
	}

	let sessionId = $derived($page.params.session_id);
	let sessionData = $state<SessionData | null>(null);
	let batchData = $state<BatchData[]>([]);
	let flexEvents = $state<FlexEvent[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let chartContainer: HTMLDivElement;
	let chart: echarts.ECharts | null = null;

	async function loadSessionData() {
		try {
			loading = true;

			const [sessionRes, dataRes, flexRes] = await Promise.all([
				fetch(`/api/arduino/session/${sessionId}`),
				fetch(`/api/arduino/session/${sessionId}/data`),
				fetch(`/api/arduino/session/${sessionId}/flexes`)
			]);

			if (!sessionRes.ok || !dataRes.ok) throw new Error('Failed to load session');

			sessionData = await sessionRes.json();
			batchData = await dataRes.json();
			flexEvents = await flexRes.json();

			error = null;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	function renderChart() {
		if (!chartContainer || batchData.length === 0) return;

		if (chart) {
			chart.dispose();
		}

		chart = echarts.init(chartContainer);

		const chartData: Array<[number, number]> = [];
		const goodFlexMarkers: Array<{ coord: [number, number]; value: string }> = [];
		const normalFlexMarkers: Array<{ coord: [number, number]; value: string }> = [];
		const poorFlexMarkers: Array<{ coord: [number, number]; value: string }> = [];

		for (const batch of batchData) {
			const startTime = batch.start_micros / 1000;
			batch.values.forEach((value, idx) => {
				const time = startTime + (idx * batch.sample_period_us) / 1000;
				chartData.push([time, value]);
			});
		}

		flexEvents.forEach((flex) => {
			const time = flex.timestamp_micros / 1000;
			const marker = {
				coord: [time, flex.peak_value] as [number, number],
				value: `${flex.peak_value.toFixed(0)}`
			};

			if (flex.quality === 'good') {
				goodFlexMarkers.push(marker);
			} else if (flex.quality === 'normal') {
				normalFlexMarkers.push(marker);
			} else if (flex.quality === 'poor') {
				poorFlexMarkers.push(marker);
			}
		});

		const option: echarts.EChartsOption = {
			title: {
				text: 'EMG Signal Data',
				left: 'center'
			},
			tooltip: {
				trigger: 'axis',
				formatter: (params: any) => {
					const data = params[0];
					const time = data.value[0].toFixed(2);
					const value = data.value[1];
					return `Time: ${time}ms<br/>Value: ${value}`;
				}
			},
			legend: {
				data: ['Signal', 'Good Flex', 'Normal Flex', 'Poor Flex'],
				top: 30
			},
			xAxis: {
				type: 'value',
				name: 'Time (ms)',
				nameLocation: 'middle',
				nameGap: 30
			},
			yAxis: {
				type: 'value',
				name: 'Value',
				nameLocation: 'middle',
				nameGap: 40
			},
			dataZoom: [
				{
					type: 'inside',
					xAxisIndex: 0,
					start: 0,
					end: 100
				},
				{
					type: 'slider',
					xAxisIndex: 0,
					start: 0,
					end: 100
				}
			],
			series: [
				{
					name: 'Signal',
					type: 'line',
					data: chartData,
					showSymbol: false,
					lineStyle: {
						width: 1,
						color: '#5470c6'
					},
					markPoint: {
						symbol: 'pin',
						symbolSize: 50,
						data: goodFlexMarkers.length > 0 ? goodFlexMarkers : undefined,
						itemStyle: {
							color: '#91cc75'
						},
						label: {
							show: true,
							formatter: '{c}'
						}
					}
				},
				...(normalFlexMarkers.length > 0
					? [
							{
								name: 'Normal Flex',
								type: 'scatter',
								data: normalFlexMarkers.map((m) => m.coord),
								symbolSize: 15,
								itemStyle: {
									color: '#fac858'
								}
							}
						]
					: []),
				...(poorFlexMarkers.length > 0
					? [
							{
								name: 'Poor Flex',
								type: 'scatter',
								data: poorFlexMarkers.map((m) => m.coord),
								symbolSize: 15,
								itemStyle: {
									color: '#ee6666'
								}
							}
						]
					: [])
			]
		};

		chart.setOption(option);
	}

	onMount(() => {
		loadSessionData().then(() => {
			renderChart();
		});

		return () => {
			if (chart) {
				chart.dispose();
			}
		};
	});

	$effect(() => {
		if (!loading && batchData.length > 0) {
			renderChart();
		}
	});

	function formatDateTime(isoString: string | null): string {
		if (!isoString) return 'N/A';
		return new Date(isoString).toLocaleString();
	}
</script>

<main class="container">
	<h1>Session Details</h1>

	{#if loading}
		<p>Loading session data...</p>
	{:else if error}
		<article class="error">
			<h2>Error</h2>
			<p>{error}</p>
			<button onclick={loadSessionData}>Retry</button>
		</article>
	{:else if sessionData}
		<article>
			<header>
				<strong>Session ID:</strong>
				{sessionData.session_id}
			</header>
			<p><strong>Created:</strong> {formatDateTime(sessionData.created_datetime)}</p>
			<p><strong>Total Samples:</strong> {sessionData.sample_count.toLocaleString()}</p>
			<p><strong>Batches:</strong> {sessionData.batch_count}</p>
		</article>

		<article>
			<h2>Flex Statistics</h2>
			<div class="grid">
				<div>
					<h3 style="color: #91cc75;">Good Flexes</h3>
					<p style="font-size: 2rem; font-weight: bold;">
						{flexEvents.filter((f) => f.quality === 'good').length}
					</p>
				</div>
				<div>
					<h3 style="color: #fac858;">Normal Flexes</h3>
					<p style="font-size: 2rem; font-weight: bold;">
						{flexEvents.filter((f) => f.quality === 'normal').length}
					</p>
				</div>
				<div>
					<h3 style="color: #ee6666;">Poor Flexes</h3>
					<p style="font-size: 2rem; font-weight: bold;">
						{flexEvents.filter((f) => f.quality === 'poor').length}
					</p>
				</div>
			</div>
		</article>

		<article>
			<h2>Signal Visualization</h2>
			<div bind:this={chartContainer} style="width: 100%; height: 500px;"></div>
		</article>

		{#if flexEvents.length > 0}
			<article>
				<h2>Flex Events</h2>
				<table>
					<thead>
						<tr>
							<th>Time (ms)</th>
							<th>Peak Value</th>
							<th>Quality</th>
						</tr>
					</thead>
					<tbody>
						{#each flexEvents as flex}
							<tr>
								<td>{(flex.timestamp_micros / 1000).toFixed(2)}</td>
								<td>{flex.peak_value.toFixed(2)}</td>
								<td>
									{#if flex.quality === 'good'}
										<span style="color: #91cc75;">Good</span>
									{:else if flex.quality === 'normal'}
										<span style="color: #fac858;">Normal</span>
									{:else}
										<span style="color: #ee6666;">Poor</span>
									{/if}
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</article>
		{/if}
	{/if}

	<nav>
		<a href="/sessions/" role="button" class="secondary">Back to Sessions</a>
	</nav>
</main>

<style>
	.error {
		background: var(--pico-del-color);
		color: white;
	}

	nav {
		margin-top: 2rem;
	}

	.grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
		gap: 1rem;
	}

	.grid > div {
		text-align: center;
		padding: 1rem;
		border: 1px solid var(--pico-muted-border-color);
		border-radius: var(--pico-border-radius);
	}
</style>
