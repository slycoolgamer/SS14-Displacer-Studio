import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import math
from . import image_processing, selection_tools, ui

class SS14DisplacementTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.iconbitmap(os.path.join(os.getcwd(), 'appicon.ico'))
        self.root.title("SS14 Displacement Studio")
        self.root.geometry("1400x900")
        
        # Images
        self.displacement_image = None
        self.reference_image = None
        self.background_image = None
        
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
        ui.setup_menubar(self.root, self)
        
        # Main layout
        control_frame = ttk.Frame(self.root, width=320)
        control_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5, pady=5)
        control_frame.pack_propagate(False)
        
        canvas_frame = ttk.Frame(self.root)
        canvas_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        ui.setup_controls(control_frame, self)
        ui.setup_canvas(canvas_frame, self)
        
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
            self.temp_selection = selection_tools.create_rect_selection(
                self.selection_start, 
                pos,
                self.displacement_image.size
            )
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
            lasso_sel = selection_tools.create_lasso_selection(
                self.lasso_points,
                self.displacement_image.size
            )
            self.apply_selection(lasso_sel)
            self.lasso_points = []

        self.update_displays()

    def magic_select(self, x, y):
        if not self.displacement_image:
            return
            
        selection = selection_tools.magic_select(
            self.displacement_image, 
            x, 
            y, 
            self.magic_tolerance.get()
        )
        self.apply_selection(selection)
        
    def apply_selection(self, new_selection):
        if not new_selection:
            return
            
        self.selection_mask = selection_tools.apply_selection_op(
            self.selection_mask,
            new_selection,
            self.selection_op.get()
        )
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
            
        self.selection_mask = selection_tools.invert_selection(self.selection_mask)
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
            
        if self.selection_active and self.selection_mask:
            if self.selection_mask.getpixel((x, y)) == 0:
                return
                
        mode = self.drawing_mode.get()
        direction = self.displacement_direction.get()
        brush_size = self.brush_size.get()
        strength = self.paint_strength.get()
        
        radius = brush_size // 2
        
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
                    
                if self.selection_active and self.selection_mask and self.selection_mask.getpixel((px, py)) == 0:
                    continue
                    
                current = list(self.displacement_image.getpixel((px, py)))
                
                if mode == "erase":
                    current = [128, 128, 0, 0]
                else:
                    current[0] = max(0, min(255, current[0] + mod_r))
                    current[1] = max(0, min(255, current[1] + mod_g))
                    current[3] = 255
                
                self.displacement_image.putpixel((px, py), tuple(current))
                
    def flip_displacement(self):
        if not self.displacement_image:
            return
        self.save_state()
        
        img_array = np.array(self.displacement_image)
        img_array[:, :, 0], img_array[:, :, 1] = img_array[:, :, 1].copy(), img_array[:, :, 0].copy()
        self.displacement_image = Image.fromarray(img_array, 'RGBA')
        
        self.update_displays()
                
    def update_displays(self):
        self.update_displacement_display()
        self.update_preview()
        
    def update_displacement_display(self):
        if not self.displacement_image:
            self.disp_canvas.delete("all")
            return
            
        display_img = self.displacement_image.copy()
        
        if self.selection_active and self.selection_mask:
            overlay = Image.new("RGBA", display_img.size, (30, 50, 100, 128))
            mask_inv = Image.eval(self.selection_mask, lambda x: 255 - x)
            overlay.putalpha(mask_inv)
            display_img = Image.alpha_composite(display_img, overlay)
            
            border = image_processing.create_selection_border(self.selection_mask)
            if border:
                border_overlay = Image.new("RGBA", display_img.size, (255, 255, 255, 200))
                border_overlay.putalpha(border)
                display_img = Image.alpha_composite(display_img, border_overlay)
            
        if self.temp_selection:
            temp_overlay = Image.new("RGBA", display_img.size, (100, 150, 255, 80))
            temp_inv = Image.eval(self.temp_selection, lambda x: 255 - x)
            temp_overlay.putalpha(temp_inv)
            display_img = Image.alpha_composite(display_img, temp_overlay)
            
            temp_border = image_processing.create_selection_border(self.temp_selection)
            if temp_border:
                temp_border_overlay = Image.new("RGBA", display_img.size, (255, 255, 255, 255))
                temp_border_overlay.putalpha(temp_border)
                display_img = Image.alpha_composite(display_img, temp_border_overlay)
            
        ui.display_image_on_canvas(display_img, self.disp_canvas, self.zoom, 'disp_display')
        
    def update_preview(self):
        if not self.displacement_image:
            self.prev_canvas.delete("all")
            return
            
        if self.reference_image:
            displaced_ref = image_processing.apply_ss14_displacement(
                self.reference_image, 
                self.displacement_image
            )
            preview = image_processing.composite_images(
                self.background_image, 
                displaced_ref
            ) if self.background_image and displaced_ref else displaced_ref
        elif self.background_image:
            preview = image_processing.apply_ss14_displacement(
                self.background_image, 
                self.displacement_image
            )
        else:
            return
            
        if preview:
            ui.display_image_on_canvas(preview, self.prev_canvas, self.zoom, 'prev_display')
        
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
