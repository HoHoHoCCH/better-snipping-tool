import tkinter as tk
from PIL import ImageGrab, ImageTk
from io import BytesIO
import win32clipboard
import time
import threading
import os
import datetime
import keyboard
import yaml

# -- Configuration -- 

#Grab settings from settings.yml
try: #Improved error handling - wrapped open
    with open("settings.yml") as config_file:
        config = yaml.safe_load(config_file)
except Exception as e:
    print("[ERROR] Failed to load config:", e)
    config = {
        "SAVE_FOLDER": "screenshots",
        "DEFAULT_NAME": "screenshot",
        "FREEZE_MODE": False,
        "DEBUG_MODE": False,
        "HOTKEY": "ctrl+q"
    }


SAVE_DIRECTORY = config["SAVE_FOLDER"]
DEFAULT_FILENAME = config["DEFAULT_NAME"]
IS_FREEZE_MODE_ENABLED = config["FREEZE_MODE"]
IS_DEBUG_MODE = config["DEBUG_MODE"]
SNIP_HOTKEY = config["HOTKEY"]

# Application state
debug_counter = 0
is_snipping_active = False
current_snipper = None
is_cancelling = False

# Main application window
root = tk.Tk()
root.withdraw()
root.attributes("-topmost", True)



def log_debug(message): 
    """
    TODO: Save to logs.txt
    """
    global debug_counter
    if IS_DEBUG_MODE:
        print(f"{debug_counter} [DEBUG] {message}")
        debug_counter += 1

def create_save_dialog(screenshot):
    """
    Create and show the filename input prompt
    TODO: Include different file formats to save as.
    TODO: Add hotkeys to save, copy, and close.
    """

    
    dialog_result = {"filename": None}
    dialog = tk.Tk()
    dialog.overrideredirect(True)
    dialog.configure(bg="#F5F5F5")
    dialog.attributes("-topmost", True)

    
    container = tk.Frame(dialog, bg="#FFFFFF", padx=20, pady=20, bd=0)
    container.pack()

    
    tk.Label(container, text="Save Screenshot", bg="#FFFFFF", 
            font=("Segoe UI", 12, "bold")).pack(pady=(0, 10))
    
    filename_entry = tk.Entry(container, font=("Segoe UI", 11), bd=1, relief="solid",
                           highlightthickness=1, highlightcolor="#AAAAAA")
    filename_entry.insert(0, DEFAULT_FILENAME)
    filename_entry.pack(ipadx=50, ipady=4, pady=(0, 15))
    filename_entry.focus()

    
    def save_screenshot():
        """Saves user entered filename to be returned"""
        user_input = filename_entry.get().strip()
        if user_input:
            dialog_result["filename"] = user_input
            time.sleep(0.1)
            dialog.destroy()

    def copy_to_clipboard(): 
        """Copy screenshot to clipboard"""
        output = BytesIO()
        screenshot.convert("RGB").save(output, "BMP")
        data = output.getvalue()[14:]
        output.close()
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()
        win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
        win32clipboard.CloseClipboard()

    def close_dialog():
        """Close prompt"""
        dialog_result["filename"] = None
        time.sleep(0.1)
        dialog.destroy()

    
    def create_button(parent, text, command, bg, hover_bg, press_bg):
        btn = tk.Button(parent, text=text, command=command, bg=bg, fg="white",
                       font=("Segoe UI", 10, "bold"), padx=12, pady=8, bd=0,
                       activebackground=press_bg, relief="flat", cursor="hand2")
        btn.pack(fill="x")
        btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
        btn.bind("<Leave>", lambda e: btn.config(bg=bg))
        btn.bind("<ButtonPress-1>", lambda e: btn.config(bg=press_bg))
        btn.bind("<ButtonRelease-1>", lambda e: btn.config(bg=hover_bg))
        return btn

    create_button(container, "Save", save_screenshot, "#1976D2", "#1565C0", "#0D47A1")
    create_button(container, "Copy to Clipboard", copy_to_clipboard, "#696969", "#4c4c4c", "#2f2f2f")

    
    close_frame = tk.Frame(container, bg="#FFFFFF")
    close_frame.pack(fill="x", pady=(10, 0))
    close_btn = tk.Label(close_frame, text="Close", bg="#FFFFFF", fg="#666666",
                         font=("Segoe UI", 9), cursor="hand2", anchor="center")
    close_btn.pack(fill="x")
    close_btn.bind("<Button-1>", lambda e: close_dialog())
    close_btn.bind("<Enter>", lambda e: close_btn.config(fg="#AA0000", font=("Segoe UI", 9, "bold")))
    close_btn.bind("<Leave>", lambda e: close_btn.config(fg="#666666", font=("Segoe UI", 9)))

    
    dialog.update_idletasks()
    width, height = dialog.winfo_width(), dialog.winfo_height()
    x_pos = (dialog.winfo_screenwidth() - width) // 2
    y_pos = (dialog.winfo_screenheight() - height) // 2
    dialog.geometry(f"{width}x{height}+{x_pos}+{y_pos}")

    dialog.mainloop()
    return dialog_result["filename"]

def capture_region(x1, y1, x2, y2):
    """Capture the screen region and save with user-provided filename"""
    time.sleep(0.05)
    screenshot = ImageGrab.grab((x1, y1, x2, y2))
    filename = create_save_dialog(screenshot)
    
    if not filename:
        return
        
    os.makedirs(SAVE_DIRECTORY, exist_ok=True)
    

    stripped_filename = "".join(c for c in filename if c.isalnum() or c in (" ", "-", "_")).rstrip()
    timestamp = datetime.datetime.now().strftime("_%Y%m%d_%H%M%S")
    full_filename = f"{stripped_filename}{timestamp}.png"
    filepath = os.path.join(SAVE_DIRECTORY, full_filename)
    
    screenshot.save(filepath)
    log_debug(f"Saved screenshot to {filepath}")

class SnippingTool:

    def __init__(self, parent):
        self.IS_FREEZE_MODE_ENABLED = config["FREEZE_MODE"]
        self.parent = parent
        self.screenshot = ImageGrab.grab()
        self.background_image = ImageTk.PhotoImage(self.screenshot)
        
        self.setup_window()
        self.setup_ui()
        self.setup_selection_variables()
        self.setup_hotkeys()
        self.activate_interface()

    def setup_window(self):

        self.window = tk.Toplevel(self.parent)
        self.window.withdraw()
        self.window.attributes("-transparent", "grey")
        self.main_frame = tk.Frame(self.window, background="grey")
        self.main_frame.pack(fill=tk.BOTH, expand=tk.YES)

    def setup_ui(self):

        self.create_info_bar()
        self.create_freeze_button()
        
    def create_info_bar(self):

        self.info_bar_frame = tk.Frame(self.window, bg="", padx=20, pady=10)
        self.info_bar_frame.place(relx=0.5, y=-60, anchor="n")
        
        self.info_label = tk.Label(
            self.info_bar_frame,
            text="Select the area you want to capture",
            bg="#FFFFFF",
            fg="#333333",
            font=("Segoe UI", 12, "bold"),
            padx=15,
            pady=5,
            bd=0,
            relief="flat",
        )
        self.info_label.pack()
        self.info_label.configure(highlightthickness=1, highlightbackground="#DDDDDD")
        self.info_bar_frame.configure(bg="#FFFFFF")

    def create_freeze_button(self):

        self.freeze_button_frame = tk.Frame(self.info_bar_frame, bg="#FFFFFF")
        self.freeze_button_frame.pack(pady=(10, 0))
        
        self.freeze_button = tk.Label(
            self.freeze_button_frame,
            text="Freeze Mode [F]",
            bg="#2196F3" if self.IS_FREEZE_MODE_ENABLED else "#9E9E9E",
            fg="white",
            font=("Segoe UI", 10, "bold"),
            padx=14,
            pady=8,
            bd=0,
            relief="flat",
            cursor="hand2",
        )
        self.freeze_button.pack()
        self.freeze_button.configure(highlightthickness=1, highlightbackground="#1E88E5")
        

        self.freeze_button.bind("<Enter>", self.on_freeze_button_hover)
        self.freeze_button.bind("<Leave>", self.on_freeze_button_leave)
        self.freeze_button.bind("<ButtonPress-1>", self.on_freeze_button_press)
        self.freeze_button.bind("<ButtonRelease-1>", self.on_freeze_button_release)

    def on_freeze_button_hover(self, event):

        if self.IS_FREEZE_MODE_ENABLED:
            self.freeze_button.config(bg="#1E88E5")
        else:
            self.freeze_button.config(bg="#BDBDBD")
            
    def on_freeze_button_leave(self, event):

        if self.IS_FREEZE_MODE_ENABLED:
            self.freeze_button.config(bg="#2196F3")
        else:
            self.freeze_button.config(bg="#9E9E9E")
            
    def on_freeze_button_press(self, event):

        if self.IS_FREEZE_MODE_ENABLED:
            self.freeze_button.config(bg="#1565C0")
        else:
            self.freeze_button.config(bg="#757575")
            
    def on_freeze_button_release(self, event):
        
        self.IS_FREEZE_MODE_ENABLED = not self.IS_FREEZE_MODE_ENABLED
        config["FREEZE_MODE"] = self.IS_FREEZE_MODE_ENABLED
        
        with open("settings.yml", "w") as config_file:
            yaml.dump(config, config_file, default_flow_style=False)

        if self.IS_FREEZE_MODE_ENABLED:
            self.create_frozen_background()
            self.window.deiconify()
        elif hasattr(self, 'frozen_background_window'):
            self.frozen_background_window.destroy()
            
        self.freeze_button.config(bg="#2196F3" if self.IS_FREEZE_MODE_ENABLED else "#9E9E9E")

    def setup_selection_variables(self):
        
        self.start_x = None
        self.start_y = None
        self.current_x = None
        self.current_y = None
        self.selection_rect = None
        self.overlay_rect = None

    def setup_hotkeys(self):
        
        keyboard.add_hotkey("esc", self.cancel_snipping)

    def activate_interface(self):
        
        self.setup_canvas()
        self.configure_window()
        
        if self.IS_FREEZE_MODE_ENABLED:
            self.create_frozen_background()
            
        self.window.deiconify()
        self.animate_fade_in()
        self.animate_info_bar_slide()

    def setup_canvas(self):
        
        self.canvas = tk.Canvas(self.main_frame, cursor="cross", bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=tk.YES)
        

        self.canvas.bind("<ButtonPress-1>", self.start_selection)
        self.canvas.bind("<B1-Motion>", self.update_selection)
        self.canvas.bind("<ButtonRelease-1>", self.complete_selection)

    def configure_window(self):
        
        self.window.attributes("-fullscreen", True)
        self.window.lift()
        self.window.attributes("-topmost", True)

    def create_frozen_background(self):
        '''TODO: Ensure screenshot is fully loaded before deinconifying window.'''
        self.frozen_background_window = tk.Toplevel(self.window)
        self.frozen_background_window.withdraw()
        self.frozen_background_window.overrideredirect(True)
        
        bg_label = tk.Label(self.frozen_background_window, image=self.background_image)
        bg_label.pack(fill=tk.BOTH, expand=True)
        
        self.frozen_background_window.geometry(
            f"{self.screenshot.width}x{self.screenshot.height}+0+0"
        )
        self.frozen_background_window.deiconify()
        self.frozen_background_window.attributes("-topmost", True)
        self.frozen_background_window.lower(self.window)
        
        self.window.attributes("-topmost", True)
        self.window.deiconify()
        self.window.lift()

    def animate_fade_in(self):
        
        def fade(step=0, steps=30, final_alpha=0.75):
            if step <= steps:
                alpha = step / steps * final_alpha
                self.window.attributes("-alpha", alpha)
                self.window.after(10, fade, step + 1)
                
        fade()

    def animate_info_bar_slide(self):
       
        def slide(position=-60, target=10, step=2):
            if position <= target:
                self.info_bar_frame.place_configure(y=position)
                self.window.after(5, slide, position + step)
                
        slide()

    def start_selection(self, event):
        
        self.animate_info_bar_slide_up()
        
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)
        

        if self.selection_rect:
            self.canvas.delete(self.selection_rect)
        if self.overlay_rect:
            self.canvas.delete(self.overlay_rect)
            

        self.selection_rect = self.canvas.create_rectangle(
            self.start_x,
            self.start_y,
            self.start_x + 1,
            self.start_y + 1,
            outline="#FFFFFF",
            width=3,
            fill="grey",
        )

    def update_selection(self, event):
        
        self.current_x = self.canvas.canvasx(event.x)
        self.current_y = self.canvas.canvasy(event.y)
        
        if self.selection_rect:
            self.canvas.coords(
                self.selection_rect,
                self.start_x,
                self.start_y,
                self.current_x,
                self.current_y,
            )

    def complete_selection(self, event):
        
        self.current_x = self.canvas.canvasx(event.x)
        self.current_y = self.canvas.canvasy(event.y)
        

        x1 = min(self.start_x, self.current_x)
        y1 = min(self.start_y, self.current_y)
        x2 = max(self.start_x, self.current_x)
        y2 = max(self.start_y, self.current_y)
        

        if self.overlay_rect:
            self.canvas.delete(self.overlay_rect)
            
        self.overlay_rect = self.canvas.create_rectangle(
            x1, y1, x2, y2, fill="#FFFFFF", outline=""
        )
        self.canvas.update()
        

        time.sleep(0.1)
        threading.Thread(
            target=self.process_screenshot, 
            args=(x1, y1, x2, y2), 
            daemon=True
        ).start()

    def animate_info_bar_slide_up(self):
        
        def slide(position=10, target=-150, step=-4):
            if position >= target:
                self.info_bar_frame.place_configure(y=position)
                self.window.after(5, slide, position + step)
                
        slide()

    def cancel_snipping(self):
        
        global is_cancelling
        
        if is_cancelling:
            return
            
        if hasattr(self, 'frozen_background_window'):
            self.frozen_background_window.destroy()
            
        is_cancelling = True
        
        def fade_out(step=10):
            if step < 0:
                self.canvas.destroy()
                self.window.withdraw()
                return
                
            self.window.attributes("-alpha", (step / 10) * 0.4)
            self.window.after(10, fade_out, step - 1)
            
        if self.info_bar_frame.winfo_exists():
            self.animate_info_bar_slide_up()
            
        fade_out()
        is_cancelling = False
        global is_snipping_active
        is_snipping_active = False

    def process_screenshot(self, x1, y1, x2, y2):
        
        if hasattr(self, 'frozen_background_window'):
            self.frozen_background_window.destroy()
            
        def fade_out(step=10):
            if step < 0:
                self.canvas.destroy()
                self.window.withdraw()
                capture_region(x1, y1, x2, y2)
                return
                
            self.window.attributes("-alpha", (step / 10) * 0.4)
            self.window.after(10, fade_out, step - 1)
            
        fade_out()
        global is_snipping_active
        is_snipping_active = False

def start_snipping():
    
    global is_snipping_active, current_snipper
    
    if is_snipping_active:
        return

    log_debug("Starting snipping tool")
    is_snipping_active = True
    current_snipper = SnippingTool(root)

def setup_hotkeys():
    '''TODO: Add hotkeys for saving, copying and closing filename prompt.'''
    log_debug("Setting up hotkeys")
    
    keyboard.add_hotkey(SNIP_HOTKEY, start_snipping)
    keyboard.add_hotkey("esc", lambda: current_snipper.cancel_snipping() if current_snipper else None)
    keyboard.add_hotkey("f", lambda: current_snipper.on_freeze_button_release(None) 
                          if current_snipper and is_snipping_active else None)
    
    log_debug("Hotkeys configured")
    keyboard.wait()


keyboard_thread = threading.Thread(target=setup_hotkeys, daemon=True)
keyboard_thread.start()


root.mainloop()
