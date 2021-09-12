import math

import torch
import torch.nn as nn
#import logging
#from mobilenet_v2 import MobileNetV2
#from pretrainedmodels import inceptionresnetv2
#import fpn_mobilenet as mn
import numpy as np
import cv2
#from pypapi import events, papi_high as high
#from thop import profile, clever_format
from pthflops import count_ops

class GhostModule(nn.Module):
    """class that replaces Conv2D layers"""
    def __init__(self, inp, oup, kernel_size=1, ratio=2, dw_size=3, stride=1, relu=True,  bias= False):
        super(GhostModule, self).__init__()
        self.oup = oup
        init_channels = math.ceil(oup / ratio)
        new_channels = init_channels*(ratio-1)

        self.primary_conv = nn.Sequential(
            nn.Conv2d(inp, init_channels, kernel_size, stride, kernel_size//2, bias=bias),
            nn.InstanceNorm2d(init_channels),
            nn.ReLU(inplace=True) if relu else nn.Sequential(),
        )

        self.cheap_operation = nn.Sequential(
            nn.Conv2d(init_channels, new_channels, dw_size, 1, dw_size//2, groups=init_channels, bias=bias),
            nn.InstanceNorm2d(new_channels),
            nn.ReLU(inplace=True) if relu else nn.Sequential(),
        )

    def forward(self, x):
        #print(f'\n\n{x.shape}\n\n')
        x1 = self.primary_conv(x.repeat(2,1,1,1))
        x2 = self.cheap_operation(x1)
        #print(f'\n\n{x1.shape}\n\n')
        #print(f'\n\n{x2.shape}\n\n')
        out = torch.cat([x1[0,:,:,:].unsqueeze(0),x2[0,:,:,:].unsqueeze(0)], dim=1)
        #print(f'\n\n{out.shape}\n\n')
        return out[:,:self.oup,:,:]

class FPNHead(nn.Module):

    """"this is the FPNHead class common to all backbones"""
    def __init__(self, num_in, num_mid, num_out):
        super(FPNHead, self).__init__()

        self.block0 = GhostModule(num_in, num_mid, kernel_size= 3, bias= False)
        self.block1 = GhostModule(num_mid, num_out, kernel_size= 3,  bias= False)

    def forward(self, x):
        x = nn.functional.relu(self.block0(x), inplace=True)
        x = nn.functional.relu(self.block1(x), inplace=True)
        return x

class FPNGhostNetv2(nn.Module):

    def __init__(self, norm_layer, output_ch=3, num_filters=64, num_filters_fpn=128, pretrained=True):
        super(FPNGhostNetv2, self).__init__()
        #print("\n\n GhostNET constructed \n\n")

        # Feature Pyramid Network (FPN) with four feature maps of resolutions
        # 1/4, 1/8, 1/16, 1/32 and `num_filters` filters for all feature maps.

        self.fpn = FPN(num_filters=num_filters_fpn, norm_layer=norm_layer, pretrained=pretrained)

        # The segmentation heads on top of the FPN

        self.head1 = FPNHead(num_filters_fpn, num_filters, num_filters)
        self.head2 = FPNHead(num_filters_fpn, num_filters, num_filters)
        self.head3 = FPNHead(num_filters_fpn, num_filters, num_filters)
        self.head4 = FPNHead(num_filters_fpn, num_filters, num_filters)

        self.smooth = nn.Sequential(
            GhostModule(4*num_filters, num_filters, kernel_size=3),
            norm_layer(num_filters),
            nn.ReLU(),
        )

        self.smooth2 = nn.Sequential(
            GhostModule(num_filters, num_filters //2, kernel_size= 3),
            norm_layer(num_filters // 2),
            nn.ReLU(),
        )

        self.final = GhostModule(num_filters // 2, output_ch, kernel_size= 3)

    def unfreeze(self):
        self.fpn.unfreeze()

    def forward(self, x):
        #print(x.shape)
        map0, map1, map2, map3, map4 = self.fpn(x)

        map4 = nn.functional.interpolate(self.head4(map4), scale_factor=8, mode="nearest")
        map3 = nn.functional.interpolate(self.head3(map3), scale_factor=4, mode="nearest")
        map2 = nn.functional.interpolate(self.head2(map2), scale_factor=2, mode="nearest")
        map1 = nn.functional.interpolate(self.head1(map1), scale_factor=1, mode="nearest")

        """for i in range(1,5):
            eval(f'print(map{i}.shape)')"""

        smoothed = self.smooth(torch.cat([map4, map3, map2, map1], dim=1))
        smoothed = nn.functional.interpolate(smoothed, scale_factor=4, mode="nearest")
        #print(smoothed.shape)
        #print(map0.shape)
        smoothed = self.smooth2(smoothed + map0)
        smoothed = nn.functional.interpolate(smoothed, scale_factor=2, mode="nearest")

        final = self.final(smoothed)
        res = torch.tanh(final) + x

        return torch.clamp(res, min=-1, max=1)

class FPN(nn.Module):

    def __init__(self, norm_layer, num_filters=128, pretrained=True):
        """Creates an `FPN` instance for feature extraction.
        Args:
          num_filters: the number of filters in each output pyramid level
          pretrained: use ImageNet pre-trained backbone feature extractor
        """

        super(FPN, self).__init__()
        model = torch.hub.load('huawei-noah/ghostnet', 'ghostnet_1x', pretrained=pretrained)
        model.train()
        self.features= model.blocks
        """model.blocks has 10 elements"""
        #print(len(self.blocks))
        self.enc0 = nn.Sequential(model.conv_stem, model.bn1, model.act1) # nn.Sequential(*self.features[0:2])
        self.enc1 = nn.Sequential( *self.features[0:4])
        self.enc2 = nn.Sequential(*self.features[4:7])
        self.enc3 = nn.Sequential(*self.features[7:10])
        self.enc4 = nn.Sequential( model.global_pool, model.conv_head, model.act2)

        self.td1 = nn.Sequential(GhostModule(num_filters, num_filters, kernel_size= 3, bias= True),
                                 norm_layer(num_filters),
                                 nn.ReLU(inplace=True))
        self.td2 = nn.Sequential(GhostModule(num_filters, num_filters, kernel_size= 3, bias= True),
                                 norm_layer(num_filters),
                                 nn.ReLU(inplace=True))
        self.td3 = nn.Sequential(GhostModule(num_filters, num_filters, kernel_size= 3, bias= True),
                                 norm_layer(num_filters),
                                 nn.ReLU(inplace=True))

        self.lateral4 = GhostModule(1280, num_filters, kernel_size= 1, bias= False)#nn.Conv2d(1280, num_filters, kernel_size=1, bias=False)
        self.lateral3 = GhostModule(960, num_filters, kernel_size= 1, bias= False)#nn.Conv2d(960, num_filters, kernel_size=1, bias=False)
        self.lateral2 = GhostModule(112, num_filters, kernel_size= 1, bias= False)#nn.Conv2d(112, num_filters, kernel_size=1, bias=False)
        self.lateral1 = GhostModule(40, num_filters, kernel_size= 1, bias= False)#nn.Conv2d(40, num_filters, kernel_size=1, bias=False)
        self.lateral0 = GhostModule(16, num_filters//2, kernel_size= 1, bias= False)# nn.Conv2d(16, num_filters // 2, kernel_size=1, bias=False)

        for param in self.features.parameters():
            param.requires_grad = False

    def unfreeze(self):
        for param in self.features.parameters():
            param.requires_grad = True

    def forward(self, x):

        # Bottom-up pathway, from ResNet
        #print(x.shape)
        enc0 = self.enc0(x)

        enc1 = self.enc1(enc0)  # 256

        enc2 = self.enc2(enc1)  # 512

        enc3 = self.enc3(enc2)  # 1024

        enc4 = self.enc4(enc3)  # 2048


        # Lateral connections

        lateral4 = self.lateral4(enc4)
        lateral3 = self.lateral3(enc3)
        lateral2 = self.lateral2(enc2)
        lateral1 = self.lateral1(enc1)
        lateral0 = self.lateral0(enc0)

        # Top-down pathway
        map4 = lateral4
        """print(f'shape of lateral3:{lateral3.shape}')
        print(f'shape of map4: {map4.shape}')"""
        map3 = self.td1(lateral3 + nn.functional.interpolate(map4, scale_factor=8, mode="nearest"))
        map2 = self.td2(lateral2 + nn.functional.interpolate(map3, scale_factor=2, mode="nearest"))
        """for i in range(2,5):
            print(f'map{i}')
            eval(f'print(map{i}.shape)')"""
       # print(f'shape of lateral1:{lateral1.shape}')

        map1 = self.td3(lateral1 + nn.functional.interpolate(map2, scale_factor=2, mode="nearest"))
        map4= nn.functional.interpolate(lateral4, scale_factor=4, mode="nearest")
       # map1= nn.functional.upsample(map1, scale_factor= 0.5, mode= "nearest")
        return lateral0, map1, map2, map3, map4


"""
def load_ghostnet():

    model = torch.hub.load('huawei-noah/ghostnet', 'ghostnet_1x', pretrained=True)
    model.eval()
    return model

def load_mobilenet():

    net = MobileNetV2(n_class=1000)
    return net.eval()

def load_inception():

    model= inceptionresnetv2(num_classes=1000, pretrained='imagenet')
    return model.eval()

if __name__=="__main__":

    model= load_mobilenet()
    c_i= 0
    logging.basicConfig(filename='model.log', filemode='w', level= logging.DEBUG)
    logging.info(model)
    for m in model.modules():

        c_i+= 1
        #print(m)
    #print(model.blocks)
    print(f'total modules: {c_i}')
"""
def main(input_, time):
    #input_=torch.rand([1,3, 256, 256])
    #fpn_ = FPN(nn.BatchNorm2d)
    #output_ = fpn_(input_)
    """for i in range(5):
        eval(f'print(output_[{i}].shape)') """
    #input_= torch.Tensor(input_)
    fpn = FPNGhostNetv2(nn.InstanceNorm2d)
    #fpn.cuda()
    #input_.cuda()
    TIME_I= time.time()
    high.start_counters([events.PAPI_DP_OPS, ])

    output_ = fpn(input_)
    flops= high.stop_counters()
    TIME_F= time.time()
    return TIME_F-TIME_I, flops
    #print(output_.shape)
    #output_ = torch.squeeze(output_)
    #output_ = output_.detach().numpy()
    #print(output_.shape)
    #output_ = np.transpose(output_, [0, 3, 2, 1])
    #print(output_.shape)

    #cv2.imshow("img", output_[0])
    #cv2.imshow("input", np.transpose(input_[0].squeeze().detach().numpy(), [2, 1, 0]))
    #cv2.waitKey(5000)
    #cv2.imshow("img", output_)
    #cv2.imshow("input", np.transpose(input_.squeeze().detach().numpy(), [2, 1, 0]))
    #cv2.waitKey(0)

if __name__== "__main__":

    import time
    arg = torch.rand([2, 3, 256, 256])
    #TIME_I= time.time()
    #t_run, flops= main(arg, time)
    #TIME_F= time.time()
    #return TIME_F-TIME_I
    model =  FPNGhostNetv2(nn.InstanceNorm2d)
    count_ops(model, arg)
    #time, flops= main(arg, time)
    #macs, params = profile(model, inputs=(arg,))
    #macs, params = clever_format([macs, params], "%.3f")
    #print(f'MACS of ghostnet v2: {macs}')
    #print(f'PARAMS ghostnetv2: {params}')


