<script lang="ts">
  import Router, { push } from 'svelte-spa-router'
  import { onMount } from 'svelte'
  import { get } from 'svelte/store'

  import HomePage from './HomePage.svelte'
  import AboutPage from './AboutPage.svelte'
  import ChatbotPage from './ChatbotPage.svelte'
  import ArchivePage from './ArchivePage.svelte'
  import SettingsPage from './SettingsPage.svelte'
  import LoginPage from './LoginPage.svelte'
  import RegisterPage from './RegisterPage.svelte'
  import { authReady, currentUser, initAuth } from './lib/auth'

  const publicRoutes = new Set(['/login', '/register'])

  const routes = {
    '/': HomePage,
    '/about': AboutPage,
    '/assistant': ChatbotPage,
    '/archive': ArchivePage,
    '/settings': SettingsPage,
    '/login': LoginPage,
    '/register': RegisterPage
  }

  function getCurrentPath() {
    const hash = window.location.hash || '#/'
    const normalized = hash.startsWith('#') ? hash.slice(1) : hash
    return normalized || '/'
  }

  function enforceRoute(path: string) {
    if (!get(authReady)) return
    const user = get(currentUser)
    if (!user && !publicRoutes.has(path)) {
      push('/login')
    } else if (user && publicRoutes.has(path)) {
      push('/')
    }
  }

  onMount(() => {
    const handleHashChange = () => enforceRoute(getCurrentPath())

    initAuth().then(handleHashChange)
    window.addEventListener('hashchange', handleHashChange)

    return () => {
      window.removeEventListener('hashchange', handleHashChange)
    }
  })

  currentUser.subscribe(() => enforceRoute(getCurrentPath()))
</script>

{#if $authReady}
  <Router {routes} />
{:else}
  <div class="auth-wrap"><p>Loading...</p></div>
{/if}
