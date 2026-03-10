<script lang="ts">
    import Upload from "./lib/components/Upload.svelte"
    import DocumentList from "./lib/components/DocumentList.svelte"
    import Settings from "./lib/components/Settings.svelte";
    import { onMount } from "svelte"

    type ThemeMode = "system" | "light" | "dark"
    let refreshKey = 0
    let themeMode: ThemeMode = "system"
    let language: "en" | "ru" = "en"

    function handleUpload() {
        refreshKey += 1
    }


    function applyTheme(mode: ThemeMode) {
        themeMode = mode

        if (mode === "system") {
            document.body.removeAttribute("data-theme")
        } else {
            document.body.setAttribute("data-theme", mode)
        }

        localStorage.setItem("themeMode", mode)
    }

    function setLanguage(newLanguage: "en" | "ru") {
        language = newLanguage
        localStorage.setItem("language", newLanguage)
        document.documentElement.lang = newLanguage
    }

    

    onMount(() => {
        const savedTheme = (localStorage.getItem("themeMode") as ThemeMode | null) ?? "system"
        const savedLanguage = (localStorage.getItem("language") as "en" | "ru" | null) ?? "en"
        applyTheme(savedTheme)
        setLanguage(savedLanguage)
    })

</script>


<h2>OCR System</h2>


<!--


<div class="theme-switcher">
    <button on:click={() => setTheme('light')}>☀️</button>
    <button on:click={() => setTheme('dark')}>🌙</button>
</div>


<TopControls
    mode={themeMode}
    {language}
    onThemeChange={applyTheme}
    onLanguageChange={setLanguage}
/>
-->


<Upload on:uploaded={handleUpload} />

<DocumentList {refreshKey} />



