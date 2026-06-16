<script>
	import { onMount } from 'svelte';

	let value = $state('Waiting...');

	onMount(() => {
		const socket = new WebSocket(
			`${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/receive`
		);

		socket.onmessage = (event) => {
			value = event.data;
		};

		return () => socket.close();
	});
</script>

<div class="receiver">
	<div class="value">{value}</div>
</div>

<style>
	.receiver {
		display: flex;
		justify-content: center;
		align-items: center;
		min-height: 80vh;
	}

	.value {
		font-size: 8rem;
		font-weight: bold;
		text-align: center;
	}
</style>
