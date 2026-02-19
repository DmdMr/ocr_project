const API_URL = "http://localhost:8000/api"

export async function uploadImage(file: File) {
    const formData = new FormData()
    formData.append("file", file)

    const res = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData
    })

    return await res.json()
}

export async function getDocuments() {
    const res = await fetch(`${API_URL}/documents`)
    return await res.json()
}

export async function deleteDocument(id: string) {
    await fetch(`${API_URL}/documents/${id}`, {
        method: "DELETE"
    })
}

export async function updateDocument(id: string, data: any) {
    const response = await fetch(`http://localhost:8000/api/documents/${id}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })

    if (!response.ok) {
        throw new Error("Failed to update document")
    }

    return response.json()
}


export async function searchDocuments(q: string) {
    const res = await fetch(`${API_URL}/search?q=${q}`)
    return await res.json()
}
