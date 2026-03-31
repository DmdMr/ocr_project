<script lang="ts">
  import Router, { location, push } from 'svelte-spa-router'
  import { onMount } from 'svelte'
  import { get } from 'svelte/store'

  import HomePage from './HomePage.svelte'
  import AboutPage from './AboutPage.svelte'
  import ChatbotPage from './ChatbotPage.svelte'
  import ArchivePage from './ArchivePage.svelte'
  import SettingsPage from './SettingsPage.svelte'
  import LoginPage from './LoginPage.svelte'
  import RegisterPage from './RegisterPage.svelte'
  import DocumentPage from './DocumentPage.svelte'
  import { authReady, currentUser, initAuth } from './lib/auth'

  const publicRoutes = new Set(['/login', '/register'])

  const routes = {
    '/': HomePage,
    '/about': AboutPage,
    '/assistant': ChatbotPage,
    '/archive': ArchivePage,
    '/settings': SettingsPage,
    '/login': LoginPage,
    '/register': RegisterPage,
    '/document/:id/:slug': DocumentPage,
    '/document/:id': DocumentPage
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

  onMount(async () => {
    await initAuth()
    enforceRoute(get(location))
  })

  location.subscribe((path) => enforceRoute(path))
  currentUser.subscribe(() => enforceRoute(get(location)))
</script>

{#if $authReady}
  <Router {routes} />
{:else}
  <div class="auth-wrap"><p>Loading...</p></div>
{/if}
