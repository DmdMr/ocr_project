<script lang="ts">
  import { onMount } from "svelte"
  import { push } from "svelte-spa-router"
  import {
    createUserByAdmin,
    getUsers,
    resetUserPasswordByAdmin,
    updateUserByAdmin,
    type AuthUser
  } from "./lib/api"
  import { isAdmin } from "./lib/auth"

  let users: AuthUser[] = []
  let loading = false
  let error = ""
  let success = ""

  let newUsername = ""
  let newPassword = ""
  let newRole: "editor" | "admin" = "editor"
  let newIsActive = true

  async function loadUsers() {
    loading = true
    error = ""
    try {
      users = await getUsers()
    } catch (err) {
      error = err instanceof Error ? err.message : "Не удалось загрузить пользователей"
    } finally {
      loading = false
    }
  }

  async function createUser() {
    if (!newUsername.trim() || !newPassword.trim()) return
    success = ""
    error = ""
    try {
      await createUserByAdmin({
        username: newUsername.trim(),
        password: newPassword,
        role: newRole,
        is_active: newIsActive
      })
      newUsername = ""
      newPassword = ""
      newRole = "editor"
      newIsActive = true
      success = "Пользователь создан"
      await loadUsers()
    } catch (err) {
      error = err instanceof Error ? err.message : "Не удалось создать пользователя"
    }
  }

  async function updateUsername(user: AuthUser) {
    const next = prompt("Новое имя пользователя", user.username ?? "")
    if (!next || next.trim() === (user.username ?? "").trim()) return
    error = ""
    success = ""
    try {
      await updateUserByAdmin(user.id ?? "", { username: next.trim() })
      success = "Имя пользователя обновлено"
      await loadUsers()
    } catch (err) {
      error = err instanceof Error ? err.message : "Не удалось обновить пользователя"
    }
  }

  async function toggleUserActive(user: AuthUser) {
    error = ""
    success = ""
    try {
      await updateUserByAdmin(user.id ?? "", { is_active: !user.is_active })
      success = user.is_active ? "Пользователь деактивирован" : "Пользователь активирован"
      await loadUsers()
    } catch (err) {
      error = err instanceof Error ? err.message : "Не удалось обновить статус пользователя"
    }
  }

  async function changeRole(user: AuthUser, role: "editor" | "admin") {
    if (role === user.role) return
    error = ""
    success = ""
    try {
      await updateUserByAdmin(user.id ?? "", { role })
      success = "Роль пользователя обновлена"
      await loadUsers()
    } catch (err) {
      error = err instanceof Error ? err.message : "Не удалось изменить роль"
    }
  }

  async function resetPassword(user: AuthUser) {
    const nextPassword = prompt(`Новый пароль для ${user.username}`)
    if (!nextPassword) return
    error = ""
    success = ""
    try {
      await resetUserPasswordByAdmin(user.id ?? "", nextPassword)
      success = "Пароль пользователя обновлён"
    } catch (err) {
      error = err instanceof Error ? err.message : "Не удалось обновить пароль"
    }
  }

  onMount(loadUsers)
</script>

<div class="panel admin-users">
  <div class="header">
    <h2>Управление пользователями</h2>
    <button on:click={() => push("/")}>Назад</button>
  </div>

  {#if !$isAdmin}
    <p class="error">Доступно только администраторам.</p>
  {:else}
    <section class="panel create-user">
      <h3>Создать пользователя</h3>
      <div class="create-grid">
        <input bind:value={newUsername} placeholder="Username" />
        <input bind:value={newPassword} placeholder="Password" type="password" />
        <select bind:value={newRole}>
          <option value="editor">editor</option>
          <option value="admin">admin</option>
        </select>
        <label class="inline-check">
          <input type="checkbox" bind:checked={newIsActive} />
          Активен
        </label>
        <button class="primary" on:click={createUser}>Создать</button>
      </div>
    </section>

    {#if success}<p class="success">{success}</p>{/if}
    {#if error}<p class="error">{error}</p>{/if}

    {#if loading}
      <p>Загрузка...</p>
    {:else}
      <div class="users-table-wrap">
        <table class="users-table">
          <thead>
            <tr>
              <th>Username</th>
              <th>Role</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {#each users as user (user.id)}
              <tr>
                <td>{user.username}</td>
                <td>
                  <select
                    value={user.role}
                    on:change={(event) => changeRole(user, (event.target as HTMLSelectElement).value as "editor" | "admin")}
                  >
                    <option value="editor">editor</option>
                    <option value="admin">admin</option>
                  </select>
                </td>
                <td>{user.is_active ? "active" : "inactive"}</td>
                <td>
                  <div class="actions">
                    <button on:click={() => updateUsername(user)}>Переименовать</button>
                    <button on:click={() => resetPassword(user)}>Сменить пароль</button>
                    <button on:click={() => toggleUserActive(user)}>{user.is_active ? "Деактивировать" : "Активировать"}</button>
                  </div>
                </td>
              </tr>
            {/each}
          </tbody>
        </table>
      </div>
    {/if}
  {/if}
</div>

<style>
  .admin-users { padding: 16px; }
  .header { display: flex; justify-content: space-between; align-items: center; }
  .create-user { margin-top: 12px; padding: 12px; }
  .create-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 8px; align-items: center; }
  .inline-check { display: inline-flex; gap: 8px; align-items: center; }
  .users-table-wrap { overflow: auto; }
  .users-table { width: 100%; border-collapse: collapse; margin-top: 12px; }
  .users-table th, .users-table td { border-bottom: 1px solid var(--border); padding: 8px; text-align: left; }
  .actions { display: flex; gap: 8px; flex-wrap: wrap; }
  .error { color: var(--danger); }
  .success { color: #16a34a; }
</style>
