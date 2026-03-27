<script lang="ts">
    import { createEventDispatcher } from "svelte"

    const dispatch = createEventDispatcher<{
        navigateAbout: void
        navigateArchive: void
        navigateAssistant: void
        navigateSettings: void
    }>()
</script>

<div class="sidebar-block">
    <div class="sidebar-title">Рабочее пространство</div>
    <div class="sidebar-actions">
        <button on:click={() => dispatch("navigateAbout")}>О проекте</button>
        <button on:click={() => dispatch("navigateArchive")}>Архив</button>
        <button class="primary" on:click={() => dispatch("navigateAssistant")}>Чат-помощник</button>
        <button on:click={() => dispatch("navigateSettings")}>Настройки полей</button>
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

.sidebar-actions {
    display: grid;
    gap: 8px;
}

.sidebar-actions :global(button) {
    width: 100%;
    text-align: left;
}
</style>
