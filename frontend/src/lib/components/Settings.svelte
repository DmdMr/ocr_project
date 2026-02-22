<script>
import { settings } from "../settings"
let open = false
</script>

<button on:click={() => open = true}>⚙️</button>

{#if open}
<div class="modal">
    <label>
        <input type="checkbox" bind:checked={$settings.showImage}>
        Show Image
    </label>

    <label>
        <input type="checkbox" bind:checked={$settings.showFilename}>
        Show Filename
    </label>

    <label>
        <input type="checkbox" bind:checked={$settings.showTags}>
        Show Tags
    </label>

    <label>
        <input type="checkbox" bind:checked={$settings.showButtons}>
        Show Buttons
    </label>

    <button on:click={() => open = false}>Close</button>
</div>
{/if}