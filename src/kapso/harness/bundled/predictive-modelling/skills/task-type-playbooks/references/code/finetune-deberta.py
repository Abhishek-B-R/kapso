"""Fine-tuning a DeBERTa-v3 classifier: a shape from a hand-written knowledge graph
of past competitions, not a method.

Parameters, the task's: `train_file` and `validation_file` (CSV files with `text`
and `label` columns, from the task's own split or an internal fold, never a public
dataset's test split), `model_path` (the pinned path from the setup shortlist),
`num_classes`, `max_length`. Early stopping watches the validation loss. Scope:
`max_length` truncates a document at the window; on long documents chunk or slide
a window in training and inference instead (the playbook's rule), which this
example does not show.
"""
from datasets import load_dataset
from transformers import (AutoModelForSequenceClassification, AutoTokenizer, EarlyStoppingCallback,
                          Trainer, TrainingArguments)

dataset = load_dataset("csv", data_files={"train": train_file, "validation": validation_file})
tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path, num_labels=num_classes)


def tokenize(examples):
    return tokenizer(examples["text"], padding="max_length", truncation=True, max_length=max_length)


tokenized = dataset.map(tokenize, batched=True)
tokenized.set_format("torch", columns=["input_ids", "attention_mask", "label"])

training_args = TrainingArguments(
    output_dir="./results", learning_rate=2e-5, per_device_train_batch_size=16, per_device_eval_batch_size=16,
    num_train_epochs=5, weight_decay=0.01, warmup_ratio=0.05, lr_scheduler_type="linear", fp16=True,
    eval_strategy="epoch", save_strategy="epoch", load_best_model_at_end=True,
    metric_for_best_model="eval_loss", greater_is_better=False, logging_steps=50,
)
trainer = Trainer(model=model, args=training_args, train_dataset=tokenized["train"], eval_dataset=tokenized["validation"],
                  processing_class=tokenizer, callbacks=[EarlyStoppingCallback(early_stopping_patience=2)])
trainer.train()
