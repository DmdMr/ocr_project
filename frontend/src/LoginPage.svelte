<script lang="ts">
  import { push } from 'svelte-spa-router'
  import { login } from './lib/auth'

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
</script>

<div class="auth-wrap">
  <h2>Вход</h2>
  <input bind:value={username} placeholder="Имя пользователя" />
  <input bind:value={password} placeholder="Пароль" type="password" />
  <button on:click={submit} disabled={loading}>{loading ? 'Входим...' : 'Войти'}</button>
  <button class="link" on:click={() => push('/register')}>Создать аккаунт</button>
  {#if error}<p class="error">{error}</p>{/if}
</div>
