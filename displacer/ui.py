import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk

def setup_menubar(root, app):
    menubar = tk.Menu(root)
    root.config(menu=menubar)
    
    file_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="File", menu=file_menu)
    file_menu.add_command(label="New Map", command=app.create_new)
    file_menu.add_separator()
    file_menu.add_command(label="Load Reference Image", command=app.load_reference)
    file_menu.add_command(label="Load Background Image", command=app.load_background)
    file_menu.add_command(label="Load Displacement Map", command=app.load_displacement)
    file_menu.add_separator()
    file_menu.add_command(label="Save Displacement Map", command=app.save_displacement)
    file_menu.add_command(label="Save Preview", command=app.save_preview)
    
    edit_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="Edit", menu=edit_menu)
    edit_menu.add_command(label="Undo", command=app.undo, accelerator="Ctrl+Z")
    edit_menu.add_command(label="Clear All", command=app.clear)
    edit_menu.add_separator()
    edit_menu.add_command(label="Deselect", command=app.deselect_all)
    edit_menu.add_command(label="Select All", command=app.select_all)
    edit_menu.add_command(label="Invert Selection", command=app.invert_selection)
    edit_menu.add_separator()
    edit_menu.add_command(label="Invert Displacement", command=app.flip_displacement)

    view_menu = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label="View", menu=view_menu)
    view_menu.add_command(label="Sprite Grid...", command=app.open_sprite_grid_config)

    
    root.bind('<Control-z>', lambda e: app.undo())
    root.bind('<Control-a>', lambda e: app.select_all())
    root.bind('<Control-d>', lambda e: app.deselect_all())
    
def setup_controls(parent, app):
    # Make the parent container thinner
    parent.config(width=160)
    
    tool_frame = ttk.LabelFrame(parent, text="Tools")
    tool_frame.pack(fill=tk.X, pady=2, padx=2)
    
    # Updated tools list - Paint and Erase are now separate tools
    tools = [
        ("Paint", "paint"), 
        ("Erase", "erase"),
        ("Rect Select", "rect"), 
        ("Lasso Select", "lasso"), 
        ("Magic Select", "magic")
    ]
    for text, value in tools:
        ttk.Radiobutton(tool_frame, text=text, variable=app.current_tool, value=value, 
                       command=app.update_tool_ui).pack(anchor=tk.W, pady=1)
        
    # Store reference to selection frame for dynamic show/hide
    app.sel_frame = ttk.LabelFrame(parent, text="Selection")
    
    ops = [("Replace", "replace"), ("Add", "add"), ("Subtract", "subtract"), ("Intersect", "intersect")]
    for text, value in ops:
        ttk.Radiobutton(app.sel_frame, text=text, variable=app.selection_op, value=value).pack(anchor=tk.W, pady=1)
        
    ttk.Label(app.sel_frame, text="Magic Tolerance:").pack(pady=(5,0))
    ttk.Spinbox(app.sel_frame, from_=1, to=100, textvariable=app.magic_tolerance, width=8).pack(fill=tk.X, padx=2)
    
    # Renamed from "Paint Tools" to "Brush Settings" since it now applies to both paint and erase
    # Store reference to brush frame for dynamic show/hide
    app.brush_frame = ttk.LabelFrame(parent, text="Brush")
    
    ttk.Label(app.brush_frame, text="Direction:").pack(pady=(2,0))
    dir_frame = ttk.Frame(app.brush_frame)
    dir_frame.pack(pady=2)
    
    directions = [("↑", "up", 0, 1), ("←", "left", 0, 0), ("→", "right", 0, 2), ("↓", "down", 1, 1)]
    for text, value, row, col in directions:
        ttk.Radiobutton(dir_frame, text=text, variable=app.displacement_direction, value=value, width=2).grid(row=row, column=col, padx=1, pady=1)
        
    # Removed the Mode section since Paint/Erase are now separate tools
    
    ttk.Label(app.brush_frame, text="Brush Size:").pack(pady=(5,0))
    ttk.Spinbox(app.brush_frame, from_=1, to=50, textvariable=app.brush_size, width=8).pack(fill=tk.X, padx=2)
    
    ttk.Label(app.brush_frame, text="Paint Strength:").pack(pady=(5,0))
    ttk.Spinbox(app.brush_frame, from_=1, to=20, textvariable=app.paint_strength, width=8).pack(fill=tk.X, padx=2)
    
    # Initially show/hide frames based on default tool
    app.update_tool_ui()

def setup_canvas(parent, app):
    paned = ttk.PanedWindow(parent, orient=tk.HORIZONTAL)
    paned.pack(fill=tk.BOTH, expand=True)
    
    disp_frame = ttk.LabelFrame(paned, text="Displacement Editor")
    paned.add(disp_frame, weight=1)
    
    app.disp_canvas = tk.Canvas(disp_frame, bg='gray30')
    app.disp_canvas.pack(fill=tk.BOTH, expand=True)
    
    prev_frame = ttk.LabelFrame(paned, text="Preview Editor")
    paned.add(prev_frame, weight=1)
    
    app.prev_canvas = tk.Canvas(prev_frame, bg='gray20')
    app.prev_canvas.pack(fill=tk.BOTH, expand=True)
    
    bind_canvas_events(app)

def bind_canvas_events(app):
    app.disp_canvas.bind("<Button-1>", app.canvas_click)
    app.disp_canvas.bind("<B1-Motion>", app.canvas_drag)
    app.disp_canvas.bind("<ButtonRelease-1>", app.canvas_release)
    app.disp_canvas.bind("<MouseWheel>", app.zoom_canvas)

    app.prev_canvas.bind("<Button-1>", lambda e: app.canvas_click(e, from_preview=True))
    app.prev_canvas.bind("<B1-Motion>", lambda e: app.canvas_drag(e, from_preview=True))
    app.prev_canvas.bind("<ButtonRelease-1>", lambda e: app.canvas_release(e, from_preview=True))
    app.prev_canvas.bind("<MouseWheel>", app.zoom_canvas)
    app.disp_canvas.bind("<Motion>", app.canvas_hover)
    app.prev_canvas.bind("<Motion>", lambda e: app.canvas_hover(e, from_preview=True))
    app.prev_canvas.bind("<B1-Motion>", lambda e: [app.canvas_drag(e, from_preview=True), app.canvas_hover(e, from_preview=True)])



def display_image_on_canvas(image, canvas, zoom, attr_name):
    display_size = (int(image.width * zoom), int(image.height * zoom))
    display_img = image.resize(display_size, Image.NEAREST)
    
    photo = ImageTk.PhotoImage(display_img)
    setattr(canvas, attr_name, photo)
    
    canvas.delete("all")
    canvas_w = canvas.winfo_width() 
    canvas_h = canvas.winfo_height()
    x = (canvas_w - display_size[0]) // 2
    y = (canvas_h - display_size[1]) // 2
    
    canvas.create_image(x, y, anchor=tk.NW, image=photo)
