import json
import os
import re

LABELS_PATH = os.path.join("dataset", "labels.json")

if not os.path.exists(LABELS_PATH):
    raise FileNotFoundError(f"Cannot find labels file at path: {LABELS_PATH}")

with open(LABELS_PATH, "r", encoding="utf-8") as f:
    data = json.load(f)

annotations = data.get("annotations", [])

# Initialize categorisation tracking buckets
just_numbers = 0
just_text = 0
mixed_text_numbers = 0
empty_or_special = 0

print(f"Total annotations found to scan: {len(annotations)}\n")

for ann in annotations:
    # Clean the string by stripping padding whitespaces
    gt = ann.get("ground_truth", "").strip()
    
    if not gt:
        empty_or_special += 1
        continue
        
    # Check 1: Contains strictly digits (0-9)
    if gt.isdigit():
        just_numbers += 1
        
    # Check 2: Contains strictly alphabetic characters (handles Cyrillic/English text strings)
    # We strip out basic punctuation or spaces to ensure standard sentences count as text
    elif re.match(r'^[^\d\W]+$', gt.replace(" ", "")):
        just_text += 1
        
    # Check 3: If it's not purely text or purely digits, but contains both number elements and letter frames
    elif any(char.isdigit() for char in gt) and any(char.isalpha() for char in gt):
        mixed_text_numbers += 1
        
    # Catch-all: Symbols, pure punctuation, or mathematical formatting cuts
    else:
        empty_or_special += 1

# Calculate precise percentage representation allocations
total = len(annotations) if len(annotations) > 0 else 1

print("================ DATASET DISTRIBUTION FOR DIPLOMA ================")
print(f"🔢 Just Numbers Only:     {just_numbers:<5} ({ (just_numbers/total)*100 :.2f}%)")
print(f"🔤 Just Text Only:        {just_text:<5} ({ (just_text/total)*100 :.2f}%)")
print(f"🎛️ Mixed (Text + Num):    {mixed_text_numbers:<5} ({ (mixed_text_numbers/total)*100 :.2f}%)")
print(f"⚠️ Special/Empty Symbols: {empty_or_special:<5} ({ (empty_or_special/total)*100 :.2f}%)")
print("==================================================================")
