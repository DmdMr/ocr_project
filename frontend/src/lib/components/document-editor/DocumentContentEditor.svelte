<script lang="ts">
  export let value = ""
  export let editing = false
  export let onToggleEdit: () => void
  export let onSave: () => void
</script>

<section class="content panel">
  <div class="content-toolbar">
    <h2>Recognized text</h2>
    <div class="actions">
      {#if editing}
        <button class="primary" on:click={onSave}>Сохранить OCR текст</button>
      {/if}
      <button on:click={onToggleEdit}>{editing ? "Просмотр" : "Редактировать"}</button>
    </div>
  </div>

  {#if editing}
    <textarea bind:value class="editor"></textarea>
  {:else}
    <article class="preview">{value || "Пусто"}</article>
  {/if}
</section>

<style>
  .content { padding: 20px; min-height: 320px; }
  .content-toolbar { display: flex; justify-content: space-between; gap: 10px; align-items: center; margin-bottom: 12px; }
  .actions { display: flex; gap: 8px; }
  .editor {
    width: 100%;
    min-height: 420px;
    resize: vertical;
    font-size: 1rem;
    line-height: 1.6;
    padding: 12px;
  }
  .preview { white-space: pre-wrap; line-height: 1.65; min-height: 240px; }
</style>
