"""Pretrained embeddings with an MLP head: a shape from a hand-written knowledge
graph of past competitions, not a method.

Parameters, the task's: `model_path` (the encoder's pinned path from the setup
shortlist), `X_train` (texts) and `y_train`, `num_classes`, `batch_size`. Scope:
the embedding pass and one training pass over it. `truncation=True` clips a
document at the encoder's window: on long documents chunk and pool per document
instead (the playbook's rule). Embed once and cache the result; early stopping on
a validation loss is not shown.
"""
import torch
from torch import nn, optim
from transformers import AutoModel, AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained(model_path)
encoder = AutoModel.from_pretrained(model_path).eval()

embeddings = []
with torch.no_grad():
    for start in range(0, len(X_train), batch_size):
        inputs = tokenizer(X_train[start:start + batch_size], padding=True, truncation=True, return_tensors="pt")
        embeddings.append(encoder(**inputs).last_hidden_state[:, 0, :])  # the CLS token; mean pooling is the alternative
embeddings = torch.cat(embeddings)
labels = torch.tensor(y_train)

head = nn.Sequential(nn.Linear(embeddings.shape[1], 128), nn.ReLU(), nn.Linear(128, num_classes))
optimizer = optim.Adam(head.parameters(), lr=1e-3)
criterion = nn.CrossEntropyLoss()
for start in range(0, len(embeddings), batch_size):
    optimizer.zero_grad()
    loss = criterion(head(embeddings[start:start + batch_size]), labels[start:start + batch_size])
    loss.backward()
    optimizer.step()
