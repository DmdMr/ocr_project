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
    <section class="sidebar-section">
      <div class="sidebar-title">User Info</div>
      <div class="user-line">
        {#if isAuthenticated}
          Signed in as <strong>{currentUsername}</strong> · role: <strong>{role}</strong>
        {:else}
          Browsing as <strong>viewer</strong>
        {/if}
      </div>
      <div class="sidebar-actions compact">
        {#if isAuthenticated}
          <button on:click={() => dispatch("logout")}>Logout</button>
        {:else}
          <button on:click={() => dispatch("navigateLogin")}>Sign in</button>
        {/if}
      </div>
    </section>

    <section class="sidebar-section">
      <div class="sidebar-title">Primary Actions</div>
      <div class="sidebar-actions">
        <button class="primary" on:click={() => dispatch("navigateAssistant")}>Чат-помощник</button>
        <button on:click={() => dispatch("navigateAbout")}>О проекте</button>
      </div>
    </section>

    <section class="sidebar-section">
      <div class="sidebar-title">Documents</div>
      <div class="sidebar-actions">
        <button on:click={() => dispatch("navigateArchive")}>Архив</button>
        {#if role === "admin"}
          <button on:click={() => dispatch("navigateSettings")}>Настройки полей</button>
        {/if}
      </div>
    </section>

    <section class="sidebar-section">
      <div class="sidebar-title">Tags Block</div>
      <div class="sidebar-actions">
        <button on:click={() => dispatch("navigateArchive")}>Управление тегами</button>
      </div>
    </section>

    {#if role === "admin"}
      <section class="sidebar-section">
        <div class="sidebar-title">Admin Panel</div>
        <div class="sidebar-actions">
          <button on:click={() => dispatch("navigateAdminUsers")}>Пользователи</button>
          <button on:click={() => dispatch("navigateActivity")}>Активность</button>
        </div>
      </section>
    {/if}
</div>

<style>
.sidebar-block {
    text-align: left;
    display: grid;
    gap: 16px;
}

.sidebar-section {
    display: grid;
    gap: 8px;
}

.sidebar-title {
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 2px;
    color: var(--text-muted);
}

.user-line {
    font-size: 0.9rem;
}

.sidebar-actions {
    display: grid;
    gap: 8px;
}

.sidebar-actions.compact {
    gap: 6px;
}

.sidebar-actions :global(button) {
    width: 100%;
    text-align: left;
}
</style>
