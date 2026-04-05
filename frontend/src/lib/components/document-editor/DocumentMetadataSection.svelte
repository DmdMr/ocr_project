<script lang="ts">
  import { createEventDispatcher } from "svelte"
  import type { CardCustomFieldSetting, Document } from "../../types"
  import { tagHue } from "../../tagColors"

  export let doc: Document
  export let customFieldSettings: CardCustomFieldSetting[] = []
  export let customFieldDraft: Record<string, string | number | string[] | null> = {}
  export let customFieldsSaving = false

  const dispatch = createEventDispatcher<{
    saveCustomFields: void
    customFieldInput: { fieldName: string; value: string }
    manageTags: void
    deleteDoc: void
    addImages: Event
  }>()

  function peopleDraftValue(value: string | number | string[] | null | undefined) {
    if (Array.isArray(value)) return value.join(", ")
    if (value === null || value === undefined) return ""
    return String(value)
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
    <button class="primary" disabled={customFieldsSaving} on:click={() => dispatch("saveCustomFields")}>Сохранить поля</button>
  </div>
  <div class="fields-grid">
    {#each customFieldSettings as field}
      <label>
        <span>{field.name}</span>
        <input
          type={field.type === "number" ? "number" : "text"}
          value={field.type === "people" ? peopleDraftValue(customFieldDraft[field.name]) : (customFieldDraft[field.name] ?? "")}
          on:input={(event) => dispatch("customFieldInput", { fieldName: field.name, value: (event.target as HTMLInputElement).value })}
        />
      </label>
    {/each}
  </div>

  <div class="section-head">
    <h3>Изображения</h3>
    <label class="btn">
      Добавить изображения
      <input type="file" accept="image/png,image/jpeg,image/jpg" multiple hidden on:change={(event) => dispatch("addImages", event)} />
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
</style>
