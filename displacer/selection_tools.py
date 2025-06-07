import numpy as np
from PIL import Image, ImageDraw
from collections import deque

def create_rect_selection(start, end, image_size):
    w, h = image_size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    
    x1, y1 = start
    x2, y2 = end
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    
    draw.rectangle([x1, y1, x2, y2], fill=255)
    return mask

def create_lasso_selection(points, image_size):
    if len(points) < 3:
        return None
        
    w, h = image_size
    mask = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(mask)
    draw.polygon(points, fill=255)
    return mask

def magic_select(image, x, y, tolerance):
    try:
        w, h = image.size
        if x < 0 or x >= w or y < 0 or y >= h:
            return None
            
        img_rgb = image.convert('RGB')
        img_array = np.array(img_rgb)
        seed_color = img_array[y, x]
        
        mask = np.zeros((h, w), dtype=np.uint8)
        visited = np.zeros((h, w), dtype=bool)
        
        queue = deque([(x, y)])
        visited[y, x] = True
        
        while queue:
            cx, cy = queue.popleft()
            current_color = img_array[cy, cx]
            color_diff = np.sum(np.abs(current_color.astype(int) - seed_color.astype(int)))
            
            if color_diff <= tolerance:
                mask[cy, cx] = 255
                for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                    nx, ny = cx + dx, cy + dy
                    if (0 <= nx < w and 0 <= ny < h and not visited[ny, nx]):
                        visited[ny, nx] = True
                        queue.append((nx, ny))
                        
        return Image.fromarray(mask, "L")
    except Exception:
        return None

def apply_selection_op(current_mask, new_selection, op):
    if not new_selection:
        return current_mask
        
    if not current_mask or op == "replace":
        return new_selection
        
    old_array = np.array(current_mask)
    new_array = np.array(new_selection)
    
    if op == "add":
        result = np.maximum(old_array, new_array)
    elif op == "subtract":
        result = np.where(new_array > 0, 0, old_array)
    elif op == "intersect":
        result = np.minimum(old_array, new_array)
    else:
        result = old_array
        
    return Image.fromarray(result, "L")

def invert_selection(mask):
    if not mask:
        return None
        
    mask_array = np.array(mask)
    inverted = 255 - mask_array
    return Image.fromarray(inverted, "L")
