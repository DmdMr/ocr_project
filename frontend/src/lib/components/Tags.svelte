<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte";
    import { writable } from "svelte/store";

    const dispatch = createEventDispatcher();

    // This store will hold the tags list and the selected tags
    export let tags: string[] = [];  // existing tags (provided by parent)
    export let selectedTags = writable<string[]>([]);

    let newTag = "";
    let addingGlobalTag = false;

    // Toggle tag selection
    function toggleTag(tag: string) {
        selectedTags.update((currentTags) => {
            if (currentTags.includes(tag)) {
                return currentTags.filter((t) => t !== tag);
            } else {
                return [...currentTags, tag];
            }
        });
    }

    // Add a new tag if it doesn't exist already
    function addNewTag() {
        if (newTag && !tags.includes(newTag.trim())) {
            tags.push(newTag.trim());
            newTag = "";
            addingGlobalTag = false;
            dispatch("tagAdded", newTag.trim());
        }
    }

    // Handle key press (Enter) to add tag
    function handleKeyPress(event: KeyboardEvent) {
        if (event.key === 'Enter') {
            addNewTag();
        }
    }

    onMount(() => {
        // Focus on the input when the component is mounted
        document.getElementById('new-tag-input')?.focus();
    });
</script>

<div class="tags-container">
    <!-- Display existing tags -->
    <div class="tag-list">
        {#each tags as tag}
            <div class="tag-item">
                <input 
                    type="checkbox" 
                    id={tag} 
                    on:change={() => toggleTag(tag)} 
                    checked={$selectedTags.includes(tag)}
                />
                <label for={tag}>{tag}</label>
            </div>
        {/each}
    </div>

    <!-- Add new tag input -->
    <div class="new-tag">
        <input
            id="new-tag-input"
            type="text"
            bind:value={newTag}
            placeholder="Добавить новый тег"
            on:keydown={handleKeyPress}
        />
        <button on:click={addNewTag}>Добавить тег</button>
    </div>
</div>

<style>
    .tags-container {
        display: flex;
        flex-direction: column;
        gap: 15px;
    }

    .tag-list {
        display: flex;
        flex-wrap: wrap;
        gap: 15px;
    }

    .tag-item {
        display: flex;
        align-items: center;
        gap: 5px;
    }

    .new-tag input {
        padding: 5px;
        margin-right: 10px;
    }

    .new-tag button {
        padding: 5px 10px;
        cursor: pointer;
    }

    .tag-item input {
        margin: 5px;
    }
</style>