<script lang="ts">
  type ThemeMode = "system" | "light" | "dark"

  export let mode: ThemeMode = "system"
  export let language: "en" | "ru" = "en"

  export let onThemeChange: (theme: ThemeMode) => void
  export let onLanguageChange: (language: "en" | "ru") => void
</script>

<div class="top-controls panel" aria-label="Display controls">
  <select
    class="control-select"
    aria-label="Language"
    value={language}
    on:change={(event) => onLanguageChange((event.currentTarget as HTMLSelectElement).value as "en" | "ru")}
  >
    <option value="en">EN</option>
    <option value="ru">RU</option>
  </select>

  <button
    class:active={mode === "system"}
    aria-label="System theme"
    on:click={() => onThemeChange("system")}
    title="System theme"
  >
    Auto
  </button>

  <button
    class:active={mode === "light"}
    aria-label="Light theme"
    on:click={() => onThemeChange("light")}
    title="Light theme"
  >
    ☀️
  </button>

  <button
    class:active={mode === "dark"}
    aria-label="Dark theme"
    on:click={() => onThemeChange("dark")}
    title="Dark theme"
  >
    🌙
  </button>
</div>

<style>
  .top-controls {
    position: fixed;
    top: 16px;
    right: 16px;
    display: flex;
    gap: 8px;
    align-items: center;
    z-index: 1000;
    padding: 10px;
  }

  .control-select {
    min-width: 74px;
  }

  .top-controls button {
    min-width: 42px;
    padding: 8px 10px;
  }

  .top-controls button.active {
    border-color: color-mix(in srgb, var(--primary), white 18%);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary), transparent 72%);
  }
</style>
