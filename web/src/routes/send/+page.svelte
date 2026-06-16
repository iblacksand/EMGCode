<script>
	import { onMount } from 'svelte';

	let value = $state('');
	let socket;

	onMount(() => {
		socket = new WebSocket(
			`${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}/ws/send`
		);

		return () => socket?.close();
	});

	function sendValue() {
		if (socket?.readyState === WebSocket.OPEN) {
			socket.send(value);
			value = '';
		}
	}
</script>

<article>
	<h2>Send Value</h2>

	<input type="number" bind:value placeholder="Enter a number" />

	<button onclick={sendValue}> Send </button>
</article>
