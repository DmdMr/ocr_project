<script lang="ts">
    import { createEventDispatcher } from "svelte"
    import type { Document } from "../types"
    import { deleteDocument } from "../api"
    import { updateDocument } from "../api"
    import CardPreview from "./CardPreview.svelte"

    let showPreview = false

    export let doc: Document

    let editing = false
    let editedText = doc.recognized_text

    async function save(text: any) {
        await updateDocument(doc._id, {
            recognized_text: editedText
        })

        doc.recognized_text = editedText
        editing = false
    }

    type DocumentCardEvents = {
        deleted: { id: string },
        tagClick: { tag: string }
    }

    const dispatch = createEventDispatcher<DocumentCardEvents>()



    async function remove() {
        await deleteDocument(doc._id)
        dispatch("deleted", { id: doc._id })
    }



</script>


<div class="card">
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <img
        src={`http://localhost:8000/uploads/${doc.filename}`}
        alt=""
        on:click={() => showPreview = true}
    />


        {#if showPreview}
            <CardPreview
                {doc}
                bind:editedText
                {editing}
                on:close={() => showPreview = false}
                on:save={(e) => save(e.detail.text)}
                on:delete={remove}
                on:editToggle={() => editing = !editing}
            />
        {/if}
</div>



<style>




.card {
    border: 1px solid #dddddd84;
    border-radius: 8px;
    padding: 15px;
    background: var(--card);
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    break-inside: avoid;
    margin-bottom: 20px;
}


img {
    width: 100%;
    border-radius: 6px;
    margin-bottom: 5px;
}



</style>
