import os
import torch
import pandas as pd
from PIL import Image
from torch.utils.data import Dataset
from transformers import (
    TrOCRProcessor,
    VisionEncoderDecoderModel,
    Seq2SeqTrainer,
    Seq2SeqTrainingArguments,
    DataCollatorForSeq2Seq
)

import os
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["CUDA_VISIBLE_DEVICES"] = ""
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.0"

# =========================
# DEVICE SETUP (M2 SAFE)
# =========================

import torch

DEVICE = torch.device("cpu")
torch.set_default_device("cpu")

print("Using device:", DEVICE)

# =========================
# MODEL
# =========================

MODEL_NAME = "microsoft/trocr-small-handwritten"

processor = TrOCRProcessor.from_pretrained(MODEL_NAME)
model = VisionEncoderDecoderModel.from_pretrained(MODEL_NAME)
model.to(DEVICE)

# Required for training
model.config.decoder_start_token_id = processor.tokenizer.cls_token_id
model.config.pad_token_id = processor.tokenizer.pad_token_id
model.config.eos_token_id = processor.tokenizer.sep_token_id

# =========================
# PATHS
# =========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

TRAIN_TSV = os.path.join(DATA_DIR, "train.tsv")
TEST_TSV = os.path.join(DATA_DIR, "test.tsv")

TRAIN_IMAGES = os.path.join(DATA_DIR, "train")
TEST_IMAGES = os.path.join(DATA_DIR, "test")

# =========================
# CUSTOM DATASET (LOW RAM)
# =========================

class OCRDataset(Dataset):
    def __init__(self, tsv_path, images_folder, processor, max_samples=None):
        self.df = pd.read_csv(tsv_path, sep="\t", header=None)
        self.df.columns = ["filename", "text"]

        # 🔥 LIMIT DATASET SIZE
        if max_samples is not None:
            self.df = self.df.sample(n=max_samples, random_state=42)

        self.images_folder = images_folder
        self.processor = processor

    def __len__(self):
        return len(self.df)

    def __getitem__(self, idx):
        filename = self.df.iloc[idx]["filename"]
        text = self.df.iloc[idx]["text"]

        image_path = os.path.join(self.images_folder, filename)
        image = Image.open(image_path).convert("RGB")

        pixel_values = self.processor(
            image,
            return_tensors="pt"
        ).pixel_values.squeeze()

        labels = self.processor.tokenizer(
            text,
            padding="max_length",
            max_length=32,
            truncation=True
        ).input_ids

        # Replace padding token id's with -100
        labels = [
            (label if label != self.processor.tokenizer.pad_token_id else -100)
            for label in labels
        ]

        return {
            "pixel_values": pixel_values,
            "labels": torch.tensor(labels)
        }

# =========================
# CREATE DATASETS
# =========================

train_dataset = OCRDataset(TRAIN_TSV, TRAIN_IMAGES, processor, max_samples=5000)
test_dataset = OCRDataset(TEST_TSV, TEST_IMAGES, processor, max_samples=1000)
# =========================
# TRAINING CONFIG (SAFE)
# =========================

training_args = Seq2SeqTrainingArguments(
    output_dir=os.path.join(BASE_DIR, "trocr-finetuned"),
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    num_train_epochs=2,
    learning_rate=3e-5,
    weight_decay=0.01,
    logging_steps=500,
    save_steps=5000,
    save_total_limit=1,
    fp16=False,
    report_to="none",
    no_cuda=True,
)



trainer = Seq2SeqTrainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=test_dataset,
)

# =========================
# TRAIN
# =========================

trainer.train()

# =========================
# SAVE MODEL
# =========================

MODEL_OUTPUT = os.path.join(BASE_DIR, "trocr-finetuned")

trainer.save_model(MODEL_OUTPUT)
processor.save_pretrained(MODEL_OUTPUT)

print("Training complete.")