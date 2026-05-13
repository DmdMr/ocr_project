<script lang="ts">
  import { push } from 'svelte-spa-router'
  import { continueAsViewer, login } from './lib/auth'
  import { t } from './lib/i18n'

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
      error = e instanceof Error ? e.message : $t('auth.loginError')
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
      error = e instanceof Error ? e.message : $t('auth.viewerError')
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
  <h2>{$t('auth.loginTitle')}</h2>
  <input bind:value={username} placeholder={$t('auth.username')} />
  <input bind:value={password} placeholder={$t('auth.password')} type="password" />
  <button on:click={submit} disabled={loading}>{loading ? $t('auth.signingIn') : $t('auth.signIn')}</button>
  <button class="viewer-button" type="button" on:click={openAsViewer} disabled={loading}>{$t('auth.continueViewer')}</button>
  <p class="viewer-note">{$t('auth.viewerNote')}</p>
  {#if error}<p class="error">{error}</p>{/if}
</div>
