<script lang="ts">
    import { createEventDispatcher } from "svelte"
    import { language, setLanguage, t, type Language } from "../i18n"

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

    function chooseLanguage(nextLanguage: Language) {
        setLanguage(nextLanguage)
    }
</script>
<div class="sidebar-block">
    <section class="sidebar-section">
      <div class="sidebar-title">{$t("language.title")}</div>
      <div class="language-actions" role="group" aria-label={$t("language.title")}>
        <button class:active={$language === "ru"} on:click={() => chooseLanguage("ru")}>{$t("language.ru")}</button>
        <button class:active={$language === "en"} on:click={() => chooseLanguage("en")}>{$t("language.en")}</button>
      </div>
    </section>

    <section class="sidebar-section">
      <div class="sidebar-title">{$t("sidebar.userInfo")}</div>
      <div class="user-line">
        {#if isAuthenticated}
          {$t("sidebar.signedInAs")} <strong>{currentUsername}</strong> · {$t("sidebar.role")}: <strong>{role}</strong>
        {:else}
          {$t("sidebar.browsingAsViewer")}
        {/if}
      </div>
      <div class="sidebar-actions compact">
        {#if isAuthenticated}
          <button on:click={() => dispatch("logout")}>{$t("sidebar.logout")}</button>
        {:else}
          <button on:click={() => dispatch("navigateLogin")}>{$t("auth.signIn")}</button>
        {/if}
      </div>
    </section>


    <section class="sidebar-section">
      <div class="sidebar-title">{$t("sidebar.documents")}</div>
      <div class="sidebar-actions">
        <button on:click={() => dispatch("navigateArchive")}>{$t("sidebar.archive")}</button>
        {#if role === "admin"}
          <button on:click={() => dispatch("navigateSettings")}>{$t("sidebar.fieldsSettings")}</button>
        {/if}
      </div>
    </section>

    {#if role === "admin"}
      <section class="sidebar-section">
        <div class="sidebar-title">{$t("sidebar.adminPanel")}</div>
        <div class="sidebar-actions">
          <button on:click={() => dispatch("navigateAdminUsers")}>{$t("sidebar.users")}</button>
          <button on:click={() => dispatch("navigateActivity")}>{$t("sidebar.activity")}</button>
        </div>
      </section>
    {/if}
</div>

<style>
.sidebar-block {
    text-align: left;
    display: grid;
    gap: 18px;
}

.sidebar-section {
    display: grid;
    gap: 10px;
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

.sidebar-actions,
.language-actions {
    display: grid;
    gap: 8px;
}

.language-actions {
    grid-template-columns: 1fr 1fr;
}

.language-actions button.active {
    border-color: var(--accent);
    font-weight: 700;
}

.sidebar-actions.compact {
    gap: 6px;
}

.sidebar-actions :global(button) {
    width: 100%;
    text-align: left;
}
</style>
