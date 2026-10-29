"""Code Example of Fine-tuning DeBERTa-v3 (from the benchmark's graph; the task's own inputs where the original named a public dataset)."""
from datasets import load_dataset
from transformers import DebertaV2Tokenizer, DebertaV2ForSequenceClassification
from transformers import TrainingArguments, Trainer
import torch

dataset = load_dataset('csv', data_files={'train': 'train.csv', 'validation': 'validation.csv'})  # the task's own split, never a public dataset's test split
model_name = 'microsoft/deberta-v3-base'
tokenizer = DebertaV2Tokenizer.from_pretrained(model_name)
model = DebertaV2ForSequenceClassification.from_pretrained(model_name, num_labels=2)

def tokenize_function(examples):
    return tokenizer(examples['text'], padding='max_length', truncation=True, max_length=256)

tokenized_datasets = dataset.map(tokenize_function, batched=True)
tokenized_datasets.set_format('torch', columns=['input_ids', 'attention_mask', 'label'])

training_args = TrainingArguments(
    output_dir='./results',
    learning_rate=2e-5,
    per_device_train_batch_size=16,
    per_device_eval_batch_size=16,
    num_train_epochs=3,
    weight_decay=0.01,
    save_strategy='epoch',
    logging_dir='./logs',
    logging_steps=50,
    fp16=True
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=tokenized_datasets['train'],
    eval_dataset=tokenized_datasets['validation'],
    tokenizer=tokenizer
)
trainer.train()
