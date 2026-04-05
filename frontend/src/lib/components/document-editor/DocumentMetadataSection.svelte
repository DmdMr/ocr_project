<script lang="ts">
  import { createEventDispatcher } from "svelte"
  import type { CardCustomFieldSetting, Document } from "../../types"
  import { tagHue } from "../../tagColors"

  export let doc: Document
  export let customFieldSettings: CardCustomFieldSetting[] = []
  export let customFieldDraft: Record<string, string | number | string[] | null> = {}
  export let customFieldsStatus: "idle" | "saving" | "saved" | "error" = "idle"

  const dispatch = createEventDispatcher<{
    customFieldInput: { fieldName: string; value: string; saveNow?: boolean }
    manageTags: void
    deleteDoc: void
    addImages: { files: File[] }
  }>()

  function peopleDraftValue(value: string | number | string[] | null | undefined) {
    if (Array.isArray(value)) return value.join(", ")
    if (value === null || value === undefined) return ""
    return String(value)
  }

  function emitSelectedImages(event: Event) {
    const input = event.target as HTMLInputElement
    const files = Array.from(input.files ?? [])
    dispatch("addImages", { files })
    input.value = ""
  }
</script>

<section class="panel metadata">
  <div class="section-head">
    <h3>Теги</h3>
    <button on:click={() => dispatch("manageTags")}>Управлять</button>
  </div>
  <div class="tags">
    {#if doc.tags?.length}
      {#each doc.tags as tag}
        <span class="tag tag-colored" style={`--tag-hue: ${tagHue(tag)}`}>{tag}</span>
      {/each}
    {:else}
      <span class="muted">Нет тегов</span>
    {/if}
  </div>

  <div class="section-head">
    <h3>Пользовательские поля</h3>
    <span class="save-state" data-state={customFieldsStatus}>
      {#if customFieldsStatus === "saving"}Saving...{/if}
      {#if customFieldsStatus === "saved"}Saved{/if}
      {#if customFieldsStatus === "error"}Error{/if}
    </span>
  </div>
  <div class="fields-grid">
    {#each customFieldSettings as field}
      <label>
        <span>{field.name}</span>
        <input
          type={field.type === "number" ? "number" : "text"}
          value={field.type === "people" ? peopleDraftValue(customFieldDraft[field.name]) : (customFieldDraft[field.name] ?? "")}
          on:input={(event) => dispatch("customFieldInput", { fieldName: field.name, value: (event.target as HTMLInputElement).value })}
          on:blur={(event) => dispatch("customFieldInput", { fieldName: field.name, value: (event.target as HTMLInputElement).value, saveNow: true })}
        />
      </label>
    {/each}
  </div>

  <div class="section-head">
    <h3>Изображения</h3>
    <label class="upload-btn">
      Добавить изображения
      <input type="file" accept="image/png,image/jpeg,image/jpg" multiple hidden on:change={emitSelectedImages} />
    </label>
  </div>

  <div class="section-head">
    <h3>Действия</h3>
    <button class="danger" on:click={() => dispatch("deleteDoc")}>Удалить документ</button>
  </div>
</section>

<style>
  .metadata { padding: 14px; display: grid; gap: 12px; }
  .section-head { display: flex; justify-content: space-between; gap: 10px; align-items: center; }
  .tags { display: flex; flex-wrap: wrap; gap: 8px; }
  .fields-grid { display: grid; gap: 8px; }
  .fields-grid label { display: grid; gap: 4px; }
  .muted { color: var(--muted); }
  .save-state { font-size: 0.82rem; color: var(--muted); min-height: 18px; }
  .save-state[data-state="saving"] { color: #3b82f6; }
  .save-state[data-state="saved"] { color: #16a34a; }
  .save-state[data-state="error"] { color: #ef4444; }
  .upload-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 36px;
    padding: 8px 12px;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--surface-strong);
    cursor: pointer;
    font-weight: 600;
  }
</style>
