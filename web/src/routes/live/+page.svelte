<script lang="ts">
	import { onMount } from 'svelte';
	import * as echarts from 'echarts';

	interface CurrentSession {
		session_id: string;
		calibrated: boolean;
		calibration_normal_peak: number | null;
		good_flex_count: number;
		normal_flex_count: number;
		poor_flex_count: number;
	}

	let value = $state('Waiting...');
	let chartContainer: HTMLDivElement;
	let chart: echarts.ECharts | null = null;
	let dataPoints: Array<[number, number]> = [];
	let dataBuffer: Array<[number, number]> = [];
	let maxDataPoints = 100000;
	let startTime = Date.now();
	let currentSession = $state<CurrentSession | null>(null);
	let sessionCheckInterval: number;
	let chartUpdateInterval: number;

	async function checkCurrentSession() {
		try {
			const response = await fetch('/api/current_session');
			if (response.ok) {
				const data = await response.json();
				currentSession = data;
			}
		} catch (e) {
			console.error('Failed to fetch current session:', e);
		}
	}

	function updateChart() {
		if (!chart || dataBuffer.length === 0) return;

		dataPoints.push(...dataBuffer);
		dataBuffer = [];

		while (dataPoints.length > maxDataPoints) {
			dataPoints.shift();
		}

		chart.setOption(
			{
				series: [
					{
						data: dataPoints
					}
				]
			},
			{
				notMerge: false,
				lazyUpdate: false
			}
		);
	}

	onMount(() => {
		chart = echarts.init(chartContainer);

		const option: echarts.EChartsOption = {
			title: {
				text: 'Live EMG Signal',
				left: 'center'
			},
			tooltip: {
				trigger: 'axis',
				formatter: (params: any) => {
					const data = params[0];
					const time = (data.value[0] / 1000).toFixed(2);
					const val = data.value[1];
					return `Time: ${time}s<br/>Value: ${val}`;
				}
			},
			xAxis: {
				type: 'value',
				name: 'Time (ms)',
				nameLocation: 'middle',
				nameGap: 30,
				boundaryGap: false
			},
			yAxis: {
				type: 'value',
				name: 'Value',
				nameLocation: 'middle',
				nameGap: 40,
				scale: true
			},
			animation: false,
			series: [
				{
					name: 'Signal',
					type: 'line',
					data: dataPoints,
					showSymbol: false,
					lineStyle: {
						width: 1.5,
						color: '#5470c6'
					},
					areaStyle: {
						color: {
							type: 'linear',
							x: 0,
							y: 0,
							x2: 0,
							y2: 1,
							colorStops: [
								{
									offset: 0,
									color: 'rgba(84, 112, 198, 0.5)'
								},
								{
									offset: 1,
									color: 'rgba(84, 112, 198, 0.1)'
								}
							]
						}
					}
				}
			]
		};

		chart.setOption(option);

		const socket = new WebSocket(
			`${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/receive`
		);

		socket.onmessage = (event) => {
			value = event.data;
			const numValue = parseFloat(event.data);

			if (!isNaN(numValue)) {
				const time = Date.now() - startTime;
				dataBuffer.push([time, numValue]);
			}
		};

		checkCurrentSession();
		sessionCheckInterval = setInterval(checkCurrentSession, 2000);
		chartUpdateInterval = setInterval(updateChart, 1000);

		return () => {
			socket.close();
			if (chart) {
				chart.dispose();
			}
			clearInterval(sessionCheckInterval);
			clearInterval(chartUpdateInterval);
		};
	});
</script>

<main class="container">
	<h1>Live EMG Monitor</h1>

	{#if currentSession}
		{#if !currentSession.calibrated}
			<article class="calibration-notice">
				<header>
					<strong>Calibration Required</strong>
				</header>
				<p>
					<strong>Session:</strong>
					{currentSession.session_id.slice(0, 8)}...
				</p>
				<p>Your Arduino device needs to complete calibration before tracking can begin.</p>
				<h4>Instructions:</h4>
				<ol>
					<li>Wait for the cyan blinking LED on your Arduino</li>
					<li>Perform 3 normal muscle flexes (comfortable, consistent strength)</li>
					<li>Wait 1-2 seconds between each flex</li>
					<li>The system will automatically calculate your baseline</li>
				</ol>
				<p style="opacity: 0.7; font-size: 0.9rem;">
					Once calibrated, the LED will change color based on your flex quality.
				</p>
			</article>
		{:else}
			<article class="calibrated">
				<header>
					<strong>Status</strong>
				</header>
				<div class="stats-grid">
					<div>
						<strong>Normal Peak</strong>
						<p class="stat-value">{currentSession.calibration_normal_peak?.toFixed(2)}</p>
					</div>
					<div>
						<strong>Good</strong>
						<p class="stat-value">{currentSession.good_flex_count}</p>
					</div>
					<div>
						<strong>Normal</strong>
						<p class="stat-value">{currentSession.normal_flex_count}</p>
					</div>
					<div>
						<strong>Poor</strong>
						<p class="stat-value">{currentSession.poor_flex_count}</p>
					</div>
				</div>
			</article>
		{/if}
	{:else}
		<article>
			<p>Waiting for Arduino to connect and create a session...</p>
			<p style="opacity: 0.7; font-size: 0.9rem;">
				Make sure your Arduino is powered on and connected to the network.
			</p>
		</article>
	{/if}

	<article>
		<div class="value-display">
			<div class="label">Current Value</div>
			<div class="value">{value}</div>
		</div>
	</article>

	<article>
		<div bind:this={chartContainer} style="width: 100%; height: 400px;"></div>
	</article>

	<nav>
		<a href="/" role="button" class="secondary">Back to Home</a>
		<a href="/sessions/" role="button" class="secondary">View Sessions</a>
	</nav>
</main>

<style>
	.value-display {
		text-align: center;
		padding: 2rem;
	}

	.label {
		font-size: 1rem;
		opacity: 0.7;
		margin-bottom: 0.5rem;
	}

	.value {
		font-size: 4rem;
		font-weight: bold;
		color: var(--pico-primary);
	}

	.calibration-notice {
		background: linear-gradient(135deg, rgba(0, 255, 255, 0.1), rgba(0, 150, 255, 0.1));
		border-left: 4px solid #00bcd4;
	}

	.calibration-notice h4 {
		margin-top: 1rem;
		margin-bottom: 0.5rem;
	}

	.calibration-notice ol {
		margin-left: 1.5rem;
	}

	.calibration-notice ol li {
		margin: 0.5rem 0;
	}

	.calibrated {
		background: linear-gradient(135deg, rgba(76, 175, 80, 0.1), rgba(76, 175, 80, 0.05));
		border-left: 4px solid #4caf50;
	}

	.stats-grid {
		display: grid;
		grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
		gap: 1rem;
		margin-top: 1rem;
	}

	.stats-grid > div {
		text-align: center;
	}

	.stat-value {
		font-size: 2rem;
		font-weight: bold;
		margin: 0.5rem 0 0 0;
		color: var(--pico-primary);
	}

	nav {
		margin-top: 2rem;
		display: flex;
		gap: 1rem;
	}
</style>
