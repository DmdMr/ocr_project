<script lang="ts">
    import { createEventDispatcher } from "svelte"

    export let currentUsername: string | null = null

    const dispatch = createEventDispatcher<{
        navigateAbout: void
        navigateArchive: void
        navigateAssistant: void
        navigateSettings: void
        logout: void
    }>()
</script>

<div class="sidebar-block">
    <div class="sidebar-title">Рабочее пространство</div>
    {#if currentUsername}
      <div class="user-line">Signed in as <strong>{currentUsername}</strong></div>
    {/if}
    <div class="sidebar-actions">
        <button on:click={() => dispatch("navigateAbout")}>О проекте</button>
        <button on:click={() => dispatch("navigateArchive")}>Архив</button>
        <button class="primary" on:click={() => dispatch("navigateAssistant")}>Чат-помощник</button>
        <button on:click={() => dispatch("navigateSettings")}>Настройки полей</button>
        <button on:click={() => dispatch("logout")}>Logout</button>
    </div>
</div>

<style>
.sidebar-block {
    text-align: left;
}

.sidebar-title {
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 10px;
    color: var(--text-muted);
}

.user-line {
    margin-bottom: 10px;
    font-size: 0.9rem;
}

.sidebar-actions {
    display: grid;
    gap: 8px;
}

.sidebar-actions :global(button) {
    width: 100%;
    text-align: left;
}
</style>
