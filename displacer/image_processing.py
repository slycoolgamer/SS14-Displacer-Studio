import numpy as np
from PIL import Image, ImageDraw
from collections import deque
import math

def apply_ss14_displacement(reference, displacement, displacement_size=1.0):
    """
    Apply SS14-style displacement mapping with simplified pixel-perfect movement.
    
    Args:
        reference: PIL Image - the reference image to displace
        displacement: PIL Image - the displacement map
        displacement_size: float - displacement multiplier (default 1.0 for one-to-one pixel movement)
    
    Returns:
        PIL Image - the displaced image
    """
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
            
            # Skip transparent pixels in displacement map
            if disp_pixel[3] == 0:
                result_data[y, x] = [0, 0, 0, 0]
                continue
            
            # Calculate offset using simplified displacement calculation
            # Convert from 0-255 range to -127 to +127 range, then apply displacement_size
            offset_x = (disp_pixel[0] - 128) * displacement_size
            offset_y = (disp_pixel[1] - 128) * displacement_size
            
            # Calculate sample coordinates with rounding for pixel-perfect sampling
            sample_x = max(0, min(width - 1, int(round(x + offset_x))))
            sample_y = max(0, min(height - 1, int(round(y + offset_y))))
            
            # Direct pixel sampling (no interpolation)
            result_data[y, x] = ref_data[sample_y, sample_x]
                        
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
