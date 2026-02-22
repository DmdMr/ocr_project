import { writable } from "svelte/store"

export const settings = writable({
    showImage: true,
    showFilename: true,
    showTags: true,
    showButtons: true
})