<script lang="ts">
  import { t } from "../../i18n"
  export let value = ""
  export let editing = false
  export let canEdit = true
  export let onToggleEdit: () => void
  export let onSave: () => void
</script>

<section class="content panel">
  <div class="content-toolbar">
    <h2>{$t("ocr.title")}</h2>
    <div class="actions">
      {#if canEdit && editing}
        <button class="primary" on:click={onSave}>{$t("ocr.save")}</button>
      {/if}
      {#if canEdit}
        <button on:click={onToggleEdit}>{editing ? $t("ocr.view") : $t("ocr.edit")}</button>
      {/if}
    </div>
  </div>

  {#if editing}
    <textarea bind:value class="editor"></textarea>
  {:else}
    <article class="preview">{value || $t("ocr.empty")}</article>
  {/if}
</section>

<style>
  .content { padding: 16px; min-height: 320px; }
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
