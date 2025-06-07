import numpy as np
from PIL import Image, ImageDraw
from collections import deque
import math

def clean_displacement_map(displacement_map):
    """
    Ensure all transparent pixels have the neutral color (128,128,0)
    """
    if not displacement_map:
        return None
    
    disp_data = np.array(displacement_map)
    height, width = disp_data.shape[:2]
    
    for y in range(height):
        for x in range(width):
            if disp_data[y, x, 3] == 0:  # If transparent
                disp_data[y, x] = [128, 128, 0, 0]  # Set to neutral but transparent
    
    return Image.fromarray(disp_data, 'RGBA')

def apply_ss14_displacement(reference, displacement):
    """Fixed displacement function matching the original accuracy"""
    if not reference or not displacement:
        return None
        
    if displacement.size != reference.size:
        displacement = displacement.resize(reference.size, Image.NEAREST)
        
    width, height = reference.size
    disp_data = np.array(displacement)
    ref_data = np.array(reference)
    result_data = np.zeros((height, width, 4), dtype=np.uint8)
    
    # Use the original displacement_size of 1.0 for one-to-one pixel movement
    displacement_size = 1.0
    
    for y in range(height):
        for x in range(width):
            disp_pixel = disp_data[y, x]
            
            if disp_pixel[3] == 0:
                result_data[y, x] = [0, 0, 0, 0]
                continue
                
            # Use the original simple offset calculation
            offset_x = (disp_pixel[0] - 128) * displacement_size
            offset_y = (disp_pixel[1] - 128) * displacement_size
            
            sample_x = max(0, min(width - 1, int(round(x + offset_x))))
            sample_y = max(0, min(height - 1, int(round(y + offset_y))))
            
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

def paint_displacement_pixel(displacement_map, x, y, color, allow_transparent=True):
    """
    Paint a pixel on the displacement map while maintaining proper neutral color
    """
    if not displacement_map:
        return displacement_map
    
    disp_data = np.array(displacement_map)
    
    if x < 0 or x >= disp_data.shape[1] or y < 0 or y >= disp_data.shape[0]:
        return displacement_map
    
    # When making transparent, set to neutral color with alpha=0
    if color[3] == 0 and allow_transparent:
        disp_data[y, x] = [128, 128, 0, 0]  # Neutral color but transparent
    else:
        disp_data[y, x] = color
    
    return Image.fromarray(disp_data, 'RGBA')

def paint_displacement_brush(displacement_map, x, y, brush_size, direction, strength, drawing_mode="directional", selection_mask=None):
    if not displacement_map:
        return displacement_map
        
    disp_data = np.array(displacement_map)
    height, width = disp_data.shape[:2]
    radius = brush_size // 2
    
    direction_values = {
        "right": (128 + strength, 128, 0, 255),
        "left": (128 - strength, 128, 0, 255),
        "up": (128, 128 - strength, 0, 255),
        "down": (128, 128 + strength, 0, 255)
    }
    
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            px, py = x + dx, y + dy
        
            if (px < 0 or py < 0 or px >= width or py >= height):
                continue
            
            if math.sqrt(dx*dx + dy*dy) > radius:
                continue
            
            if selection_mask and selection_mask.getpixel((px, py)) == 0:
                continue
            
            if drawing_mode == "erase":
                # Set to neutral color with alpha=0 when erasing
                disp_data[py, px] = [128, 128, 0, 0]
            else:
                disp_data[py, px] = direction_values[direction]
    
    return Image.fromarray(disp_data, 'RGBA')

def initialize_displacement_canvas(width, height, fill_neutral=True):
    """
    Create a new displacement map canvas, optionally filled with neutral color
    """
    if fill_neutral:
        # Fill with neutral displacement color
        canvas = Image.new('RGBA', (width, height), (128, 128, 0, 255))
    else:
        # Create transparent canvas
        canvas = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    
    return canvas

def create_neutral_displacement_brush():
    """Returns the neutral displacement color (128, 128, 0, 255)"""
    return (128, 128, 0, 255)

def create_displacement_brush(direction='neutral', strength=1.0):
    """
    Create a displacement brush color for different directions
    
    Args:
        direction: 'neutral', 'up', 'down', 'left', 'right', or 'custom'
        strength: displacement strength (0.0 to 1.0)
    
    Returns:
        RGBA tuple for the displacement color
    """
    base = 128
    offset = int(127 * strength)
    
    if direction == 'neutral':
        return (128, 128, 0, 255)
    elif direction == 'up':
        return (128, min(255, base + offset), 0, 255)
    elif direction == 'down':
        return (128, max(0, base - offset), 0, 255)
    elif direction == 'left':
        return (max(0, base - offset), 128, 0, 255)
    elif direction == 'right':
        return (min(255, base + offset), 128, 0, 255)
    else:
        return (128, 128, 0, 255)  # Default to neutral

def magic_select_flood_fill(image, x, y, tolerance=32):
    """
    Fixed magic select using iterative flood fill to avoid stack overflow
    """
    if not image:
        return None
        
    try:
        w, h = image.size
        
        # Ensure coordinates are within bounds
        if x < 0 or x >= w or y < 0 or y >= h:
            return None
            
        # Convert to RGB for comparison (ignore alpha for selection)
        img_rgb = image.convert('RGB')
        img_array = np.array(img_rgb)
        
        # Get seed color
        seed_color = img_array[y, x]
        
        # Create selection mask
        mask = np.zeros((h, w), dtype=np.uint8)
        visited = np.zeros((h, w), dtype=bool)
        
        # Iterative flood fill using queue to avoid recursion limits
        queue = deque([(x, y)])
        visited[y, x] = True
        
        while queue:
            cx, cy = queue.popleft()
            
            # Check if current pixel matches seed color within tolerance
            current_color = img_array[cy, cx]
            color_diff = np.sum(np.abs(current_color.astype(int) - seed_color.astype(int)))
            
            if color_diff <= tolerance:
                mask[cy, cx] = 255
                
                # Add neighbors to queue
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = cx + dx, cy + dy
                    
                    if (0 <= nx < w and 0 <= ny < h and not visited[ny, nx]):
                        visited[ny, nx] = True
                        queue.append((nx, ny))
        
        # Convert mask to PIL Image
        selection = Image.fromarray(mask, "L")
        return selection
        
    except Exception as e:
        print(f"Magic Select Error: {str(e)}")
        return None
