"""
SS14 Displacement Map Creator
A GUI tool for creating displacement maps compatible with Space Station 14

Requirements: pip install tkinter pillow numpy
"""

from tkinter import Tk, ttk, filedialog, messagebox, Canvas, Frame
from PIL import Image, ImageTk, ImageDraw, ImageFilter
import tkinter as tk
import numpy as np
import math
from collections import deque
import os

class SS14DisplacementTool:
    def __init__(self):
        self.root = tk.Tk()
        #self.root.iconbitmap(os.path.join(os.getcwd(), 'appicon.ico'))
        self.root.title("SS14 Displacement Studio")
        self.root.geometry("1400x900")
        
        # Images
        self.displacement_image = None
        self.reference_image = None
        self.background_image = None
        self.preview_image = None
        
        # Selection system
        self.selection_mask = None
        self.selection_active = False
        self.current_tool = tk.StringVar(value="paint")
        self.selection_op = tk.StringVar(value="replace")
        
        # Selection drawing state
        self.selection_start = None
        self.temp_selection = None
        self.lasso_points = []
        
        # Settings
        self.brush_size = tk.IntVar(value=5)
        self.paint_strength = tk.IntVar(value=1)
        self.zoom = 2.0
        self.magic_tolerance = tk.IntVar(value=32)
        
        # Drawing state
        self.is_drawing = False
        self.drawing_mode = tk.StringVar(value="directional")
        self.displacement_direction = tk.StringVar(value="right")
        
        # Undo system
        self.undo_stack = []
        self.max_undo_steps = 10
        
        self.setup_ui()
        
    def setup_ui(self):
        self.setup_menubar()
        
        # Main layout
        control_frame = ttk.Frame(self.root, width=320)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        control_frame.pack_propagate(False)
        
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.setup_controls(control_frame)
        self.setup_canvas(canvas_frame)
        
    def setup_menubar(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Map", command=self.create_new)
        file_menu.add_separator()
        file_menu.add_command(label="Load Reference Image", command=self.load_reference)
        file_menu.add_command(label="Load Background Image", command=self.load_background)
        file_menu.add_command(label="Load Displacement Map", command=self.load_displacement)
        file_menu.add_separator()
        file_menu.add_command(label="Save Displacement Map", command=self.save_displacement)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Undo", command=self.undo, accelerator="Ctrl+Z")
        edit_menu.add_command(label="Clear All", command=self.clear)
        edit_menu.add_command(label="Flip Displacement", command=self.flip_displacement)
        
        select_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Select", menu=select_menu)
        select_menu.add_command(label="Select All", command=self.select_all)
        select_menu.add_command(label="Deselect", command=self.deselect_all)
        select_menu.add_command(label="Invert Selection", command=self.invert_selection)
        
        self.root.bind('<Control-z>', lambda e: self.undo())
        self.root.bind('<Control-a>', lambda e: self.select_all())
        self.root.bind('<Control-d>', lambda e: self.deselect_all())
        
    def setup_controls(self, parent):
        # Tool selection
        tool_frame = ttk.LabelFrame(parent, text="Tools")
        tool_frame.pack(fill=tk.X, pady=5)
        
        tools = [("Paint", "paint"), ("Rectangle Select", "rect"), ("Lasso Select", "lasso"), ("Magic Select", "magic")]
        for text, value in tools:
            ttk.Radiobutton(tool_frame, text=text, variable=self.current_tool, value=value).pack(anchor=tk.W)
            
        # Selection operations
        sel_frame = ttk.LabelFrame(parent, text="Selection Mode")
        sel_frame.pack(fill=tk.X, pady=5)
        
        ops = [("Replace", "replace"), ("Add", "add"), ("Subtract", "subtract"), ("Intersect", "intersect")]
        for text, value in ops:
            ttk.Radiobutton(sel_frame, text=text, variable=self.selection_op, value=value).pack(anchor=tk.W)
            
        ttk.Button(sel_frame, text="Invert", command=self.invert_selection).pack(fill=tk.X, pady=2)
        ttk.Button(sel_frame, text="Clear", command=self.deselect_all).pack(fill=tk.X)
        
        # Magic wand tolerance
        ttk.Label(sel_frame, text="Magic Tolerance:").pack(pady=(10,0))
        ttk.Scale(sel_frame, from_=1, to=100, variable=self.magic_tolerance, orient=tk.HORIZONTAL).pack(fill=tk.X)
        
        # Drawing tools
        draw_frame = ttk.LabelFrame(parent, text="Paint Tools")
        draw_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(draw_frame, text="Direction:").pack(pady=(5,0))
        dir_frame = ttk.Frame(draw_frame)
        dir_frame.pack(pady=5)
        
        directions = [("↑", "up", 0, 1), ("←", "left", 0, 0), ("→", "right", 0, 2), ("↓", "down", 1, 1)]
        for text, value, row, col in directions:
            ttk.Radiobutton(dir_frame, text=text, variable=self.displacement_direction, value=value, width=3).grid(row=row, column=col, padx=2, pady=2)
            
        ttk.Label(draw_frame, text="Mode:").pack(pady=(10,0))
        ttk.Radiobutton(draw_frame, text="Paint Direction", variable=self.drawing_mode, value="directional").pack(anchor=tk.W)
        ttk.Radiobutton(draw_frame, text="Erase", variable=self.drawing_mode, value="erase").pack(anchor=tk.W)
        
        ttk.Label(draw_frame, text="Brush Size:").pack(pady=(10,0))
        ttk.Scale(draw_frame, from_=1, to=50, variable=self.brush_size, orient=tk.HORIZONTAL).pack(fill=tk.X)
        
        ttk.Label(draw_frame, text="Paint Strength (pixels):").pack(pady=(10,0))
        ttk.Spinbox(draw_frame, from_=1, to=20, textvariable=self.paint_strength, width=10).pack(fill=tk.X)

    def setup_canvas(self, parent):
        paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)
        
        disp_frame = ttk.LabelFrame(paned, text="Displacement Editor")
        paned.add(disp_frame, weight=1)
        
        self.disp_canvas = tk.Canvas(disp_frame, bg='gray30')
        self.disp_canvas.pack(fill=tk.BOTH, expand=True)
        
        prev_frame = ttk.LabelFrame(paned, text="Live Preview")
        paned.add(prev_frame, weight=1)
        
        self.prev_canvas = tk.Canvas(prev_frame, bg='gray20')
        self.prev_canvas.pack(fill=tk.BOTH, expand=True)
        
        self.bind_canvas_events()
        
    def bind_canvas_events(self):
        self.disp_canvas.bind("<Button-1>", self.canvas_click)
        self.disp_canvas.bind("<B1-Motion>", self.canvas_drag)
        self.disp_canvas.bind("<ButtonRelease-1>", self.canvas_release)
        self.disp_canvas.bind("<MouseWheel>", self.zoom_canvas)

        self.prev_canvas.bind("<Button-1>", lambda e: self.canvas_click(e, from_preview=True))
        self.prev_canvas.bind("<B1-Motion>", lambda e: self.canvas_drag(e, from_preview=True))
        self.prev_canvas.bind("<ButtonRelease-1>", lambda e: self.canvas_release(e, from_preview=True))
        self.prev_canvas.bind("<MouseWheel>", self.zoom_canvas)

    def canvas_click(self, event, from_preview=False):
        if not self.displacement_image:
            return

        canvas = self.prev_canvas if from_preview else self.disp_canvas
        tool = self.current_tool.get()
        pos = self.canvas_to_image_coords(event, canvas)
        if not pos:
            return

        if tool == "paint":
            self.save_state()
            self.is_drawing = True
            self.paint_displacement(*pos)
        elif tool == "rect":
            self.selection_start = pos
            self.temp_selection = None
        elif tool == "lasso":
            self.lasso_points = [pos]
        elif tool == "magic":
            self.magic_select(*pos)

        self.update_displays()

    def canvas_drag(self, event, from_preview=False):
        if not self.displacement_image:
            return

        canvas = self.prev_canvas if from_preview else self.disp_canvas
        tool = self.current_tool.get()
        pos = self.canvas_to_image_coords(event, canvas)
        if not pos:
            return

        if tool == "paint" and self.is_drawing:
            self.paint_displacement(*pos)
        elif tool == "rect" and self.selection_start:
            self.temp_selection = self.create_rect_selection(self.selection_start, pos)
        elif tool == "lasso":
            self.lasso_points.append(pos)

        self.update_displays()

    def canvas_release(self, event, from_preview=False):
        tool = self.current_tool.get()

        if tool == "paint":
            self.is_drawing = False
        elif tool == "rect" and self.temp_selection:
            self.apply_selection(self.temp_selection)
            self.temp_selection = None
        elif tool == "lasso" and len(self.lasso_points) > 2:
            lasso_sel = self.create_lasso_selection()
            self.apply_selection(lasso_sel)
            self.lasso_points = []

        self.update_displays()

        
    def create_rect_selection(self, start, end):
        if not self.displacement_image:
            return None
            
        w, h = self.displacement_image.size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        
        x1, y1 = start
        x2, y2 = end
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        
        draw.rectangle([x1, y1, x2, y2], fill=255)
        return mask
        
    def create_lasso_selection(self):
        if not self.displacement_image or len(self.lasso_points) < 3:
            return None
            
        w, h = self.displacement_image.size
        mask = Image.new("L", (w, h), 0)
        draw = ImageDraw.Draw(mask)
        draw.polygon(self.lasso_points, fill=255)
        return mask
        
    def magic_select(self, x, y):
        """Fixed magic select using iterative flood fill to avoid stack overflow"""
        if not self.displacement_image:
            return
            
        try:
            w, h = self.displacement_image.size
            
            # Ensure coordinates are within bounds
            if x < 0 or x >= w or y < 0 or y >= h:
                return
                
            # Convert to RGB for comparison (ignore alpha for selection)
            img_rgb = self.displacement_image.convert('RGB')
            img_array = np.array(img_rgb)
            
            # Get seed color
            seed_color = img_array[y, x]
            tolerance = self.magic_tolerance.get()
            
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
            
            # Convert mask to PIL Image and apply selection
            selection = Image.fromarray(mask, "L")
            self.apply_selection(selection)
            
        except Exception as e:
            messagebox.showerror("Magic Select Error", f"Failed to perform magic select: {str(e)}")
        
    def apply_selection(self, new_selection):
        if not new_selection:
            return
            
        op = self.selection_op.get()
        
        if not self.selection_mask or op == "replace":
            self.selection_mask = new_selection
        else:
            old_array = np.array(self.selection_mask)
            new_array = np.array(new_selection)
            
            if op == "add":
                result = np.maximum(old_array, new_array)
            elif op == "subtract":
                result = np.where(new_array > 0, 0, old_array)
            elif op == "intersect":
                result = np.minimum(old_array, new_array)
            else:
                result = old_array
                
            self.selection_mask = Image.fromarray(result, "L")
            
        self.selection_active = True
        
    def select_all(self):
        if not self.displacement_image:
            return
        w, h = self.displacement_image.size
        self.selection_mask = Image.new("L", (w, h), 255)
        self.selection_active = True
        self.update_displays()
        
    def deselect_all(self):
        self.selection_mask = None
        self.selection_active = False
        self.update_displays()
        
    def invert_selection(self):
        if not self.displacement_image:
            return
            
        if not self.selection_mask:
            self.select_all()
            return
            
        mask_array = np.array(self.selection_mask)
        inverted = 255 - mask_array
        self.selection_mask = Image.fromarray(inverted, "L")
        self.update_displays()
        
    def save_state(self):
        if self.displacement_image:
            self.undo_stack.append(self.displacement_image.copy())
            if len(self.undo_stack) > self.max_undo_steps:
                self.undo_stack.pop(0)
                
    def undo(self):
        if self.undo_stack:
            self.displacement_image = self.undo_stack.pop()
            self.update_displays()
    
    def load_image(self, title, callback):
        filename = filedialog.askopenfilename(title=title, filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif")])
        if filename:
            try:
                image = Image.open(filename).convert("RGBA")
                callback(image)
                self.update_displays()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load image: {str(e)}")
    
    def load_reference(self):
        self.load_image("Load Reference Image", lambda img: setattr(self, 'reference_image', img))
        
    def load_background(self):
        self.load_image("Load Background Image", lambda img: setattr(self, 'background_image', img))
            
    def load_displacement(self):
        self.load_image("Load Displacement Map", lambda img: setattr(self, 'displacement_image', img))
            
    def save_displacement(self):
        if not self.displacement_image:
            messagebox.showwarning("Warning", "No displacement map to save")
            return
            
        filename = filedialog.asksaveasfilename(title="Save Displacement Map", defaultextension=".png", filetypes=[("PNG files", "*.png")])
        if filename:
            self.displacement_image.save(filename)
            messagebox.showinfo("Success", f"Saved to {filename}\n\nRemember to set sRGB: false in RSI meta.json!")
            
    def create_new(self):
        base_image = self.reference_image or self.background_image
        size = base_image.size if base_image else self.get_size_from_dialog()
            
        if size:
            self.displacement_image = Image.new("RGBA", size, (128, 128, 0, 255))
            self.update_displays()
            
    def get_size_from_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("New Displacement Map Size")
        dialog.geometry("300x150")
        dialog.transient(self.root)
        dialog.grab_set()
        
        width_var = tk.IntVar(value=256)
        height_var = tk.IntVar(value=256)
        result = [None]
        
        ttk.Label(dialog, text="Width:").grid(row=0, column=0, padx=10, pady=10, sticky='e')
        ttk.Entry(dialog, textvariable=width_var, width=10).grid(row=0, column=1, padx=10, pady=10)
        ttk.Label(dialog, text="Height:").grid(row=1, column=0, padx=10, pady=10, sticky='e')
        ttk.Entry(dialog, textvariable=height_var, width=10).grid(row=1, column=1, padx=10, pady=10)
        
        ttk.Button(dialog, text="Create", command=lambda: [result.__setitem__(0, (width_var.get(), height_var.get())), dialog.destroy()]).grid(row=2, column=0, columnspan=2, pady=20)
        dialog.wait_window()
        return result[0]
        
    def canvas_to_image_coords(self, event, canvas):
        canvas_x = canvas.canvasx(event.x)
        canvas_y = canvas.canvasy(event.y)
        
        if not self.displacement_image:
            return None
            
        img_w, img_h = self.displacement_image.size
        canvas_w = canvas.winfo_width() 
        canvas_h = canvas.winfo_height()
        
        display_w = int(img_w * self.zoom)
        display_h = int(img_h * self.zoom)
        offset_x = (canvas_w - display_w) // 2
        offset_y = (canvas_h - display_h) // 2
        
        img_x = int((canvas_x - offset_x) / self.zoom)
        img_y = int((canvas_y - offset_y) / self.zoom)
        
        return (img_x, img_y) if 0 <= img_x < img_w and 0 <= img_y < img_h else None
        
    def paint_displacement(self, x, y):
        if not self.displacement_image:
            return
            
        # Always allow painting - remove alpha check for transparent areas
        if self.selection_active and self.selection_mask:
            if self.selection_mask.getpixel((x, y)) == 0:
                return  # Outside selection
                
        mode = self.drawing_mode.get()
        direction = self.displacement_direction.get()
        brush_size = self.brush_size.get()
        strength = self.paint_strength.get()
        
        radius = brush_size // 2
        
        # Changed multiplier from 10 to 1 for finer control
        direction_modifiers = {
            "right": (strength, 0), "left": (-strength, 0),
            "up": (0, -strength), "down": (0, strength)
        }
        
        mod_r, mod_g = direction_modifiers.get(direction, (0, 0)) if mode == "directional" else (0, 0)
            
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                px, py = x + dx, y + dy
                
                if (px < 0 or py < 0 or px >= self.displacement_image.width or py >= self.displacement_image.height):
                    continue
                    
                if math.sqrt(dx*dx + dy*dy) > radius:
                    continue
                    
                # Remove alpha check here too - allow painting over transparent areas
                if self.selection_active and self.selection_mask and self.selection_mask.getpixel((px, py)) == 0:
                    continue
                    
                current = list(self.displacement_image.getpixel((px, py)))
                
                if mode == "erase":
                    current = [128, 128, 0, 0]
                else:
                    # Always paint with full alpha when painting directionally
                    current[0] = max(0, min(255, current[0] + mod_r))
                    current[1] = max(0, min(255, current[1] + mod_g))
                    current[3] = 255  # Ensure full opacity when painting
                
                self.displacement_image.putpixel((px, py), tuple(current))
                
    def flip_displacement(self):
        if not self.displacement_image:
            return
        self.save_state()
        
        # Flip R and G channels (X and Y displacement)
        img_array = np.array(self.displacement_image)
        img_array[:, :, 0], img_array[:, :, 1] = img_array[:, :, 1].copy(), img_array[:, :, 0].copy()
        self.displacement_image = Image.fromarray(img_array, 'RGBA')
        
        self.update_displays()
                
    def apply_ss14_displacement(self, reference, displacement):
        if not reference or not displacement:
            return None
            
        if displacement.size != reference.size:
            displacement = displacement.resize(reference.size, Image.NEAREST)
            
        width, height = reference.size
        disp_data = np.array(displacement)
        ref_data = np.array(reference)
        result_data = np.zeros((height, width, 4), dtype=np.uint8)
        
        # Changed displacement_size from 4.0 to 1.0 for one-to-one pixel movement
        displacement_size = 1.0
        
        for y in range(height):
            for x in range(width):
                disp_pixel = disp_data[y, x]
                
                if disp_pixel[3] == 0:
                    result_data[y, x] = [0, 0, 0, 0]
                    continue
                    
                offset_x = (disp_pixel[0] - 128) * displacement_size
                offset_y = (disp_pixel[1] - 128) * displacement_size
                
                sample_x = max(0, min(width - 1, int(round(x + offset_x))))
                sample_y = max(0, min(height - 1, int(round(y + offset_y))))
                
                result_data[y, x] = ref_data[sample_y, sample_x]
                            
        return Image.fromarray(result_data, 'RGBA')
        
    def composite_images(self, background, foreground):
        if not background or not foreground:
            return foreground or background
            
        if background.size != foreground.size:
            background = background.resize(foreground.size, Image.NEAREST)
            
        result = background.copy()
        result.paste(foreground, (0, 0), foreground)
        return result
        
    def update_displays(self):
        self.update_displacement_display()
        self.update_preview()
        
    def create_diagonal_pattern(self, size, spacing=8):
        """Create a diagonal line pattern for unselected areas"""
        w, h = size
        pattern = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(pattern)
        
        # Draw diagonal lines
        for i in range(-h, w, spacing):
            draw.line([(i, 0), (i + h, h)], fill=(255, 255, 255, 128), width=1)
        
        return pattern
    
    def create_selection_border(self, mask, thickness=2):
        """Create a white border around the selection"""
        if not mask:
            return None
            
        # Convert mask to numpy array
        mask_array = np.array(mask)
        
        # Create border by dilating the mask and subtracting original
        from scipy import ndimage
        try:
            dilated = ndimage.binary_dilation(mask_array > 0, iterations=thickness)
            border = dilated & (mask_array == 0)
            
            # Convert back to PIL image
            border_img = Image.fromarray((border * 255).astype(np.uint8), "L")
            return border_img
        except ImportError:
            # Fallback if scipy not available - simple edge detection
            w, h = mask.size
            border = Image.new("L", (w, h), 0)
            draw = ImageDraw.Draw(border)
            
            mask_array = np.array(mask)
            for y in range(1, h-1):
                for x in range(1, w-1):
                    if mask_array[y, x] == 0:  # Outside selection
                        # Check if any neighbor is inside selection
                        neighbors = [
                            mask_array[y-1, x], mask_array[y+1, x],
                            mask_array[y, x-1], mask_array[y, x+1]
                        ]
                        if any(n > 0 for n in neighbors):
                            draw.point((x, y), fill=255)
            
            return border

    def update_displacement_display(self):
        if not self.displacement_image:
            self.disp_canvas.delete("all")
            return
            
        # Start with base image
        display_img = self.displacement_image.copy()
        
        # Show active selection with semi-transparent overlay outside and white border
        if self.selection_active and self.selection_mask:
            # Create a semi-transparent overlay for unselected areas (dark blue with 50% opacity)
            overlay = Image.new("RGBA", display_img.size, (30, 50, 100, 128))
            
            # Apply overlay only to unselected areas
            mask_inv = Image.eval(self.selection_mask, lambda x: 255 - x)
            overlay.putalpha(mask_inv)
            display_img = Image.alpha_composite(display_img, overlay)
            
            # Add white border around selection
            border = self.create_selection_border(self.selection_mask)
            if border:
                border_overlay = Image.new("RGBA", display_img.size, (255, 255, 255, 200))
                border_overlay.putalpha(border)
                display_img = Image.alpha_composite(display_img, border_overlay)
            
        # Show temp selection with blue tint and border
        if self.temp_selection:
            # Blue tint for temp selection
            temp_overlay = Image.new("RGBA", display_img.size, (100, 150, 255, 80))
            temp_inv = Image.eval(self.temp_selection, lambda x: 255 - x)
            temp_overlay.putalpha(temp_inv)
            display_img = Image.alpha_composite(display_img, temp_overlay)
            
            # White border for temp selection
            temp_border = self.create_selection_border(self.temp_selection)
            if temp_border:
                temp_border_overlay = Image.new("RGBA", display_img.size, (255, 255, 255, 255))
                temp_border_overlay.putalpha(temp_border)
                display_img = Image.alpha_composite(display_img, temp_border_overlay)
            
        self.display_image_on_canvas(display_img, self.disp_canvas, 'disp_display')
        
    def update_preview(self):
        if not self.displacement_image:
            self.prev_canvas.delete("all")
            return
            
        if self.reference_image:
            displaced_ref = self.apply_ss14_displacement(self.reference_image, self.displacement_image)
            preview = self.composite_images(self.background_image, displaced_ref) if self.background_image and displaced_ref else displaced_ref
        elif self.background_image:
            preview = self.apply_ss14_displacement(self.background_image, self.displacement_image)
        else:
            return
            
        if preview:
            self.display_image_on_canvas(preview, self.prev_canvas, 'prev_display')
            
    def display_image_on_canvas(self, image, canvas, attr_name):
        display_size = (int(image.width * self.zoom), int(image.height * self.zoom))
        display_img = image.resize(display_size, Image.NEAREST)
        
        photo = ImageTk.PhotoImage(display_img)
        setattr(self, attr_name, photo)
        
        canvas.delete("all")
        canvas_w = canvas.winfo_width()
        canvas_h = canvas.winfo_height()
        x = (canvas_w - display_size[0]) // 2
        y = (canvas_h - display_size[1]) // 2
        
        canvas.create_image(x, y, anchor=tk.NW, image=photo)
        
    def zoom_canvas(self, event):
        self.zoom = max(0.5, min(8.0, self.zoom * (1.2 if event.delta > 0 else 1/1.2)))
        self.update_displays()
        
    def clear(self):
        if not self.displacement_image:
            return
        self.save_state()
        w, h = self.displacement_image.size
        self.displacement_image = Image.new("RGBA", (w, h), (128, 128, 0, 255))
        self.update_displays()
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = SS14DisplacementTool()
    app.run()
