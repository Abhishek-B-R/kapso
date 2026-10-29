"""Fine-tuning RoBERTa/DistilBERT code Example (from the benchmark's graph; the task's own inputs where the original named a public dataset)."""
from transformers import RobertaForSequenceClassification, RobertaTokenizerFast, Trainer, TrainingArguments

tokenizer = RobertaTokenizerFast.from_pretrained('roberta-base')
model = RobertaForSequenceClassification.from_pretrained('roberta-base', num_labels=2)
# tokenizer = DistilBertTokenizerFast.from_pretrained('distilbert-base-uncased')
# model = DistilBertForSequenceClassification.from_pretrained('distilbert-base-uncased', num_labels=2)

trainer = Trainer(
    model=model,
    args=TrainingArguments(output_dir='./results', learning_rate=2e-5, per_device_train_batch_size=16, num_train_epochs=3),
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    tokenizer=tokenizer
)
trainer.train()
