<script lang="ts">
  import { onMount } from 'svelte'
  import { push } from 'svelte-spa-router'
  import { createCardField, deleteCardField, getCardFields } from './lib/api'
  import { isAdmin } from './lib/auth'
  import { t } from './lib/i18n'
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
      fields = await getCardFields()
    } catch (e) {
      error = e instanceof Error ? e.message : $t('settings.loadError')
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
      error = e instanceof Error ? e.message : $t('settings.addError')
    } finally {
      saving = false
    }
  }

  async function removeField(name: string) {
    if (!confirm($t('settings.deleteConfirm', { name }))) return
    try {
      await deleteCardField(name)
      await loadSettings()
    } catch (e) {
      error = e instanceof Error ? e.message : $t('settings.deleteError')
    }
  }

  onMount(loadSettings)
</script>

<div class="panel settings-page">
  <div class="settings-header">
    <h2>{$t('settings.title')}</h2>
    <button on:click={() => push('/')}>{$t('common.back')}</button>
  </div>

  {#if !$isAdmin}
    <p class="error">{$t('settings.adminOnly')}</p>
  {:else}
  <p class="muted">{$t('settings.help')}</p>

  <div class="add-field-row">
    <input bind:value={newName} placeholder={$t('settings.fieldPlaceholder')} />
    <select bind:value={newType}>
      <option value="text">text</option>
      <option value="number">number</option>
      <option value="people">people</option>
    </select>
    <button on:click={addField} disabled={saving}>{saving ? $t('common.saving') : $t('settings.add')}</button>
  </div>

  {#if error}<p class="error">{error}</p>{/if}

  {#if loading}
    <p>{$t('common.loading')}</p>
  {:else}
    <div class="fields-list">
      {#each fields as field}
        <div class="field-item">
          <div>
            <strong>{field.name}</strong>
            <span>{field.type}</span>
          </div>
          <button class="danger" on:click={() => removeField(field.name)}>{$t('common.delete')}</button>
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
