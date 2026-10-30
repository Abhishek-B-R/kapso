"""Fine-tuning a RoBERTa or DistilBERT classifier: a shape from a hand-written
knowledge graph of past competitions, not a method.

Parameters, the task's: `model_path` (the pinned path from the setup shortlist; a
RoBERTa base or a DistilBERT base), `num_classes`, `train_dataset` and
`eval_dataset` (tokenized from the task's own split or an internal fold). Early
stopping watches the validation loss; the chunking of long documents is not shown.
"""
from transformers import (AutoModelForSequenceClassification, AutoTokenizer, EarlyStoppingCallback,
                          Trainer, TrainingArguments)

tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModelForSequenceClassification.from_pretrained(model_path, num_labels=num_classes)

trainer = Trainer(
    model=model,
    args=TrainingArguments(output_dir="./results", learning_rate=2e-5, per_device_train_batch_size=16, num_train_epochs=5,
                           warmup_ratio=0.05, eval_strategy="epoch", save_strategy="epoch", load_best_model_at_end=True,
                           metric_for_best_model="eval_loss", greater_is_better=False),
    train_dataset=train_dataset, eval_dataset=eval_dataset, processing_class=tokenizer,
    callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
)
trainer.train()
