<script lang="ts">
    import { createEventDispatcher } from "svelte"

    export let currentUsername: string | null = null
    export let role: "viewer" | "editor" | "admin" = "viewer"
    export let isAuthenticated = false

    const dispatch = createEventDispatcher<{
        navigateAbout: void
        navigateArchive: void
        navigateAssistant: void
        navigateSettings: void
        navigateAdminUsers: void
        navigateActivity: void
        navigateLogin: void
        logout: void
    }>()
</script>

<div class="sidebar-block">
    <div class="sidebar-title">Рабочее пространство</div>
    <div class="user-line">
      {#if isAuthenticated}
        Signed in as <strong>{currentUsername}</strong> · role: <strong>{role}</strong>
      {:else}
        Browsing as <strong>viewer</strong>
      {/if}
    </div>
    <div class="sidebar-actions">
        <button on:click={() => dispatch("navigateAbout")}>О проекте</button>
        <button on:click={() => dispatch("navigateArchive")}>Архив</button>
        <button class="primary" on:click={() => dispatch("navigateAssistant")}>Чат-помощник</button>
        {#if role === "admin"}
          <button on:click={() => dispatch("navigateSettings")}>Настройки полей</button>
          <button on:click={() => dispatch("navigateAdminUsers")}>Пользователи</button>
          <button on:click={() => dispatch("navigateActivity")}>Активность</button>
        {/if}
        {#if isAuthenticated}
          <button on:click={() => dispatch("logout")}>Logout</button>
        {:else}
          <button on:click={() => dispatch("navigateLogin")}>Sign in</button>
        {/if}
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
