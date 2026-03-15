export interface GalleryImage {
    filename: string
    path?: string
    file_hash?: string
    recognized_text?: string
    image_version?: string
    created_at?: string
}


export interface Document {
    _id: string
    filename: string
    recognized_text: string
    created_at: string
    tags?: string[]  
    image_version?: string
    gallery_images?: GalleryImage[]
}