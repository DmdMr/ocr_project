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
      error = e instanceof Error ? e.message : 'Login failed'
    } finally {
      loading = false
    }
  }
</script>

<div class="auth-wrap">
  <h2>Login</h2>
  <input bind:value={username} placeholder="Username" />
  <input bind:value={password} placeholder="Password" type="password" />
  <button on:click={submit} disabled={loading}>{loading ? 'Logging in...' : 'Login'}</button>
  <button class="link" on:click={() => push('/register')}>Create account</button>
  {#if error}<p class="error">{error}</p>{/if}
</div>
