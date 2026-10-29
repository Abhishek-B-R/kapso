"""Code example of Pretrained Embeddings + MLP for classification (from the benchmark's graph; the task's own inputs where the original named a public dataset)."""
import torch
from torch import nn, optim
from transformers import AutoTokenizer, AutoModel

tokenizer = AutoTokenizer.from_pretrained('distilbert-base-uncased')
model = AutoModel.from_pretrained('distilbert-base-uncased')

batch_size = 32
mlp = nn.Sequential(
    nn.Linear(768, 128),
    nn.ReLU(),
    nn.Linear(128, num_classes)
)
optimizer = optim.Adam(mlp.parameters(), lr=1e-3)
criterion = nn.CrossEntropyLoss()

for i in range(0, len(X_train), batch_size):
    batch_texts = X_train[i:i+batch_size]
    batch_labels = torch.tensor(y_train[i:i+batch_size])
    inputs = tokenizer(batch_texts, padding=True, truncation=True, return_tensors='pt')
    with torch.no_grad():
        embeddings = model(**inputs).last_hidden_state[:,0,:]  # CLS token
    optimizer.zero_grad()
    outputs = mlp(embeddings)
    loss = criterion(outputs, batch_labels)
    loss.backward()
    optimizer.step()
