<script lang="ts">
  import { push } from 'svelte-spa-router'
  import { continueAsViewer, login } from './lib/auth'

  let username = ''
  let password = ''
  let error = ''
  let loading = false

  async function submit() {
    error = ''
    loading = true
    try {
      await login(username, password)
      push('/')
    } catch (e) {
      error = e instanceof Error ? e.message : 'Ошибка входа'
    } finally {
      loading = false
    }
  }

  async function openAsViewer() {
    error = ''
    loading = true
    try {
      // Viewer mode uses the existing guest role instead of creating a fake
      // admin/editor session, so write actions remain disabled and protected.
      await continueAsViewer()
      push('/')
    } catch (e) {
      error = e instanceof Error ? e.message : 'Не удалось открыть гостевой режим'
    } finally {
      loading = false
    }
  }
</script>

<div class="auth-wrap">
  <h2>Вход</h2>
  <input bind:value={username} placeholder="Имя пользователя" />
  <input bind:value={password} placeholder="Пароль" type="password" />
  <button on:click={submit} disabled={loading}>{loading ? 'Входим...' : 'Войти'}</button>
  <button class="viewer-button" type="button" on:click={openAsViewer} disabled={loading}>Continue as Viewer</button>
  <p class="viewer-note">Viewer mode lets you browse, search, filter, open documents, and read OCR text without edit permissions.</p>
  {#if error}<p class="error">{error}</p>{/if}
</div>
