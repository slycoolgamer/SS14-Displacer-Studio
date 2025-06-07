import numpy as np
from PIL import Image, ImageDraw
from collections import deque
import math

def apply_ss14_displacement(reference, displacement, displacement_size=127):
    if not reference or not displacement:
        return None
        
    if displacement.size != reference.size:
        displacement = displacement.resize(reference.size, Image.NEAREST)
        
    width, height = reference.size
    disp_data = np.array(displacement)
    ref_data = np.array(reference)
    result_data = np.zeros((height, width, 4), dtype=np.uint8)
    
    for y in range(height):
        for x in range(width):
            disp_pixel = disp_data[y, x]
            
            if disp_pixel[3] == 0:
                result_data[y, x] = [0, 0, 0, 0]
                continue
            
            offset_x = ((disp_pixel[0] - 128) / 127.0) * displacement_size
            offset_y = ((disp_pixel[1] - 128) / 127.0) * displacement_size
            offset_y = -offset_y
            
            max_offset = displacement_size * 0.5
            offset_x = max(-max_offset, min(max_offset, offset_x))
            offset_y = max(-max_offset, min(max_offset, offset_y))
            
            sample_x = x + offset_x
            sample_y = y + offset_y
            
            if (sample_x < -0.5 or sample_x >= width - 0.5 or 
                sample_y < -0.5 or sample_y >= height - 0.5):
                result_data[y, x] = [0, 0, 0, 0]
            else:
                sample_x_floor = int(np.floor(sample_x))
                sample_y_floor = int(np.floor(sample_y))
                sample_x_ceil = sample_x_floor + 1
                sample_y_ceil = sample_y_floor + 1
                
                sample_x_floor = max(0, min(width - 1, sample_x_floor))
                sample_y_floor = max(0, min(height - 1, sample_y_floor))
                sample_x_ceil = max(0, min(width - 1, sample_x_ceil))
                sample_y_ceil = max(0, min(height - 1, sample_y_ceil))
                
                fx = sample_x - sample_x_floor
                fy = sample_y - sample_y_floor
                
                tl = ref_data[sample_y_floor, sample_x_floor]
                tr = ref_data[sample_y_floor, sample_x_ceil]
                bl = ref_data[sample_y_ceil, sample_x_floor]
                br = ref_data[sample_y_ceil, sample_x_ceil]
                
                top = tl * (1 - fx) + tr * fx
                bottom = bl * (1 - fx) + br * fx
                final = top * (1 - fy) + bottom * fy
                
                result_data[y, x] = final.astype(np.uint8)
                        
    return Image.fromarray(result_data, 'RGBA')
    
def composite_images(background, foreground):
    if not background or not foreground:
        return foreground or background
        
    if background.size != foreground.size:
        background = background.resize(foreground.size, Image.NEAREST)
        
    result = background.copy()
    result.paste(foreground, (0, 0), foreground)
    return result

def create_diagonal_pattern(size, spacing=8):
    w, h = size
    pattern = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(pattern)
    
    for i in range(-h, w, spacing):
        draw.line([(i, 0), (i + h, h)], fill=(255, 255, 255, 128), width=1)
    
    return pattern

def create_selection_border(mask, thickness=2):
    if not mask:
        return None
        
    try:
        mask_array = np.array(mask)
        from scipy import ndimage
        dilated = ndimage.binary_dilation(mask_array > 0, iterations=thickness)
        border = dilated & (mask_array == 0)
        border_img = Image.fromarray((border * 255).astype(np.uint8), "L")
        return border_img
    except ImportError:
        w, h = mask.size
        border = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(border)
        mask_array = np.array(mask)
        
        for y in range(1, h-1):
            for x in range(1, w-1):
                if mask_array[y, x] == 0:
                    neighbors = [
                        mask_array[y-1, x], mask_array[y+1, x],
                        mask_array[y, x-1], mask_array[y, x+1]
                    ]
                    if any(n > 0 for n in neighbors):
                        draw.point((x, y), fill=255)
        
        return border
