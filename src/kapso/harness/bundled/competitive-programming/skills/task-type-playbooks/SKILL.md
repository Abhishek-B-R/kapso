---
name: task-type-playbooks
description: "The approaches that have won on each kind of prediction task (text, tokens, tabular, images, image-to-image, audio, video and volumes, detection and segmentation, the rest), with the model families that work, the conditions under which each applies, and reference code. Use when choosing the family for a task's data modality, in ideation and before the first implementation."
---
# Playbooks by task type

Match the task statement's data modality and output to a section; the
hub-inventory reference lists starting-point model names for the task
types without a section here. Every model name below is a starting point
at the time of writing: confirm it on the hub in setup (the hf-model-fetch
skill), pin it under `prepared/`, and size it to the task's compute.
Standing rules across all of them: a chosen pretrained backbone is loaded
from its pinned path, and a load that fails is an error, not a fallback;
train with early stopping on a measure that moves smoothly (the loss
rather than an accuracy, which steps) and a learning-rate schedule; when
the data has several modalities, train at least one model per modality
and spend most on the one that carries the most signal; a meta-model that
does not beat its members is not an ensemble (the ensembling skill).
Everything below is a measured alternative with its condition, not a
rule.

## Text classification

Three families, strongest first on most tasks: fine-tuning a pretrained
transformer (a DeBERTa-v3 base with chunking and a sliding window; a
ModernBERT base for long contexts; a distilled or small variant when the
training set is very large), pretrained embeddings (the CLS token or mean
pooling) with a classifier on top, and TF-IDF (word and character n-grams
merged) with a linear model or naive Bayes. A fine-tuned transformer
blended with TF-IDF and logistic regression has given the best results
often enough that TF-IDF earns a seat in the blend to measure at every
size; on very large sets the embeddings family is the efficient one.
Older sequence models (LSTMs, CNNs) rarely compete. Handcrafted, domain
and problem-specific features (spaCy, NLTK, fastText) usually add
accuracy. Do not truncate long texts: chunk or slide a window in training
and inference. Fine-tuning: all layers by default; gradual unfreezing is
worth measuring on a small set, full freezing is not; a warmup of a few
percent of the steps; a small learning rate (raise it slightly when the
loss falls slowly); when a fine-tune costs hours of the budget, resample
at that price (one fold is often all it affords) rather than skipping
validation. A tree model on TF-IDF wants dimensionality reduction first
when the vocabulary is very large. Reference code:
`references/code/finetune-deberta.py`, `finetune-roberta.py`,
`tfidf-classifier.py`, `embeddings-mlp.py`.

## Token classification and text normalisation

The text-classification models applied per token; when the token set is
very large, a small gradient-boosted model over token features is the
efficient choice. A few neighbouring tokens on both sides, as features,
usually help.

## Tabular data

Two things decide a tabular task: many features that capture different
information (handcrafted, generated, aggregated, from other libraries,
collectively covering the signal), and an ensemble of models that process
the information differently. Gradient-boosted trees are the strongest
default on pure tabular data; measure the feature context against the
test distribution (position, time and average-based features may shift;
represent the information behind them instead). Pure deep models rarely
beat boosting on tabular data alone and become competitive when the
table meets text or images. When features far outnumber rows, measure a
reduced or selected matrix against the full one. The tabular-modeling
skill has the practices; reference code: `references/code/xgboost.py`,
`catboost.py`.

## Images

Three things decide an image task: the backbone (a strong pretrained
convolutional or transformer model fine-tuned on the task, chosen by
dataset size, resolution and compute), data diversity through
augmentation (task-aware; applied after the train/validation split, never
before), and an ensemble of backbones with different pretraining. A base
that has served: two small pretrained CNNs (an EfficientNet-B0 and a wide
ResNet-50) blended, then more by condition: a small MobileNet at low
resolution; a ConvNeXt-tiny pretrained on the larger ImageNet for tiny
datasets; a larger EfficientNet or a DINOv2 base when global context
matters and the data is small. At high resolution, two designs to measure
against each other: several backbones each at its own downsampled size,
blended, or one backbone trained with progressive resizing (small images
first, the full size last). Epochs are decided by early stopping under a
schedule; tens are usually enough, and hundreds are a sign the rate or
the augmentation is wrong. With very many classes, metric learning (an
ArcFace head) with nearest neighbours or a boosted classifier on
embeddings scales where a dense softmax head does not. Augmentations:
flips, rotation, crop and resize, colour jitter, noise, Cutout, Mixup,
CutMix, RandAugment.

## Image to image

An ensemble of U-Nets with pretrained encoders (a wide ResNet-50 and an
EfficientNet-B0; a Swin base for medical or high-resolution images);
freeze the encoder while the decoder trains, then unfreeze; start with a
high learning rate and decay it; domain-specific augmentation and
preprocessing on the source image; a linear blend for denoising and
segmentation; for tiny datasets, freeze most of a pretrained model.
Detection and segmentation: pretrained YOLO, YOLOS or DETR families,
ensembled when the data allows; reference code:
`references/code/object-detection.py`, `segmentation-yolo.py`.

## Audio

Pretrained backbones on log-mel spectrograms (an Audio Spectrogram
Transformer fine-tuned on AudioSet, a CED mini, a ResNet-18, which is the
one that may also be trained from scratch), blended with a fitted
meta-model. Each checkpoint's processor turns the waveform into what its
model consumes (the AST feature extractor takes raw audio, usually at
16 kHz, and hands the model mel features): take the sampling rate and the
preprocessing from the chosen checkpoint, never from memory. Features
that have helped: MFCCs and their deltas, log-mel, spectral centroid,
bandwidth and roll-off, zero-crossing rate, RMS energy, duration, and
their means, variances, minima and maxima. Augmentations: time-domain,
added noise, SpecAugment, Mixup (which can hurt classification when
misaligned). Task-specific test-time augmentation (cropping) pays. Speech
recognition starts from a pretrained recogniser (the hub-inventory
reference), fine-tuned when the task's audio differs from its training
domain.

## Video and volumes

2.5D representations (slices or frames stacked as channels) through the
image backbones; when the data is small enough and the budget allows,
pretrained video models (a V-JEPA 2, an X-CLIP) or 3D variants of the
image backbones (a library that inflates the 2D image backbones and their
weights to 3D).

## The other task types

Speech, time series, graphs, question answering, translation,
summarisation, generation, ranking, similarity, pose and keypoints, depth
and the rest: the hub-inventory reference lists model names per type
(pose through the YOLO pose weights beside the keypoint models); the
hf-model-fetch skill finds the current ones.
