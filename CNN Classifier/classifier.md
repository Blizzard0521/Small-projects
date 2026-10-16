# Intel Image Classification: A Custom CNN for Natural Scene Recognition

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![TensorFlow](https://img.shields.io/badge/TensorFlow-Keras-FF6F00?logo=tensorflow&logoColor=white)
![scikit-learn](https://img.shields.io/badge/scikit--learn-metrics-F7931E?logo=scikitlearn&logoColor=white)
![Colab](https://img.shields.io/badge/Run%20on-Google%20Colab-F9AB00?logo=googlecolab&logoColor=white)
![Test Accuracy](https://img.shields.io/badge/Test%20Accuracy-86.9%25-success)

A convolutional neural network built **from scratch** (no pre-trained weights) that sorts photographs of natural and urban scenes into six categories: **buildings, forest, glacier, mountain, sea and street**. The model has about 424K parameters. On the 3,000-image held-out test set it scores **86.9% accuracy** and a **0.870 macro F1-score**.

The project was built for the *Computer Vision and Natural Language Processing* module (ITS69204) at Taylor's University, where I was in charge of the prototype development.

---

## Table of Contents

- [Highlights](#highlights)
- [Dataset](#dataset)
- [Methodology](#methodology)
- [Model Architecture](#model-architecture)
- [Training](#training)
- [Results](#results)
- [Error Analysis](#error-analysis)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Limitations & Future Work](#limitations--future-work)
- [Acknowledgements](#acknowledgements)

---

## Highlights

| | |
|---|---|
| **Task** | 6-class scene classification |
| **Approach** | Custom 4-block CNN trained from scratch |
| **Parameters** | 424,006 total (423,046 trainable) |
| **Input** | 150 × 150 RGB, pixels scaled to [0, 1] |
| **Test accuracy** | **86.90%** |
| **Macro F1** | **0.8700** |
| **Best class** | Forest (F1 = 0.977) |
| **Hardest class** | Glacier (F1 = 0.819) |

---

## Dataset

**Source:** [Intel Image Classification, on Kaggle](https://www.kaggle.com/datasets/puneet6060/intel-image-classification)

The dataset contains about 17K images of size 150 × 150, sorted into six scene categories. This project uses the official `seg_train` and `seg_test` folders. It also carves a **stratified 10% validation split** out of the training set, so the test set is used only for the final evaluation.

| Class | Train | Validation | Test | Train share |
|---|---:|---:|---:|---:|
| Buildings | 1,972 | 219 | 437 | 15.6% |
| Forest | 2,044 | 227 | 474 | 16.2% |
| Glacier | 2,163 | 241 | 553 | 17.1% |
| Mountain | 2,261 | 251 | 525 | 17.9% |
| Sea | 2,046 | 228 | 510 | 16.2% |
| Street | 2,144 | 238 | 501 | 17.0% |
| **Total** | **12,630** | **1,404** | **3,000** | 100% |

The classes are roughly balanced: the largest training share is 17.9% and the smallest is 15.6%. Because of this, the project does not use class weighting or resampling.

---

## Methodology

```
Kaggle download ─► Stratified train/val split ─► tf.data pipeline ─► CNN training ─► Test-set evaluation
                        (90 / 10, seed 42)        (resize, normalise,   (EarlyStopping,      (accuracy, per-class
                                                   augment train only)    LR scheduling)       P/R/F1, confusion matrix)
```

### 1. Stratified splitting
`sklearn.model_selection.train_test_split` with `stratify=labels` divides each class separately. This keeps the class proportions the same in the training and validation sets. `random_state=42` makes the split reproducible.

### 2. Input pipeline (`tf.data`)
- JPEGs are decoded with `channels=3`, which forces RGB because a few images in the dataset are grayscale.
- Images are resized to 150 × 150 and scaled to the [0, 1] range.
- The pipeline is parallelised with `num_parallel_calls=AUTOTUNE` and uses `prefetch`, so the GPU isn't left waiting on disk reads.
- The batch size is 32.

### 3. Data augmentation (training set only)
| Layer | Setting |
|---|---|
| `RandomFlip` | horizontal |
| `RandomRotation` | ±10% (≈ ±36°) |
| `RandomZoom` | ±10% |

The validation and test sets are **not augmented**, so the evaluation reflects real, unaltered images.

---

## Model Architecture

The model is a compact VGG-style network. It has four convolution blocks, and the number of filters doubles at each block (32 → 64 → 128 → 256). Each convolution is followed by **Batch Normalization** to make training more stable. The classifier head uses **Global Average Pooling** instead of `Flatten`, which keeps the parameter count small and reduces overfitting.

| # | Layer | Output shape | Params |
|---|---|---|---:|
| 1 | Conv2D 32 @ 3×3, ReLU, same | 150 × 150 × 32 | 896 |
| | BatchNormalization | 150 × 150 × 32 | 128 |
| | MaxPooling2D 2×2 | 75 × 75 × 32 | 0 |
| 2 | Conv2D 64 @ 3×3, ReLU, same | 75 × 75 × 64 | 18,496 |
| | BatchNormalization | 75 × 75 × 64 | 256 |
| | MaxPooling2D 2×2 | 37 × 37 × 64 | 0 |
| 3 | Conv2D 128 @ 3×3, ReLU, same | 37 × 37 × 128 | 73,856 |
| | BatchNormalization | 37 × 37 × 128 | 512 |
| | MaxPooling2D 2×2 | 18 × 18 × 128 | 0 |
| 4 | Conv2D 256 @ 3×3, ReLU, same | 18 × 18 × 256 | 295,168 |
| | BatchNormalization | 18 × 18 × 256 | 1,024 |
| | MaxPooling2D 2×2 | 9 × 9 × 256 | 0 |
| Head | GlobalAveragePooling2D | 256 | 0 |
| | Dense 128, ReLU | 128 | 32,896 |
| | Dropout 0.5 | 128 | 0 |
| | Dense 6, Softmax | 6 | 774 |
| | **Total** | | **424,006** |

---

## Training

| Setting | Value |
|---|---|
| Optimizer | Adam (initial LR = 1e-3) |
| Loss | Sparse categorical cross-entropy (integer labels) |
| Max epochs | 30 |
| `EarlyStopping` | monitor `val_loss`, patience 5, restore best weights |
| `ReduceLROnPlateau` | monitor `val_loss`, factor 0.5, patience 3, min LR 1e-6 |
| `ModelCheckpoint` | saves best `val_loss` to `best_model.keras` |
| Hardware | Google Colab GPU (~75 s / epoch) |

Training **stopped early at epoch 24**. Validation loss was lowest at **epoch 19** (val_loss 0.380, val_accuracy 87.5%), and the weights from that epoch were restored. Over the run, the learning rate was halved three times: 1e-3 → 5e-4 → 2.5e-4 → 1.25e-4.

![Training curves](assets/training_curves.png)

Validation accuracy fluctuates during the early epochs, with sharp drops at epochs 5, 10 and 14. Each drop is followed by a learning-rate reduction, after which the curve becomes smoother. This pattern is typical when BatchNorm running statistics are still settling under a relatively high learning rate. The gap between training and validation stays modest, so the augmentation, dropout and GAP head appear to be keeping overfitting in check.

---

## Results

### Overall (test set, n = 3,000)

| Metric | Score |
|---|---:|
| Accuracy | **0.8690** |
| Macro precision | 0.8705 |
| Macro recall | 0.8719 |
| Macro F1 | **0.8700** |
| Weighted F1 | 0.8681 |

### Per-class

| Class | Precision | Recall | F1-score | Support |
|---|---:|---:|---:|---:|
| Buildings | 0.8465 | 0.8581 | 0.8523 | 437 |
| Forest | **0.9708** | **0.9831** | **0.9769** | 474 |
| Glacier | 0.8812 | 0.7649 | 0.8190 | 553 |
| Mountain | 0.8366 | 0.8095 | 0.8228 | 525 |
| Sea | 0.8231 | 0.9216 | 0.8696 | 510 |
| Street | 0.8649 | 0.8942 | 0.8793 | 501 |

### Confusion matrix

![Confusion matrix](assets/confusion_matrix.png)

---

## Error Analysis

Most errors fall into **two semantic clusters**. In both, the classes share visual features, and some images could reasonably carry either label.

### 1. Natural landscapes: glacier ↔ mountain ↔ sea
| True → Predicted | Count |
|---|---:|
| Glacier → Mountain | 71 |
| Mountain → Sea | 47 |
| Mountain → Glacier | 44 |
| Glacier → Sea | 42 |

Glacier has the **lowest recall (76.5%)**. Snow-capped mountains, icy peaks and glacial lakes share the same textures, colours and horizon lines, and in many images both labels apply. Water and pale skies make the sea class a common second guess.

![Mountain misclassified as glacier](assets/misclassified_mountain_as_glacier.png)

### 2. Urban scenes: buildings ↔ street
| True → Predicted | Count |
|---|---:|
| Buildings → Street | 54 |
| Street → Buildings | 40 |

Street-level photos usually contain building façades, and close-up building shots often include a strip of road. Which label is correct depends mostly on framing, which a model working at 150 × 150 resolution finds hard to judge.

![Street misclassified as buildings](assets/misclassified_street_as_building.png)

**Forest** almost never gets confused with another class (466/474 correct). Its dense green texture looks different from every other category.

---

## Getting Started

### Option A: Google Colab (recommended)

1. Open `CV_NLP_GA.ipynb` in [Google Colab](https://colab.research.google.com/).
2. Set **Runtime → Change runtime type → GPU**.
3. Get a Kaggle API token: Kaggle → *Settings* → *API* → **Create New Token**. This downloads `kaggle.json`.
4. Run the first cell and upload `kaggle.json` when prompted. The notebook downloads and unzips the dataset (~346 MB) to `/content/intel_data`.
5. **Runtime → Run all**.

### Option B: Local

```bash
git clone <your-repo-url>
cd <repo-name>
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Place kaggle.json in ~/.kaggle/ then:
kaggle datasets download -d puneet6060/intel-image-classification
unzip -q intel-image-classification.zip -d ./intel_data
```

Then make two changes to the notebook:
- Remove the `google.colab` upload cell.
- Change `data_root` to `./intel_data`.

### Requirements

```
tensorflow>=2.15
scikit-learn
numpy
pandas
matplotlib
seaborn
kaggle
```

### Outputs produced

| File | Description |
|---|---|
| `best_model.keras` | Best checkpoint (lowest validation loss) |
| `training_curves.png` | Accuracy and loss curves |
| `per_class_metrics.csv` | Precision / recall / F1 / support per class |
| `confusion_matrix.png` | Test-set confusion matrix |
| `misclassified_examples.png` | Sample mountain → glacier errors |
| `misclassified_street_as_building_examples.png` | Sample street → buildings errors |

---

## Project Structure

```
.
├── CV_NLP_GA.ipynb          # End-to-end notebook: data → model → training → evaluation
├── requirements.txt
├── README.md
└── assets/
    ├── training_curves.png
    ├── confusion_matrix.png
    ├── misclassified_mountain_as_glacier.png
    └── misclassified_street_as_building.png
```

---

## Limitations & Future Work

- **Run-to-run variance.** `train_test_split` and dataset shuffling are seeded, but TensorFlow's weight initialisation and GPU operations are not. Re-running the notebook will give slightly different numbers. Calling `tf.keras.utils.set_random_seed(42)` would make runs more repeatable.
- **Label ambiguity.** Many glacier/mountain and building/street images could carry either label. A better architecture alone won't fix this, because part of the error is noise in the labels themselves.
- **Transfer learning.** Fine-tuning a pre-trained backbone such as EfficientNet, ResNet50 or MobileNetV3 is the obvious next step. Reported results on this dataset reach the low-to-mid 90s.
- **Stronger augmentation.** Colour jitter, random crops or MixUp/CutMix could help the model rely less on colour cues, which are a likely factor in the glacier/sea confusion.
- **Higher input resolution.** The source images are already 150 × 150, but resizing them up for a pre-trained model, or using test-time augmentation, could help with fine-grained details like road markings and snow lines.
- **Explainability.** Grad-CAM heatmaps would show whether the model looks at meaningful regions (peaks, façades, road surfaces) or at shortcuts like sky colour.

---

## Acknowledgements

- Dataset: [Intel Image Classification](https://www.kaggle.com/datasets/puneet6060/intel-image-classification), originally released by Intel for an Analytics Vidhya image classification challenge and hosted on Kaggle by Puneet Bansal.
- Built for ITS69204 *Computer Vision and Natural Language Processing*, Taylor's University.

### Authors

- Ivan Tan
