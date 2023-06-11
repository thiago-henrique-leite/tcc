# -*- coding: utf-8 -*-
"""[OFICIAL] TCC - VGG19.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1eTO-RpwAbWngLcKjLhy_jiBHrMUhNGV2
"""

import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers

from google.colab import drive
drive.mount('/content/drive')

"""
Extrai o dataset SPIE-AAPM Lung CT Challenge do drive. O conjunto de imagens pode ser acessado no link abaixo:
  - https://wiki.cancerimagingarchive.net/display/Public/SPIE-AAPM+Lung+CT+Challenge#19039197a19462154cc74bea92039089e61a0f44
"""

!unzip -q /content/drive/MyDrive/TCC/dataset.zip

!mkdir ndataset
!mkdir ndataset/malignant
!mkdir ndataset/benign

import os
from PIL import Image

dataset_dir = 'dataset'
ndataset_dir = 'ndataset'

for class_name in ['malignant', 'benign']:
    class_dir = os.path.join(ndataset_dir, class_name)
    if not os.path.exists(class_dir):
        os.makedirs(class_dir)

for class_name in os.listdir(dataset_dir):
    class_dir = os.path.join(dataset_dir, class_name)
    if os.path.isdir(class_dir):
        for image_file in os.listdir(class_dir):
            image_path = os.path.join(class_dir, image_file)
            if os.path.isfile(image_path):
                image = Image.open(image_path)
                new_image = image.resize((180, 180))
                save_dir = os.path.join(ndataset_dir, class_name)
                save_path = os.path.join(save_dir, image_file)
                new_image.save(save_path)

IMAGE_SIZE = (180, 180)
BATCH_SIZE = 32

train_ds, val_ds = tf.keras.preprocessing.image_dataset_from_directory(
    'ndataset',
    validation_split=0.2,
    subset='both',
    seed=1337,
    image_size=IMAGE_SIZE,
    batch_size=BATCH_SIZE,
)

data_augmentation = keras.Sequential(
    [
      layers.RandomFlip('horizontal'),
      layers.RandomRotation(0.1),
      layers.RandomContrast(0.2),
      layers.RandomZoom(0.2),
      layers.RandomTranslation(0.1, 0.1)
    ]
)

from tensorflow.keras.applications import VGG19

def make_model(input_shape):
    inputs = keras.Input(shape=input_shape)

    x = data_augmentation(inputs)

    base_model = VGG19(weights='imagenet', include_top=False, input_shape=input_shape)

    x = base_model(x)
    x = layers.Rescaling(1.0 / 255)(x)
    x = layers.Conv2D(32, 3, strides=2, padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.Conv2D(64, 3, padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.SeparableConv2D(1024, 3, padding='same')(x)
    x = layers.BatchNormalization()(x)
    x = layers.Activation('relu')(x)
    x = layers.GlobalAveragePooling2D()(x)
    x = layers.Dropout(0.5)(x)

    outputs = layers.Dense(1, activation='sigmoid')(x)

    return keras.Model(inputs, outputs, name='vgg16')

model = make_model(input_shape=(180, 180, 3))
keras.utils.plot_model(model, show_shapes=True)

import keras.backend as K

def f1_score(y_true, y_pred):
    y_true = K.round(y_true)
    y_pred = K.round(y_pred)
    tp = K.sum(y_true * y_pred)
    fp = K.sum((1 - y_true) * y_pred)
    fn = K.sum(y_true * (1 - y_pred))
    precision = tp / (tp + fp + K.epsilon())
    recall = tp / (tp + fn + K.epsilon())
    return 2 * precision * recall / (precision + recall + K.epsilon())

EPOCHS = 70

callbacks = [keras.callbacks.ModelCheckpoint("save_at_{epoch}.h5")]

model.compile(
    optimizer=keras.optimizers.Adam(1e-5),
    loss='binary_crossentropy',
    metrics=['accuracy', keras.metrics.Precision(), keras.metrics.Recall(), f1_score]
)

history = model.fit(train_ds, epochs=EPOCHS, callbacks=callbacks, validation_data=val_ds)

import matplotlib.pyplot as plt

test_loss, test_acc, test_precision, test_recall, test_f1_score = model.evaluate(val_ds)

print('Test Loss:', test_loss)
print('Test Accuracy:', test_acc)
print('Test Precision:', test_precision)
print('Test Recall:', test_recall)
print('Test F1Score:', test_f1_score)

fig, axs = plt.subplots(5, figsize=(8, 12))

# Loss plot
axs[0].plot(history.history['loss'], label='train')
axs[0].plot(history.history['val_loss'], label='val')
axs[0].set_title('Model Loss')
axs[0].set_xlabel('Epoch')
axs[0].set_ylabel('Loss')
axs[0].legend()

# Accuracy plot
axs[1].plot(history.history['accuracy'], label='train')
axs[1].plot(history.history['val_accuracy'], label='val')
axs[1].set_title('Model Accuracy')
axs[1].set_xlabel('Epoch')
axs[1].set_ylabel('Accuracy')
axs[1].legend()

# Precision plot
axs[2].plot(history.history['precision'], label='train')
axs[2].plot(history.history['val_precision'], label='val')
axs[2].set_title('Model Precision')
axs[2].set_xlabel('Epoch')
axs[2].set_ylabel('Precision')
axs[2].legend()

# Recall plot
axs[3].plot(history.history['recall'], label='train')
axs[3].plot(history.history['val_recall'], label='val')
axs[3].set_title('Model Recall')
axs[3].set_xlabel('Epoch')
axs[3].set_ylabel('Recall')
axs[3].legend()

# F1Score plot
axs[4].plot(history.history['f1_score'], label='train')
axs[4].plot(history.history['val_f1_score'], label='val')
axs[4].set_title('Model F1Score')
axs[4].set_xlabel('Epoch')
axs[4].set_ylabel('F1Score')
axs[4].legend()

plt.tight_layout()
plt.show()

from sklearn.metrics import classification_report, confusion_matrix
import numpy as np

threshold = 0.999 # Limiar de decisão

y_true = np.concatenate([y for x, y in val_ds], axis=0)
y_pred = model.predict(val_ds)

y_true_binary = y_true.astype(int)
y_pred_binary = (y_pred > threshold).astype(int)

conf_matrix = confusion_matrix(y_true_binary, y_pred_binary)
class_report = classification_report(y_true_binary, y_pred_binary)

print('Confusion Matrix:', conf_matrix)
print('Classification Report:', class_report)