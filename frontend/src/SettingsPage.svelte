<script lang="ts">
  import { onMount } from 'svelte'
  import { push } from 'svelte-spa-router'
  import { createCardField, deleteCardField, getSettings } from './lib/api'
  import { isAdmin } from './lib/auth'
  import type { CardCustomFieldSetting } from './lib/types'

  let fields: CardCustomFieldSetting[] = []
  let loading = true
  let error = ''
  let newName = ''
  let newType: 'text' | 'number' | 'people' = 'text'
  let saving = false

  async function loadSettings() {
    loading = true
    error = ''
    try {
      const data = await getSettings()
      fields = data.fields_for_cards ?? []
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load settings'
    } finally {
      loading = false
    }
  }

  async function addField() {
    const name = newName.trim().toLowerCase()
    if (!name || saving) return

    saving = true
    error = ''
    try {
      await createCardField(name, newType)
      newName = ''
      await loadSettings()
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to add field'
    } finally {
      saving = false
    }
  }

  async function removeField(name: string) {
    if (!confirm(`Удалить поле "${name}"?`)) return
    try {
      await deleteCardField(name)
      await loadSettings()
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to delete field'
    }
  }

  onMount(loadSettings)
</script>

<div class="panel settings-page">
  <div class="settings-header">
    <h2>Настройки карточек</h2>
    <button on:click={() => push('/')}>Назад</button>
  </div>

  {#if !$isAdmin}
    <p class="error">Доступно только администраторам.</p>
  {:else}
  <p class="muted">Поля ниже добавляются в каждую карточку документа.</p>

  <div class="add-field-row">
    <input bind:value={newName} placeholder="Название поля (например hours-to-make)" />
    <select bind:value={newType}>
      <option value="text">Текст</option>
      <option value="number">Число</option>
      <option value="people">Люди</option>
    </select>
    <button class="primary" on:click={addField} disabled={saving || !newName.trim()}>
      {saving ? 'Добавление...' : 'Добавить'}
    </button>
  </div>

  {#if error}
    <p class="error">{error}</p>
  {/if}

  {#if loading}
    <p class="muted">Загрузка...</p>
  {:else if !fields.length}
    <p class="muted">Пока нет пользовательских полей.</p>
  {:else}
    <div class="fields-list">
      {#each fields as field}
        <div class="field-item">
          <div>
            <strong>{field.name}</strong>
            <span>{field.type}</span>
          </div>
          <button class="danger" on:click={() => removeField(field.name)}>Удалить</button>
        </div>
      {/each}
    </div>
  {/if}
  {/if}
</div>

<style>
  .settings-page { padding: 16px; }
  .settings-header { display: flex; justify-content: space-between; align-items: center; }
  .add-field-row { display: grid; grid-template-columns: 1fr 130px auto; gap: 8px; margin: 12px 0; }
  .fields-list { display: grid; gap: 8px; }
  .field-item { display: flex; justify-content: space-between; align-items: center; border: 1px solid var(--border); border-radius: var(--radius-md); padding: 10px; }
  .field-item span { margin-left: 8px; color: var(--text-muted); }
  .muted { color: var(--text-muted); }
  .error { color: var(--danger); }
</style>
