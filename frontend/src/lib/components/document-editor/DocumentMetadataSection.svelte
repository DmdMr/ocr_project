<script lang="ts">
  import { tick } from "svelte"
  import { createEventDispatcher } from "svelte"
  import type { CardCustomFieldSetting, Document } from "../../types"
  import { tagHue } from "../../tagColors"
  import { t } from "../../i18n"

  export let doc: Document
  export let customFieldSettings: CardCustomFieldSetting[] = []
  export let customFieldDraft: Record<string, string | number | string[] | null> = {}
  export let customFieldsStatus: "idle" | "saving" | "saved" | "error" = "idle"
  export let canEdit = true
  export let canCreateFields = false

  type CustomFieldType = "text" | "number" | "people"

  let creatingField = false
  let newFieldName = ""
  let newFieldValue = ""
  let newFieldType: CustomFieldType = "text"
  let newFieldError = ""
  let newFieldSaving = false
  let newFieldNameInput: HTMLInputElement | null = null
  export let onCreateCustomField: (payload: { name: string; value: string; type: CustomFieldType }) => Promise<void> = async () => {}

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

  async function startCustomFieldCreation() {
    if (!canEdit || !canCreateFields) return
    creatingField = true
    newFieldName = ""
    newFieldValue = ""
    newFieldType = "text"
    newFieldError = ""

    // The draft row is rendered before anything is saved so users can enter the
    // new field name and value without leaving the document editor.
    await tick()
    newFieldNameInput?.focus()
  }

  async function submitCustomFieldCreation() {
    if (!canEdit || !canCreateFields || newFieldSaving) return
    const trimmedName = newFieldName.trim()
    if (!trimmedName) {
      newFieldError = $t("metadata.fieldNameRequired")
      await tick()
      newFieldNameInput?.focus()
      return
    }

    newFieldSaving = true
    newFieldError = ""

    try {
      // Parent persists in two steps: create the field definition through the
      // existing settings endpoint, then save this document's custom_fields value.
      await onCreateCustomField({
        name: trimmedName,
        value: newFieldValue,
        type: newFieldType
      })
      creatingField = false
      newFieldName = ""
      newFieldValue = ""
      newFieldType = "text"
    } catch (error) {
      newFieldError = error instanceof Error ? error.message : $t("metadata.createFieldError")
    } finally {
      newFieldSaving = false
    }
  }

  function cancelCustomFieldCreation() {
    creatingField = false
    newFieldName = ""
    newFieldValue = ""
    newFieldType = "text"
    newFieldError = ""
  }
</script>

<section class="panel metadata">
  <div class="metadata-block">
    <div class="section-head">
      <h3>{$t("metadata.tags")}</h3>
      {#if canEdit}
        <button on:click={() => dispatch("manageTags")}>{$t("metadata.manage")}</button>
      {/if}
    </div>
    <div class="tags">
      {#if doc.tags?.length}
        {#each doc.tags as tag}
          <span class="tag tag-colored" style={`--tag-hue: ${tagHue(tag)}`}>{tag}</span>
        {/each}
      {:else}
        <span class="muted">{$t("metadata.noTags")}</span>
      {/if}
    </div>
  </div>

  <div class="metadata-block">
    <div class="section-head">
      <h3>{$t("metadata.customFields")}</h3>
      <div class="field-actions">
        {#if canEdit}
          <button type="button" on:click={startCustomFieldCreation} disabled={!canCreateFields || creatingField} title={canCreateFields ? $t("metadata.createFieldTitle") : $t("metadata.adminOnlyFieldCreate")}>{$t("metadata.addField")}</button>
        {/if}
        <span class="save-state" data-state={customFieldsStatus}>
          {#if customFieldsStatus === "saving"}{$t("common.saving")}{/if}
          {#if customFieldsStatus === "saved"}{$t("common.saved")}{/if}
          {#if customFieldsStatus === "error"}{$t("common.error")}{/if}
        </span>
      </div>
    </div>
    <div class="fields-grid">
      {#if creatingField}
        <div class="new-field-card">
          <label>
            <span>{$t("metadata.fieldName")}</span>
            <input
              bind:this={newFieldNameInput}
              bind:value={newFieldName}
              disabled={newFieldSaving}
              placeholder={$t("metadata.fieldNamePlaceholder")}
              on:keydown={(event) => { if (event.key === "Enter") submitCustomFieldCreation() }}
            />
          </label>
          <label>
            <span>{$t("metadata.fieldType")}</span>
            <select bind:value={newFieldType} disabled={newFieldSaving}>
              <option value="text">text</option>
              <option value="number">number</option>
              <option value="people">people</option>
            </select>
          </label>
          <label>
            <span>{$t("metadata.fieldValue")}</span>
            <input
              type={newFieldType === "number" ? "number" : "text"}
              bind:value={newFieldValue}
              disabled={newFieldSaving}
              placeholder={$t("metadata.fieldValuePlaceholder")}
              on:keydown={(event) => { if (event.key === "Enter") submitCustomFieldCreation() }}
            />
          </label>
          {#if newFieldError}
            <p class="field-error">{newFieldError}</p>
          {/if}
          <div class="new-field-actions">
            <button type="button" on:click={submitCustomFieldCreation} disabled={newFieldSaving}>{newFieldSaving ? $t("common.saving") : $t("metadata.saveField")}</button>
            <button type="button" on:click={cancelCustomFieldCreation} disabled={newFieldSaving}>{$t("common.cancel")}</button>
          </div>
        </div>
      {/if}
      {#each customFieldSettings as field}
        <label>
          <span>{field.name}</span>
          <input
            type={field.type === "number" ? "number" : "text"}
            disabled={!canEdit}
            value={field.type === "people" ? peopleDraftValue(customFieldDraft[field.name]) : (customFieldDraft[field.name] ?? "")}
            on:input={(event) => dispatch("customFieldInput", { fieldName: field.name, value: (event.target as HTMLInputElement).value })}
            on:change={(event) => dispatch("customFieldInput", { fieldName: field.name, value: (event.target as HTMLInputElement).value, saveNow: true })}
            on:blur={(event) => dispatch("customFieldInput", { fieldName: field.name, value: (event.target as HTMLInputElement).value, saveNow: true })}
          />
        </label>
      {/each}
    </div>
  </div>

  <div class="metadata-block">
    <div class="section-head">
      <h3>{$t("metadata.images")}</h3>
      {#if canEdit}
        <label class="upload-btn">
          {$t("metadata.addImages")}
          <input type="file" accept="image/png,image/jpeg,image/jpg" multiple hidden on:change={emitSelectedImages} />
        </label>
      {/if}
    </div>
  </div>
</section>

<style>
  .metadata { padding: 16px; display: grid; gap: 12px; }
  .metadata-block { display: grid; gap: 8px; }
  .section-head { display: flex; justify-content: space-between; gap: 10px; align-items: center; }
  .field-actions { display: flex; align-items: center; gap: 8px; }
  .tags { display: flex; flex-wrap: wrap; gap: 8px; }
  .fields-grid { display: grid; gap: 8px; }
  .fields-grid label { display: grid; gap: 4px; }
  .new-field-card { border: 1px dashed #94a3b8; border-radius: 12px; padding: 10px; display: grid; gap: 8px; background: rgba(148, 163, 184, 0.08); }
  .new-field-actions { display: flex; gap: 8px; flex-wrap: wrap; }
  .field-error { margin: 0; color: #ef4444; font-size: 0.86rem; }
  .muted { color: var(--muted); }
  .save-state { font-size: 0.82rem; color: var(--muted); min-height: 18px; }
  .save-state[data-state="saving"] { color: #3b82f6; }
  .save-state[data-state="saved"] { color: #16a34a; }
  .save-state[data-state="error"] { color: #ef4444; }
</style>
