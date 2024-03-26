#!/usr/bin/env -S pkgx python@3
import argparse
from PIL import Image
import imageio
from skimage.color import rgb2gray
from skimage.feature import canny
from skimage.morphology import dilation
from scipy import ndimage as ndi
from skimage.measure import label
from skimage.color import label2rgb
from skimage.measure import regionprops
from PIL import ImageFont
from PIL import ImageDraw
import numpy as np

import os

class Kumiko:
    options = {}
    def __init__(self, options = None):
        options = options or {}
    
    def do_bboxes_overlap(self, a, b):
        return (
            a[0] < b[2] and
            a[2] > b[0] and
            a[1] < b[3] and
            a[3] > b[1]
        )

    def merge_bboxes(self, a, b):
        return (
            min(a[0], b[0]),
            min(a[1], b[1]),
            max(a[2], b[2]),
            max(a[3], b[3])
        )

    def are_bboxes_aligned(self, a, b, axis):
        return (
            a[0 + axis] < b[2 + axis] and
            b[0 + axis] < a[2 + axis]
        )
    def cluster_bboxes(self, bboxes, axis=0):
        
        clusters = []

        # Regroup bboxes which overlap along the current axis.
        # For instance, two panels on the same row overlap
        # along their verticial coordinate.
        for bbox in bboxes:
            for cluster in clusters:
                if any(
                    self.are_bboxes_aligned(b, bbox, axis=axis)
                    for b in cluster
                ):
                    cluster.append(bbox)
                    break
            else:
                clusters.append([bbox])

        # We want rows to be ordered from top to bottom, and
        # columns to be ordered from left to right.
        clusters.sort(key=lambda c: c[0][0 + axis])

        # For each row, we want to cluster the panels of that
        # row into columns, etc. etc.
        for i, cluster in enumerate(clusters):
            if len(cluster) > 1:
                clusters[i] = self.cluster_bboxes(
                    bboxes=cluster,
                    axis=1 if axis == 0 else 0
                )

        return clusters

    def flatten(self, l):
        for el in l:
            if isinstance(el, list):
                yield from self.flatten(el)
            else:
                yield el

    def read_transparent_png(self, filename):
        image_4channel = imageio.v3.imread(filename)
        alpha_channel = image_4channel[:,:,3]
        rgb_channels = image_4channel[:,:,:3]

        # White Background Image
        white_background_image = np.ones_like(rgb_channels, dtype=np.uint8) * 255

        # Alpha factor
        alpha_factor = alpha_channel[:,:,np.newaxis].astype(np.float32) / 255.0
        alpha_factor = np.concatenate((alpha_factor,alpha_factor,alpha_factor), axis=2)

        # Transparent Image Rendered on White Background
        base = rgb_channels.astype(np.float32) * alpha_factor
        white = white_background_image.astype(np.float32) * (1 - alpha_factor)
        final_image = base + white
        return final_image.astype(np.uint8)

    def parse_image(self, filename, urls = None):
        im = self.read_transparent_png(filename) #[:,:,:3]
        Image.fromarray(im)
        ## Convert to gray scale
        grayscale = rgb2gray(im[:,:,:3])
        Image.fromarray((grayscale * 255).astype('uint8'), 'L')
        ## canny edge finding
        edges = canny(grayscale)
        Image.fromarray(edges)
        ## Dilation
        thick_edges = dilation(dilation(edges))
        Image.fromarray(thick_edges)
        ## Filling the wholes
        segmentation = ndi.binary_fill_holes(thick_edges)
        Image.fromarray(segmentation)
        ## Labeling
        labels = label(segmentation)
        # Image.fromarray(np.uint8(label2rgb(labels, bg_label=0) * 255))
        ## Regrouping patches into panels
        regions = regionprops(labels)
        panels = []

        for region in regions:
            
            for i, panel in enumerate(panels):
                if self.do_bboxes_overlap(region.bbox, panel):
                    print('changing panel ' + panel)
                    panels[i] = self.merge_bboxes(panel, region.bbox)
                    break
            else:
                print(region.bbox)
                panels.append(region.bbox)

        ## post-processing step to remove small panels
        for i, bbox in reversed(list(enumerate(panels))):
            area = (bbox[2] - bbox[0]) * (bbox[3] - bbox[1])
            if area < 0.01 * im.shape[0] * im.shape[1]:
                del panels[i]
        panel_img = np.zeros_like(labels)

        ## visualization 
        for i, bbox in enumerate(panels, start=1):
            panel_img[bbox[0]:bbox[2], bbox[1]:bbox[3]] = i

        # TODO fix - Image.fromarray(label2rgb(panel_img, bg_label=0) * 255).astype('uint8')
        ## clustering 
        clusters = self.cluster_bboxes(panels)
        print(clusters)

        ## more visualization
        img = Image.fromarray(im)
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()

        for i, bbox in enumerate(self.flatten(clusters), start=1):
            x, y, w, h = draw.textbbox(xy=[0,0], text=str(i), font=font)
            x = (bbox[1] + bbox[3] - w) / 2
            y = (bbox[0] + bbox[2] - h) / 2
            draw.text((x, y), str(i), (255, 215, 0), font=font)

        ## save them 
        os.makedirs('panels', exist_ok=True)

        for i, bbox in enumerate(self.flatten(clusters)):
            panel = im[bbox[0]:bbox[2], bbox[1]:bbox[3]]
            Image.fromarray(panel).save(f'panels/{i}.png')



parser = argparse.ArgumentParser(description = 'Kumiko CLI')
parser.add_argument('-i', '--input', nargs = '+', required = True, help = 'A file or folder name to parse')
args = parser.parse_args()

k = Kumiko()

if len(args.input) == 1 and os.path.isfile(args.input[0]):
    filename = args.input[0]
    k.parse_image(filename)


