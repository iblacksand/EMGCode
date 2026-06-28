<main class="hero">
	<div>
		<h1>EMG Dashboard</h1>
		<div class="button-group">
			<a href="/sessions/" role="button">View Sessions</a>
			<a href="/live/" role="button">Live Monitor</a>
			<a href="/settings/" role="button" class="secondary">Settings</a>
		</div>
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

	.hero h1 {
		font-size: clamp(3rem, 8vw, 6rem);
		margin-bottom: 2rem;
	}

	.button-group {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		min-width: 250px;
	}
</style>
