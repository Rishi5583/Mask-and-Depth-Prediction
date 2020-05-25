# Mask-and-Depth-Prediction
The problem comes under the domain of single class semantic segmentation (mask) and supervised depth estimation (depth). Here, I present my entire journey of how I approached the problem, starting from the data creation. 

I will explain every thing in detail but let's look at the results first:

<p float="left">
  <img src="https://github.com/akshatjaipuria/Mask-and-Depth-Prediction/blob/master/files/bg.png" width="140" />
  <img src="https://github.com/akshatjaipuria/Mask-and-Depth-Prediction/blob/master/files/fg_bg.png" width="140" />
  <img src="https://github.com/akshatjaipuria/Mask-and-Depth-Prediction/blob/master/files/target_mask.png" width="140" />
  <img src="https://github.com/akshatjaipuria/Mask-and-Depth-Prediction/blob/master/files/pred_mask.png" width="140" />
  <img src="https://github.com/akshatjaipuria/Mask-and-Depth-Prediction/blob/master/files/target_depth.png" width="140" />
  <img src="https://github.com/akshatjaipuria/Mask-and-Depth-Prediction/blob/master/files/pred_depth.png" width="140" />
</p>

```
On Train set:
Mask:  Average Evaluation loss(BCEWithLogits Loss): 0.0106	 Average Metric(IOU):       0.9369
Depth: Average Evaluation loss(L1 Loss):            0.0592	 Average Metric(RMS Error): 0.8572
```

```
On Validation set: 
Mask:  Average Evaluation loss(BCEWithLogits Loss): 0.0106	 Average Metric(IOU):       0.9368
Depth: Average Evaluation loss(L1 Loss):            0.0595	 Average Metric(RMS Error): 0.8616
```

Note: The Intersection over Union (IoU) metric, also referred to as the Jaccard index, is essentially a method to quantify the percent overlap between the target mask and our prediction output. So the value of 1 is the best value for IOU whereas RMSE (Root Mean Squared Error) is an error rate, and hence, 0 defines the bast value in this case.

## Dataset
The one used in the project is a custom dataset. Please refer <a href = 'https://github.com/akshatjaipuria/Mask-and-Depth-Prediction/tree/master/data#about-the-data'>`this`</a> for details regarding the data creation.
Some of the samples from the dataset:
> bg
![bg](data/Samples/bg.jpg)
> fg
![bg](data/Samples/fg.jpg)
> fg_mask
![bg](data/Samples/fg_mask.jpg)
> fg_bg
![bg](data/Samples/fg_bg.jpg)
> fg_bg_mask
![bg](data/Samples/fg_bg_mask.jpg)
> fg_bg_depth
![bg](data/Samples/fg_bg_depth.jpg)

## What am I supposed to end up with?
My model is supposed to take two images, backgroung(bg) and fg_bg, as inputs at once. The output should be the mask, which is the segmented footballer in the fg_bg and the depth map of the fg_bg. The images are of dimension 224x224, both for imputs and outputs.

<p align="center">
  <img src="https://github.com/akshatjaipuria/Mask-and-Depth-Prediction/blob/master/files/overview.png" width="700">
</p>

We will unveil the magic slowly.

## Data Loader
The very first step is how we load data to train the model. Since it's a custom dataset, the dataloder had to be written according to my folder structure. The images that are to be loaded include bg, fg_bg, mask and depths. This <a href="https://github.com/akshatjaipuria/Mask-and-Depth-Prediction/blob/master/model/data_loader.py" target="_blank">`File`</a> can be referred for the code.

On a brief note, I use the PIL library to load the images. We have 100 bg, 400k fg_bg, 400k masks and 400k depth. Onle one bg images corresponds to 4000 images from each of the other categories. Instead of making copies of bg, I decided to play with the index to make that work with 100 images only 😆. The images are in such order that fg_bg, mask and depth from index 0-3999, 4000-7999, 8000-11999 ... correspond to bg at index 0, 1, 2, ... respectively. A simple solution is to chnage the bg index as:
```Python
bg_index = int(index / 4000)
```
#### Train set and Validation set
- Training size: 70% of 400k, i.e. 280k
- Validation size: 30% of 400k, i.e. 120k

The split is made using simple array slicing (numpy) of the list of paths and seed was set to avoid data mixup in train and validation sets.

To speed up, I used pin memory, num_morkers in dataloader as 4 (this reduced the loading time for each epoch by ~400s on Nvidia Tesla P100). Also, to speed up training, I kept the batch size as large as possible, given the GPU capacity.

## Model
Next comes the model architecture. Initially, I built some fully convolutional networks to experiment. Those were the usual linear CNN architectures, with the sequence of Conv, BN, ReLU repeatedly with some skip connections to get various receptive fields at the end of the model.

<p align="center">
  <img src="https://github.com/akshatjaipuria/Mask-and-Depth-Prediction/blob/master/files/cnn_simple.png" width="700">
</p>

But is this the correct way?

Here are some probable issues:
- It is computationally too expensive to mantain the same clannel dimmension throughout the layers.
- We need a full resolution output from the model and not just the class activations.
- This type of model learns the content of the images easily, but what we require is the spatial information (location) to be preserved.

Going through some of the blogs and contents online, I realised that Encoder-Decoder Model is a better and popular approach for this task. You can refer <a href="http://cs231n.stanford.edu/slides/2017/cs231n_2017_lecture11.pdf" target="_blank">`this`</a> for a brief overview. In this, we downsample the spatial resolution of the input, developing lower-resolution feature mappings which are learned to be highly efficient at discriminating between classes, and then upsample the feature representations into a full-resolution segmentation map. Same works well for depth maps too.

<p align="center">
  <img src="https://github.com/akshatjaipuria/Mask-and-Depth-Prediction/blob/master/files/cnn_enc_doc.png" width="700">
</p>

One of the popular Encoder-Decoder Models is <a href="https://arxiv.org/pdf/1505.04597.pdf" target="_blank">`UNet`</a>. It has been improved over time with BN and an alternate upsampling (using 'bilinear' instead of Transpose Convolution). The image below presents the original architecture. But the <a href="https://github.com/qubvel/segmentation_models.pytorch#encoders-" target="_blank">`Encoder`</a> can be replaced with the State of the art models to achieve better results, which also depends on the complexity of the dataset.

<p align="center">
  <img src="https://github.com/akshatjaipuria/Mask-and-Depth-Prediction/blob/master/files/unet.png" width="700">
</p>

Now, for the model I am using, I have two seperate problems to solve (mask and depth). The image size in the original model was 572x572 and ours is 224x224. Keeping this in mind, the channels' size would become too small at the end of the encoder (as we would be training at 112 before 224) and the fact that if we keep the model size smaller, we would be able to train with larger batch sizes. Also, colab gives limited GPU, so it wasn't good enough to waste resources, I removed one of the encoder and one corresponding decoder layers to have a proper balance over all the constraints. And replacement of encoder with SOTA models was demanding a high increment of parameters count. The dataset not being very complex, I went with the default encoder only.

Since we had two seperate output requirements which are very different w.r.t the information they carry, I tried having seperate final decoder layers but that didn't help because mask and depth require same initial information from the images, but what they carry till the end is totally different. Therefor, I made the encoder part common and had seperate decoders for both the outputs. Here is a high level representation of my model.

<p align="center">
  <img src="https://github.com/akshatjaipuria/Mask-and-Depth-Prediction/blob/master/files/my_model.png" width="700">
</p>

My model contains `~ 6.2 M  (6,242,050) parameters`, of which the encoder part has ~2.2 M parameters and the two decoders have ~2 M parameters each. The code for the model is available <a href="https://github.com/akshatjaipuria/Mask-and-Depth-Prediction/blob/master/model/network_architecture.py" target="_blank">`here`</a>. The fact that we use 'bilinear' upsampling instead of transpose convolution in decoders has decreased the parameter count considerably. But we never train the entire 6.2 M parameters at once, how we train in parts will be explained in the coming sections.

## Training

