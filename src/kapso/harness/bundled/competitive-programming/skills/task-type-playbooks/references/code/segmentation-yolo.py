"""Image segmentation with a pretrained YOLO segmentation model (from the benchmark's graph)."""
from ultralytics import YOLO

model = YOLO("yolo11m-seg.pt")  # pretrained; "yolo11l-seg.pt" and "yolo11s-seg.pt" exist too
model.train(data="dataset.yaml", epochs=50, imgsz=640)  # the task's dataset description
results = model.predict(source="images/", save=True)
