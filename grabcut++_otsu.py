import os
import  cv2
import sys
from metrics import seg_metrics
import imageio
import numpy as np
import json
from skimage.draw import polygon
from skimage.transform import resize
sys.path.append("/DATA/mishra.4/mishra.4/dsve/")
sys.path.append("/DATA/mishra.4/mishra.4/DeepGrabCut/")
os.chdir('/DATA/mishra.4/mishra.4/dsve')
from dsve.interactive_class import fbib
from DeepGrabCut.demo2  import deepgrabcut
# device = torch.device("cpu") # uncomment to run with cpu
os.environ["CUDA_DEVICE_ORDER"]="PCI_BUS_ID"
# The GPU id to use , "0" to  "7" 
os.environ["CUDA_VISIBLE_DEVICES"]="6"

# Utility function to Create Binary masks from segmentation polygons
def segToMask(S, h, w):
        M = np.zeros((h, w), dtype=np.bool)
        for s in S:
            N = len(s)
            rr, cc = polygon(np.array(s[1:N:2]), np.array(s[0:N:2]))  # (y, x)
            M[rr, cc] = 1
        return M

class outputs:

    def cal_metrics(self, logits, mask):
        metrics = seg_metrics(logits, mask)
        return metrics
    
    def save_results(self, img, mask, logits, heatmap, name):
        temp = np.zeros((img.shape[0], img.shape[1]*4, img.shape[2]))
        temp[:, :img.shape[1], :] = img
        temp[:, img.shape[1]:img.shape[1]*2, :] = mask
        temp[:, img.shape[1]*2:img.shape[1]*3, :] = logits
        temp[:, img.shape[1]*3:, :] = heatmap
        imageio.imwrite('/DATA/mishra.4/mishra.4/fbib_deepgrabcut_results/Otsu/' + name + '.jpg', temp)


output_shape = 320
data_root = '/DATA/mishra.4/mishra.4/Ref_dataset/refcocog/val/'
mask_root = data_root + 'instances.json'
img_root = '/DATA/mishra.4/mishra.4/refer/data/images/train2014/images/train2014/'
embeddings_path = data_root + 'embeddings/'
with open(mask_root, 'r') as openfile:
			dict_list = json.load(openfile)
name_list = os.listdir(embeddings_path)
length_names = len(name_list)
output = outputs()
dice, jaccard, recall, precision = [], [], [], []
hm_obj=fbib()
seg_obj=deepgrabcut()

count = 0

for index in range(length_names):
    name = name_list[index]
    name_image = name.rstrip().split(".")[0] + '.jpg'
    temp_dict = {}
    for element in dict_list:
        if element['image']['file_name'] == name_image:
            temp_dict.update(element)
    
    seg_poly = temp_dict['mask']['segmentation']
    caption = temp_dict['image']['sentences'][0]['sent']
    # print('---------------{}---------------'.format(caption))
    if name_image.split('_') == 3:
        img_path = img_root + name_image
        img = np.asarray(imageio.imread(img_path))
    else:
        temp = name.rstrip().split(".")[0].split('_')
        img_path = img_root + temp[0] + '_' + temp[1] + '_' + temp[2] +'.jpg'
        img = np.asarray(imageio.imread(img_path))

    if len(img.shape) == 3:
        h , w , c = img.shape
    else:
        h, w = img.shape
        img = np.stack((img, img, img), axis = 2)
    #print('***********{}*********'.format(seg_poly))
    mask = segToMask(seg_poly, h, w)
    # print(np.amax(mask), np.amin(mask))
    mask = mask * 255
    # print(np.amax(mask), np.amin(mask))
    # print(mask.shape)
    # print(type(mask))
    mask = resize(mask, (output_shape, output_shape), preserve_range= True)
    # print(np.amax(mask), np.amin(mask))
    # print(mask.shape)
    # print(type(mask))
    # print(mask)
    heatmap_output = hm_obj.main_heatmap(img_path,caption)

    ''' Applying Otsu's Thresholding'''
    heatmap_output = (heatmap_output - np.amin(heatmap_output))/ (np.amax(heatmap_output) - np.amin(heatmap_output))
    heatmap_output = heatmap_output * 255
    heatmap_output = heatmap_output.astype(np.uint8)
    print(heatmap_output.shape)
    print(heatmap_output.dtype)
    ret, heatmap_output = cv2.threshold(heatmap_output, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    prediction , prediction_mask= seg_obj.return_segment(img,heatmap_output)
    prediction_mask = resize(prediction_mask, (output_shape, output_shape), preserve_range= True)
    # imageio.imwrite("/DATA/mishra.4/mishra.4/fbib_deepgrabcut_results/" + caption+name_image, prediction)
    # imageio.imwrite("/DATA/mishra.4/mishra.4/fbib_deepgrabcut_results/heatmap/" + name_image, heatmap_output)
    # imageio.imwrite("/DATA/mishra.4/mishra.4/fbib_deepgrabcut_results/mask/" + name_image, prediction_mask)
    # imageio.imwrite("/DATA/mishra.4/mishra.4/fbib_deepgrabcut_results/GTmask/" + name_image, mask)
    metrics = output.cal_metrics(prediction_mask, mask)
    dice.append(metrics.dice_coefficient())
    jaccard.append(metrics.jaccard())
    recall.append(metrics.recall())
    precision.append(metrics.precision())

    mask_3 = np.stack((mask, mask, mask), axis = 2)
    prediction_3 = np.stack((prediction_mask, prediction_mask, prediction_mask), axis=2)
    img = resize(img, (output_shape, output_shape), preserve_range = True)
    heatmap_output = np.stack((heatmap_output, heatmap_output, heatmap_output), axis =2)
    heatmap_output = resize(heatmap_output, (output_shape, output_shape), preserve_range = True)
    # print(mask_3.shape)
    # print(prediction_3.shape)
    # print(img.shape)
    # print(heatmap_output.shape)
    # print(np.amax(heatmap_output), np.amin(heatmap_output))
    #output.save_results(img, mask_3, prediction_3, heatmap_output, caption)
    print(index)
    # if count ==10:
    #     break


print(sum(dice)/len(dice))
print(sum(jaccard)/len(jaccard))
print(sum(recall)/len(recall))
print(sum(precision)/len(precision))
