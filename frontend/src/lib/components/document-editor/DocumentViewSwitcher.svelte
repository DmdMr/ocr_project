<script lang="ts">
  export let documentId: string
  export let activeView: "classic" | "editor" = "editor"

  const classicHref = `#/documents/${documentId}/classic`
  const editorHref = `#/documents/${documentId}/editor`
</script>

<nav class="view-switcher" aria-label="Переключение режима документа">
  <a class:active={activeView === "classic"} href={classicHref}>Classic view</a>
  <a class:active={activeView === "editor"} href={editorHref}>New doc view</a>
</nav>

<style>
  .view-switcher {
    display: inline-flex;
    border: 1px solid var(--border);
    border-radius: 999px;
    padding: 3px;
    background: var(--surface);
    gap: 4px;
  }

  .view-switcher a {
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 0.85rem;
    text-decoration: none;
    color: var(--muted);
    font-weight: 600;
  }

  .view-switcher a.active {
    background: color-mix(in srgb, var(--accent), transparent 82%);
    color: var(--text);
  }
</style>
