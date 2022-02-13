# Ghost-DeblurGAN
Motion blur can impede marker detection and marker-based pose estimation, which is common in real-world robotic applications involving fiducial markers. To solve this problem, we propose a novel lightweight generative adversarial network (GAN), Ghost-DeblurGAN, for real-time motion deblurring. Furthermore, a new large-scale dataset, YorkTag, provides pairs of sharp/blurred images containing fiducial markers and is proposed to train and qualitatively and quantitatively evaluate our model. Experimental results demonstrate that when applied along with fudicual marker systems to motion-blurred images, Ghost-DeblurGAN improves the marker detection significantly and mitigates the rotational ambiguity problem in marker-based pose estimation.   
Link to the introduction video: https://www.youtube.com/watch?v=uYHIDIJQ0r8 <br>
The implementation is modified from https://github.com/VITA-Group/DeblurGANv2.<br> 

Visual comparison of marker detection with and without Ghost-DeblurGAN in robotic applications. (a):  A video captured by a downwards camera onboard a maneuvering UAV (Qdrone, from the Quanser Inc. https://www.quanser.com/products/qdrone/). (b): A video captured by a low-cost CSI camera onboard a moving UGV (Qcar, from the Quanser Inc. https://www.quanser.com/products/qcar/).
<img src="https://user-images.githubusercontent.com/58899542/132931107-2761194b-2c94-4f87-a907-57773be92a4e.gif" width="800">
<img src="https://user-images.githubusercontent.com/58899542/132931220-d1d661f4-b148-4467-9ba0-a859b440caed.gif" width="800">



# YorkTag Dataset

Current deblurring benchmarks only contain routine scenes including pedestrians, cars, buildings, and human faces, etc. To illustrate the necessity of proposing a new deblurring benchmark containing fiducial markers, we test HINet (https://github.com/megvii-model/HINet) which has the SOTA performance on GoPro dataset with a blurred image and apply the Apriltag Detector  to the deblurred image (See Fig.1(d)). As shown in the figure, due to the fact that HINet is trained on GoPro dataset which contains no fiducial markers, the marker detection rate is far from satisfying.

<img src="https://user-images.githubusercontent.com/58899542/132930466-46acdd1d-fed4-4c69-9506-4dc84107bbaa.png" width="600">


To end this, we propose a new large-scale dataset, **YorkTag**, that provides paired blurred and sharp images containing AprilTags and ArUcos. For the sake of obtaining ideal sharp images, we employ the iPhone 12 with the DJI OM 4 stabilizer to capture high-resolution videos. Detailed introduction of the blurred and sharp image pairs generation is available in our paper. Our training set consists of 1577 image pairs, and test set consists of 497 image pairs totalling 2074 blurry-sharp image pairs. We will keep augmenting the yorktag dataset later on.   
Link to the YorkTag dataset utilized in our paper: https://drive.google.com/file/d/1S3wVptR_mzrntuCtEarkXHE6d1zN6jd3/view?usp=sharing
 
<img src="https://user-images.githubusercontent.com/58899542/132930869-a66fb452-9579-4922-980a-94bc5e067ae9.jpeg" width="900">


# Training
## Command
```python train.py``` A video tutorial is available at: https://www.youtube.com/watch?v=JSCA2x3NBHs <br>
By default training script will load conifguration from config/config.yaml
files_a parameter represents blurry images and files_b represents sharp images
modify config.yaml file to change the generator model.
Available model scripts are:
- Ghostnet + Half Instance Normalization (HIN) + Ghost module (GM)
- MobilenetV2


# Testing and Inference
For single image inference,
```python predict.py /path/to/image.png --weights_path=/path/to/weights``` <br>
by default output is written under submit directory

Note: 'model' parameters in config.yaml must correspond to the weights <br>
For testing on single image,<br>
```python test_metrics.py --img_folder=/path/to/image.png --weights_path=/path/to/weights --new_gopro``` <br>
For testing on the dataset utilized in this work,<br>
```python test_metrics.py --img_folder=/base/directory/of/GOPRO/test/blur --weights_path=/path/to/weights --new_gopro ```


# Pre-trained models
For fair comparison we used the same mobilenet model as the original DeblurGANv2 (https://github.com/VITA-Group/DeblurGANv2) and 
trained all models from **scratch** on the GOPRO dataset (https://drive.google.com/file/d/1KStHiZn5TNm2mo3OLZLjnRvd0vVFCI0W/view).
The metrics in the above table are to illustrate the superiority of Ghost-DeblurGAN over the original deblurGAN-v2 (mobilenetV2). Note that to obtain the deblurring performance shown in the visual comparison, the weights trained on the mix of YorkTag and GoPro should be adopted. These weights are coming soon.
<table align="center">
    <tr>
        <th>Dataset</th>
        <th>Model</th>
        <th>FLOPs</th>
        <th>PSNR/ SSIM</th>
        <th>Link</th>
    </tr>
    <tr>
        <td rowspan="2">GoPro Test Dataset</td>     
        <td>DeblurGAN-v2 (MobileNetV2)</td>
        <td>43.75G</td>
        <td>28.40/ 0.917</td>
        <td><a href="./trained_weights/fpn_ghostnet_gm_hin.h5">fpn_mobilnet_v2.h5</a></td>        
    </tr>
    <tr>
        <td>Ghost-DeblurGAN (Ours)</td>
        <td>20.51G</td>
        <td>28.79/ 0.920</td>
        <td><a href="./trained_weights/fpn_ghostnet_gm_hin.h5">fpn_ghostnet_gm_hin.h5</a></td>
    </tr>
   
</table>

# Citation
If you find this work helpful for your research, please cite our paper:
```
@misc{liu2021ghostdeblurgan,
      title={Ghost-DeblurGAN and Its Application to Fiducial Marker System}, 
      author={Yibo Liu and Amaldev Haridevan and Hunter Schofield and Jinjun Shan},
      year={2021},
      eprint={2109.03379},
      archivePrefix={arXiv},
      primaryClass={eess.IV}
}
```
