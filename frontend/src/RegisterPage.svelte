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
      error = e instanceof Error ? e.message : 'Registration failed'
    } finally {
      loading = false
    }
  }
</script>

<div class="auth-wrap">
  <h2>Create account</h2>
  <input bind:value={username} placeholder="Username" />
  <input bind:value={password} placeholder="Password" type="password" />
  <button on:click={submit} disabled={loading}>{loading ? 'Creating...' : 'Register'}</button>
  <button class="link" on:click={() => push('/login')}>Back to login</button>
  {#if error}<p class="error">{error}</p>{/if}
</div>
