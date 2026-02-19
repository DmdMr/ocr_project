<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte"

    export let imageUrl: string

    const dispatch = createEventDispatcher()

    function close() {
        dispatch("close")
    }

    function handleKey(e: KeyboardEvent) {
        if (e.key === "Escape") close()
    }

    onMount(() => {
        window.addEventListener("keydown", handleKey)
        return () => window.removeEventListener("keydown", handleKey)
    })
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div class="overlay" on:click={close}>
    <img src={imageUrl} alt="preview" on:click|stopPropagation />
    <button class="close" on:click={close}>✕</button>
</div>

<style>
.overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.85);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

img {
    max-width: 90vw;
    max-height: 90vh;
    border-radius: 8px;
}

.close {
    position: fixed;
    top: 20px;
    right: 30px;
    font-size: 28px;
    background: none;
    border: none;
    color: white;
    cursor: pointer;
}
</style>
