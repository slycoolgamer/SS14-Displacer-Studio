import numpy as np
from PIL import Image, ImageDraw
from collections import deque
import math

def clean_displacement_map(displacement_map):
    """
    Ensure all transparent pixels have the neutral color (128,128,0) - Vectorized
    """
    if not displacement_map:
        return None
    
    disp_data = np.array(displacement_map)
    
    # Vectorized: Set all transparent pixels to neutral color in one operation
    transparent_mask = disp_data[:, :, 3] == 0
    disp_data[transparent_mask] = [128, 128, 0, 0]
    
    return Image.fromarray(disp_data, 'RGBA')

def apply_ss14_displacement(reference, displacement):
    """Optimized displacement function using vectorized operations"""
    if not reference or not displacement:
        return None
        
    if displacement.size != reference.size:
        displacement = displacement.resize(reference.size, Image.NEAREST)
        
    width, height = reference.size
    disp_data = np.array(displacement)
    ref_data = np.array(reference)
    
    # Create coordinate grids
    y_coords, x_coords = np.mgrid[0:height, 0:width]
    
    # Vectorized displacement calculation
    displacement_size = 1.0
    offset_x = (disp_data[:, :, 0].astype(np.float32) - 128) * displacement_size
    offset_y = (disp_data[:, :, 1].astype(np.float32) - 128) * displacement_size
    
    # Calculate sample coordinates
    sample_x = np.clip(np.round(x_coords + offset_x).astype(np.int32), 0, width - 1)
    sample_y = np.clip(np.round(y_coords + offset_y).astype(np.int32), 0, height - 1)
    
    # Vectorized sampling
    result_data = ref_data[sample_y, sample_x]
    
    # Handle transparent displacement pixels
    transparent_mask = disp_data[:, :, 3] == 0
    result_data[transparent_mask] = [0, 0, 0, 0]
    
    return Image.fromarray(result_data, 'RGBA')

def composite_images(background, foreground):
    """Optimized compositing using PIL's built-in alpha compositing"""
    if not background or not foreground:
        return foreground or background
        
    if background.size != foreground.size:
        background = background.resize(foreground.size, Image.NEAREST)
    
    # Use PIL's optimized alpha compositing instead of manual paste
    return Image.alpha_composite(background.convert('RGBA'), foreground.convert('RGBA'))

def create_diagonal_pattern(size, spacing=8):
    """Optimized diagonal pattern creation"""
    w, h = size
    pattern = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(pattern)
    
    # Pre-calculate line coordinates to reduce loop overhead
    lines = []
    for i in range(-h, w, spacing):
        lines.append([(i, 0), (i + h, h)])
    
    # Draw all lines at once
    for line in lines:
        draw.line(line, fill=(255, 255, 255, 128), width=1)
    
    return pattern

def create_selection_border(mask, thickness=2):
    """Optimized border creation using vectorized operations"""
    if not mask:
        return None
        
    try:
        from scipy import ndimage
        mask_array = np.array(mask) > 0
        
        # Vectorized dilation and border detection
        dilated = ndimage.binary_dilation(mask_array, iterations=thickness)
        border = dilated & (~mask_array)
        
        return Image.fromarray((border * 255).astype(np.uint8), "L")
        
    except ImportError:
        # Fallback method with some optimization
        mask_array = np.array(mask)
        h, w = mask_array.shape
        
        # Use convolution-like approach for neighbor checking
        border = np.zeros_like(mask_array, dtype=np.uint8)
        
        # Vectorized neighbor checking using array slicing
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                if dx == 0 and dy == 0:
                    continue
                    
                y1, y2 = max(0, -dy), min(h, h - dy)
                x1, x2 = max(0, -dx), min(w, w - dx)
                
                # Check if any neighbors are non-zero
                neighbor_mask = mask_array[max(0, dy):min(h, h + dy), max(0, dx):min(w, w + dx)] > 0
                current_zero = mask_array[y1:y2, x1:x2] == 0
                
                border[y1:y2, x1:x2] |= (neighbor_mask & current_zero) * 255
        
        return Image.fromarray(border, "L")

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
    """Optimized brush painting using vectorized operations"""
    if not displacement_map:
        return displacement_map
        
    disp_data = np.array(displacement_map)
    height, width = disp_data.shape[:2]
    radius = brush_size // 2
    
    direction_values = {
        "right": np.array([128 + strength, 128, 0, 255], dtype=np.uint8),
        "left": np.array([128 - strength, 128, 0, 255], dtype=np.uint8),
        "up": np.array([128, 128 - strength, 0, 255], dtype=np.uint8),
        "down": np.array([128, 128 + strength, 0, 255], dtype=np.uint8)
    }
    
    # Pre-calculate brush bounds
    x_min, x_max = max(0, x - radius), min(width, x + radius + 1)
    y_min, y_max = max(0, y - radius), min(height, y + radius + 1)
    
    if x_min >= x_max or y_min >= y_max:
        return Image.fromarray(disp_data, 'RGBA')
    
    # Create coordinate grids for the brush area
    yy, xx = np.mgrid[y_min:y_max, x_min:x_max]
    
    # Vectorized distance calculation
    distances = np.sqrt((xx - x)**2 + (yy - y)**2)
    brush_mask = distances <= radius
    
    if not np.any(brush_mask):
        return Image.fromarray(disp_data, 'RGBA')
    
    # Apply selection mask if provided
    if selection_mask:
        sel_array = np.array(selection_mask)
        selection_slice = sel_array[y_min:y_max, x_min:x_max]
        brush_mask = brush_mask & (selection_slice > 0)
    
    # Apply brush effect
    if drawing_mode == "erase":
        disp_data[y_min:y_max, x_min:x_max][brush_mask] = [128, 128, 0, 0]
    else:
        disp_data[y_min:y_max, x_min:x_max][brush_mask] = direction_values[direction]
    
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
    Optimized magic select using NumPy operations where possible
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
        img_array = np.array(img_rgb, dtype=np.int32)  # Use int32 to prevent overflow
        
        # Get seed color
        seed_color = img_array[y, x]
        
        # Create selection mask and visited array
        mask = np.zeros((h, w), dtype=np.uint8)
        visited = np.zeros((h, w), dtype=bool)
        
        # Pre-allocate queue with reasonable initial size
        queue = deque([(x, y)])
        visited[y, x] = True
        
        # Precompute neighbor offsets
        neighbors = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        
        while queue:
            cx, cy = queue.popleft()
            
            # Vectorized color difference calculation
            current_color = img_array[cy, cx]
            color_diff = np.sum(np.abs(current_color - seed_color))
            
            if color_diff <= tolerance:
                mask[cy, cx] = 255
                
                # Add unvisited neighbors to queue
                for dx, dy in neighbors:
                    nx, ny = cx + dx, cy + dy
                    
                    if (0 <= nx < w and 0 <= ny < h and not visited[ny, nx]):
                        visited[ny, nx] = True
                        queue.append((nx, ny))
        
        # Convert mask to PIL Image
        return Image.fromarray(mask, "L")
        
    except Exception as e:
        print(f"Magic Select Error: {str(e)}")
        return None

# Additional optimization utility functions
def batch_process_pixels(func, *args, batch_size=1000):
    """Utility function to process large pixel operations in batches"""
    # This can be used for future optimizations if needed
    pass

def get_memory_efficient_array(image, dtype=np.uint8):
    """Get memory-efficient array representation of image"""
    return np.asarray(image, dtype=dtype)
