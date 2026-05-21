import os
import json
import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
from transformers import TrOCRProcessor, VisionEncoderDecoderModel, AdamW
from tqdm import tqdm

# --- 1. PROXY CONFIGURATION (Crucial for network access) ---
PROXY_STRING = "http://191.101.65"
os.environ["http_proxy"] = PROXY_STRING
os.environ["https_proxy"] = PROXY_STRING
PROXY_DICT = {"http": PROXY_STRING, "https": PROXY_STRING}

# --- 2. DATASET DEFINITION ENGINE ---
# --- 1. DATASET DEFINITION ENGINE ---
class RussianOCRDataset(Dataset):
    def __init__(self, labels_json_path, dataset_dir, processor, subset_type="train"):
        if not os.path.exists(labels_json_path):
            raise FileNotFoundError(f"Critical error: Master file not found at {labels_json_path}")
            
        with open(labels_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Safe fallback: If 'subset' key is missing, default it to 'train'
        self.annotations = [
            ann for ann in data["annotations"] 
            if str(ann.get("subset", "train")).strip().lower() == subset_type.lower()
        ]
        
        self.dataset_dir = dataset_dir
        self.processor = processor

    def __len__(self):
        return len(self.annotations)


    def __getitem__(self, idx):
        ann = self.annotations[idx]
        img_path = os.path.join(self.dataset_dir, ann["file_path"])
        image = Image.open(img_path).convert("RGB")
        
        # Generate image pixel tensors
        pixel_values = self.processor(image, return_tensors="pt").pixel_values.squeeze()
        
        # Tokenize ground truth transcriptions securely
        labels = self.processor.tokenizer(
            ann["ground_truth"], 
            return_tensors="pt", 
            padding="max_length", 
            max_length=64
        ).input_ids.squeeze()
        
        # Ensure CrossEntropy mapping ignores padding sequences (-100 parameter)
        labels = [label if label != self.processor.tokenizer.pad_token_id else -100 for label in labels]
        
        return {
            "pixel_values": pixel_values,
            "labels": torch.tensor(labels, dtype=torch.long)
        }

# --- 3. HARDWARE & DIRECTORY RESOLUTION ---
DEVICE = "cpu"  # Optimized baseline target for Intel macOS
DATASET_DIR = "dataset"
LABELS_PATH = os.path.join(DATASET_DIR, "labels.json")

# TARGET PATH: Adjusted to map directly to your local stock model repository folder
MODEL_NAME = "/Users/demidmurakhin/Desktop/ocr_project/backend/models/trocr-base-ru"

print(f"Initializing training components on: {DEVICE}")
print(f"Loading local base parameters from: {MODEL_NAME}")

# Initialize processor and baseline weights from your local paths
processor = TrOCRProcessor.from_pretrained(MODEL_NAME)
model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME).to(DEVICE)

# Bind generation configurations parameters
model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
model.config.pad_token_id = processor.tokenizer.pad_token_id

# Instantiate data loading pipes

# train_dataset = RussianOCRDataset(LABELS_PATH, DATASET_DIR, processor, subset_type="train")

train_dataset = RussianOCRDataset(LABELS_PATH, DATASET_DIR, processor, subset_type="train")
# SLICE FOR FAST CPU TRAINING: Keep only the first 20 items for testing
train_dataset.annotations = train_dataset.annotations[:20]


# Check if dataset mapping is populated correctly to avoid PyTorch crashes
if len(train_dataset) == 0:
    print("\n❌ CRITICAL PATH FAULT: Still loaded 0 samples.")
    print("Please open your 'dataset/labels.json' file and verify what is inside the 'subset' field.")
    exit()

print(f"Successfully compiled {len(train_dataset)} training line elements from your json.")

# Intel Mac Safe Parameter Settings (Small batch size keeps memory footprints small)
train_loader = DataLoader(train_dataset, batch_size=2, shuffle=True)

# --- 4. EXECUTION STEP TUNING ENGINE ---
optimizer = AdamW(model.parameters(), lr=5e-5)
epochs = 3  # Start with 3 epochs to test run execution performance

print("\n--- Starting Fine-Tuning Execution Pipeline ---")
model.train()

for epoch in range(epochs):
    epoch_loss = 0.0
    progress_bar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{epochs}")
    
    for batch in progress_bar:
        optimizer.zero_grad()
        
        input_pixels = batch["pixel_values"].to(DEVICE)
        target_labels = batch["labels"].to(DEVICE)
        
        outputs = model(pixel_values=input_pixels, labels=target_labels)
        loss = outputs.loss
        
        loss.backward()
        optimizer.step()
        
        epoch_loss += loss.item()
        progress_bar.set_postfix(loss=loss.item())
        
    avg_loss = epoch_loss / len(train_loader)
    print(f"Epoch {epoch+1} Complete. Average Training Loss Matrix Score: {avg_loss:.4f}")

# --- 5. COMPACT SAVE ARTIFACT WRITER ---
OUTPUT_MODEL_DIR = "./fine_tuned_russian_trocr"
model.save_pretrained(OUTPUT_MODEL_DIR)
processor.save_pretrained(OUTPUT_MODEL_DIR)
print(f"\n🎉 Training complete! Custom handwriting model saved to: {OUTPUT_MODEL_DIR}")
