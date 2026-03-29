<script lang="ts">
  import { push } from 'svelte-spa-router'
  import { register } from './lib/auth'

  let username = ''
  let password = ''
  let error = ''
  let loading = false

  async function submit() {
    error = ''
    loading = true
    try {
      await register(username, password)
      push('/')
    } catch (e) {
      error = e instanceof Error ? e.message : 'Ошибка регистрации'
    } finally {
      loading = false
    }
  }
</script>

<div class="auth-wrap">
  <h2>Регистрация</h2>
  <input bind:value={username} placeholder="Имя пользователя" />
  <input bind:value={password} placeholder="Пароль" type="password" />
  <button on:click={submit} disabled={loading}>{loading ? 'Создаем...' : 'Зарегистрироваться'}</button>
  <button class="link" on:click={() => push('/login')}>Назад ко входу</button>
  {#if error}<p class="error">{error}</p>{/if}
</div>
