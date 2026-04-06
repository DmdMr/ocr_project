export interface GalleryImage {
    filename: string
    path?: string
    file_hash?: string
    recognized_text?: string
    image_version?: string
    created_at?: string
}

export interface AttachmentFile {
    filename: string
    path?: string
    original_name?: string
    content_type?: string
    size?: number
    created_at?: string
}


export interface Document {
    _id: string
    filename: string
    display_filename?: string
    recognized_text: string
    created_at: string
    is_archived?: boolean
    archived_at?: string | null
    tags?: string[]  
    image_version?: string
    gallery_images?: GalleryImage[]
    attachments?: AttachmentFile[]
    custom_fields?: Record<string, string | number | string[] | null>
    created_by_user_id?: string
    created_by_username?: string
    updated_by_user_id?: string
    updated_by_username?: string
    folder_id?: string | null
    folder_path?: FolderPathItem[]
}

export interface CardCustomFieldSetting {
    name: string
    type: "text" | "number" | "people"
    created_at?: string
}


export interface FolderPathItem {
    id: string
    name: string
    is_system?: boolean
}

export interface Folder {
    id: string
    name: string
    parent_id: string | null
    is_system: boolean
    system_key?: string
    created_at?: string
    updated_at?: string
    created_by_user_id?: string | null
    created_by_username?: string | null
    path?: FolderPathItem[]
    children?: Folder[]
}
