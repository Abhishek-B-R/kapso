"""Object detection with a pretrained YOLO detector: a shape from a hand-written
knowledge graph of past competitions, not a method.

Parameters, the task's: `weights` (the pinned detector under prepared/models; the
larger and smaller variants trade accuracy for speed), `data_yaml` (the dataset
description you write from the task's files and its split), `image_dir`. Epochs
are bounded by patience on the validation metric.
"""
from ultralytics import YOLO

model = YOLO(weights)
model.train(data=data_yaml, epochs=100, patience=20, imgsz=640)
results = model.predict(source=image_dir, save=True)
