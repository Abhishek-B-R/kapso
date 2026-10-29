"""Object detection with a pretrained YOLO family model (from the benchmark's graph)."""
from ultralytics import YOLO

model = YOLO("yolo11l.pt")  # a pretrained detector; "yolo11m.pt" is the smaller one
model.train(data="dataset.yaml", epochs=50, imgsz=640)  # the task's dataset description, never a public one
results = model.predict(source="images/", save=True)
