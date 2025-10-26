import pygame
import sys
from pygame.locals import *
from PIL import Image
import tkinter as tk
from tkinter import filedialog

# 初始化pygame
pygame.init()

# 设置窗口
WIDTH, HEIGHT = 1200, 900
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption('Word ASCII Art Generator')

# --- Theme & Layout ---
HEADER_H = 64
SIDEBAR_W = 420
CONTROL_X = 20
CONTROL_W = SIDEBAR_W - 40

COLOR_BG = pygame.Color(18, 18, 20)
COLOR_HEADER = pygame.Color(28, 28, 34)
COLOR_ACCENT = pygame.Color(90, 140, 255)
COLOR_PANEL = pygame.Color(24, 24, 28)
COLOR_PANEL_BORDER = pygame.Color(55, 55, 65)
COLOR_TEXT = pygame.Color(235, 240, 250)
COLOR_TEXT_MUTED = pygame.Color(165, 175, 185)
COLOR_BUTTON = pygame.Color(45, 47, 55)
COLOR_BUTTON_HOVER = pygame.Color(65, 70, 80)
COLOR_BUTTON_ACTIVE = pygame.Color(75, 115, 200)
COLOR_TRACK = pygame.Color(60, 60, 70)
COLOR_TRACK_FILL = pygame.Color(90, 130, 220)
COLOR_KNOB = pygame.Color(140, 200, 255)
COLOR_STATUS = pygame.Color(255, 200, 140)

sidebar_rect = pygame.Rect(0, HEADER_H, SIDEBAR_W, HEIGHT - HEADER_H)
ascii_panel_rect = pygame.Rect(SIDEBAR_W + 20, HEADER_H + 20, WIDTH - SIDEBAR_W - 40, HEIGHT - HEADER_H - 80)

# --- Drawing helpers ---
def draw_shadowed_panel(surf, rect, bg, border, radius=10):
    shadow = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    pygame.draw.rect(shadow, (0, 0, 0, 60), shadow.get_rect(), border_radius=radius)
    surf.blit(shadow, (rect.x + 4, rect.y + 5))
    pygame.draw.rect(surf, bg, rect, border_radius=radius)
    pygame.draw.rect(surf, border, rect, width=1, border_radius=radius)

def draw_button(surf, rect, label_surface, hovered=False, active=False):
    color = COLOR_BUTTON
    if active:
        color = COLOR_BUTTON_ACTIVE
    elif hovered:
        color = COLOR_BUTTON_HOVER
    pygame.draw.rect(surf, color, rect, border_radius=8)
    surf.blit(label_surface, (rect.x + (rect.width - label_surface.get_width()) // 2,
                              rect.y + (rect.height - label_surface.get_height()) // 2))

def draw_slider(surf, rect, value, vmin, vmax):
    # Track
    pygame.draw.rect(surf, COLOR_TRACK, rect, border_radius=5)
    # Fill
    pct = 0 if vmax == vmin else (value - vmin) / (vmax - vmin)
    fill_w = max(0, min(rect.width, int(rect.width * pct)))
    if fill_w > 0:
        fill_rect = pygame.Rect(rect.x, rect.y, fill_w, rect.height)
        pygame.draw.rect(surf, COLOR_TRACK_FILL, fill_rect, border_radius=5)
    # Knob
    knob_x = int(rect.x + pct * rect.width)
    pygame.draw.circle(surf, COLOR_KNOB, (knob_x, rect.y + rect.height // 2), 8)

def draw_checkbox(surf, rect, checked):
    pygame.draw.rect(surf, COLOR_TEXT_MUTED, rect, width=2, border_radius=4)
    if checked:
        pygame.draw.line(surf, COLOR_TEXT, (rect.x + 4, rect.y + rect.height // 2), (rect.x + rect.width // 2, rect.y + rect.height - 5), 3)
        pygame.draw.line(surf, COLOR_TEXT, (rect.x + rect.width // 2, rect.y + rect.height - 5), (rect.x + rect.width - 4, rect.y + 5), 3)

def render_wrapped_text(surf, text, font_obj, color, x, y, max_width, line_spacing=2):
    """Render text wrapped by words so it fits within max_width.
    Returns the bottom y position after drawing (for optional chaining)."""
    words = text.split(' ')
    lines = []
    current = ''
    for w in words:
        test = (current + ' ' + w).strip()
        if font_obj.size(test)[0] <= max_width or not current:
            current = test
        else:
            lines.append(current)
            current = w
    if current:
        lines.append(current)
    yy = y
    for ln in lines:
        ts = font_obj.render(ln, True, color)
        surf.blit(ts, (x, yy))
        yy += ts.get_height() + line_spacing
    return yy

font = pygame.font.SysFont('consolas', 14)
title_font = pygame.font.SysFont('consolas', 28, bold=True)
instruction_font = pygame.font.SysFont('consolas', 16)

input_box = pygame.Rect(CONTROL_X, HEADER_H + 48, CONTROL_W, 36)

color_inactive = pygame.Color(70, 80, 95)
color_active = COLOR_ACCENT
color = color_inactive
active = False
text = ''
image_path = None

ascii_art = []
ascii_art_surfaces = []
ascii_canvas = None  # Surface with pre-rendered ASCII for scaling

ascii_font = pygame.font.SysFont('consolas', 8)
char_mode = 'word'  # 'word' or 'density'
ASCII_DENSE_SET = "@%#*+=-:. "
aspect_lock = False
image_aspect = 80/45


# ASCII art size controls
art_width = 80
art_height = 45
width_min, width_max = 10, 200
height_min, height_max = 5, 100
slider_length = CONTROL_W
# Sliders with clear vertical spacing
width_slider_rect = pygame.Rect(CONTROL_X, HEADER_H + 232, slider_length, 10)
height_slider_rect = pygame.Rect(CONTROL_X, width_slider_rect.y + 56, slider_length, 10)
width_dragging = False
height_dragging = False
button_rect = pygame.Rect(CONTROL_X, HEADER_H + 96, CONTROL_W, 36)
button_text = font.render('Import Image', True, COLOR_TEXT)

# Button for generating ASCII art (stacked under Import)
generate_button_rect = pygame.Rect(CONTROL_X, HEADER_H + 144, CONTROL_W, 36)
generate_button_text = font.render('Generate ASCII Art', True, COLOR_TEXT)

# Text density control (affects generation)
density_min, density_max = 0, 100
density_value = 60
density_slider_rect = pygame.Rect(CONTROL_X, height_slider_rect.y + 56, slider_length, 10)
density_dragging = False

# View adjustments: zoom and pan
zoom_min, zoom_max = 50, 300  # percent
zoom_value = 100
zoom_slider_rect = pygame.Rect(CONTROL_X, density_slider_rect.y + 56, slider_length, 10)
panx_min, panx_max = -500, 500
pany_min, pany_max = -500, 500
panx_value, pany_value = 0, 0
panx_slider_rect = pygame.Rect(CONTROL_X, zoom_slider_rect.y + 56, slider_length, 10)
pany_slider_rect = pygame.Rect(CONTROL_X, panx_slider_rect.y + 56, slider_length, 10)
zoom_dragging = False
panx_dragging = False
pany_dragging = False

# Char mode toggle buttons and aspect lock below pan sliders
word_mode_rect = pygame.Rect(CONTROL_X + 140, pany_slider_rect.y + 40, 100, 32)
word_mode_text = font.render('Word', True, COLOR_TEXT)
density_mode_rect = pygame.Rect(CONTROL_X + 244, pany_slider_rect.y + 40, 100, 32)
density_mode_text = font.render('Dense', True, COLOR_TEXT)

# Aspect ratio lock checkbox
aspect_checkbox_rect = pygame.Rect(CONTROL_X, pany_slider_rect.y + 42, 20, 20)
aspect_label_text = font.render('Lock Aspect', True, COLOR_TEXT_MUTED)

# Additional controls (computed row of three) below toggles
_triple_w = int((CONTROL_W - 24) / 3)
_row_y = aspect_checkbox_rect.y + 44
save_button_rect = pygame.Rect(CONTROL_X, _row_y, _triple_w, 32)
save_button_text = font.render('Save', True, COLOR_TEXT)
copy_button_rect = pygame.Rect(CONTROL_X + _triple_w + 12, _row_y, _triple_w, 32)
copy_button_text = font.render('Copy', True, COLOR_TEXT)
clear_button_rect = pygame.Rect(CONTROL_X + 2 * (_triple_w + 12), _row_y, _triple_w, 32)
clear_button_text = font.render('Clear', True, COLOR_TEXT)

# Open file dialog to select image
def select_image():
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(filetypes=[('Image Files', '*.png;*.jpg;*.jpeg;*.bmp')])
    # Update source image aspect if possible
    global image_aspect
    if file_path:
        try:
            with Image.open(file_path) as im:
                w, h = im.size
                if w > 0 and h > 0:
                    image_aspect = w / h
        except Exception:
            pass
    return file_path

# Generate ASCII art
def generate_ascii_art(image_path, word_text, art_width, art_height):
    img = Image.open(image_path).convert('L')
    img = img.resize((art_width, art_height))
    width, height = img.size
    pixels = img.getdata()
    # Choose character set/mapping based on mode
    if char_mode == 'density':
        # Map pixel intensity to dense ASCII set
        base = ASCII_DENSE_SET
        # Bias towards spaces when density is low by appending additional spaces
        extra_spaces = max(0, int((100 - density_value) / 5))
        chars = base[:-1] + (" " * (1 + extra_spaces))
        # Gamma to control perceived density (lower gamma -> darker -> more filled)
        gamma = 1.8 - (density_value / 100.0) * 1.3  # maps 0..100 -> ~1.8..0.5
        scale = max(1, 256 // max(1, len(chars)))
        def pick_char(px):
            # gamma correct
            p = int(255 * ((px / 255.0) ** gamma))
            idx = min(len(chars) - 1, p // scale)
            return chars[idx]
    else:
        chars = [c for c in word_text if c.isalpha()]
        if not chars:
            chars = ['.']
        idx_cycle = [*chars]
        idx = 0
        # Density affects threshold and gamma
        threshold = int(255 * (density_value / 100.0))
        gamma = 1.8 - (density_value / 100.0) * 1.3
        def pick_char(px):
            nonlocal idx
            ch = idx_cycle[idx % len(idx_cycle)]
            idx += 1
            p = int(255 * ((px / 255.0) ** gamma))
            return ch if p < threshold else ' '
    ascii_chars = []
    for i in range(height):
        line = ''
        for j in range(width):
            pixel = pixels[i * width + j]
            line += pick_char(pixel)
        ascii_chars.append(line)
    return ascii_chars

status_message = ""

# Dynamic ASCII font sizing based on width
def get_ascii_font(width):
    if width <= 40:
        return pygame.font.SysFont('consolas', 12)
    elif width <= 80:
        return pygame.font.SysFont('consolas', 10)
    elif width <= 120:
        return pygame.font.SysFont('consolas', 8)
    else:
        return pygame.font.SysFont('consolas', 7)

# Regenerate ASCII art and cached surfaces
def update_ascii_art():
    global ascii_art, ascii_art_surfaces, ascii_font, ascii_canvas
    if image_path and text and art_width >= 10 and art_height >= 5:
        ascii_font = get_ascii_font(art_width)
        ascii_art = generate_ascii_art(image_path, text, art_width, art_height)
        ascii_art_surfaces = [ascii_font.render(line, True, (255, 255, 255)) for line in ascii_art]
        # Build canvas for scaling
        line_h = ascii_art_surfaces[0].get_height() if ascii_art_surfaces else 16
        max_w = 0
        for s in ascii_art_surfaces:
            max_w = max(max_w, s.get_width())
        if max_w == 0:
            ascii_canvas = None
        else:
            canvas_h = line_h * len(ascii_art_surfaces)
            ascii_canvas = pygame.Surface((max_w, canvas_h), pygame.SRCALPHA)
            y = 0
            for s in ascii_art_surfaces:
                ascii_canvas.blit(s, (0, y))
                y += line_h
    else:
        ascii_art = []
        ascii_art_surfaces = []
        ascii_canvas = None

running = True

def redraw_screen():
    screen.fill(COLOR_BG)

    # Header bar
    pygame.draw.rect(screen, COLOR_HEADER, pygame.Rect(0, 0, WIDTH, HEADER_H))
    title_surface = title_font.render('Word ASCII Art Generator', True, COLOR_TEXT)
    screen.blit(title_surface, (20, (HEADER_H - title_surface.get_height()) // 2))

    # Sidebar and ASCII panel
    draw_shadowed_panel(screen, sidebar_rect, COLOR_PANEL, COLOR_PANEL_BORDER, radius=10)
    draw_shadowed_panel(screen, ascii_panel_rect, COLOR_PANEL, COLOR_PANEL_BORDER, radius=10)

    # Sidebar content
    mouse_pos = pygame.mouse.get_pos()
    # Labels
    lbl_controls = instruction_font.render('Controls', True, COLOR_TEXT_MUTED)
    screen.blit(lbl_controls, (CONTROL_X, HEADER_H + 12))

    # Input label and box
    lbl_word = font.render('Your Word', True, COLOR_TEXT_MUTED)
    screen.blit(lbl_word, (CONTROL_X, input_box.y - 18))
    pygame.draw.rect(screen, (35, 37, 45), input_box, border_radius=6)
    pygame.draw.rect(screen, color, input_box, width=2, border_radius=6)
    if text:
        txt_surface = font.render(text, True, COLOR_TEXT)
        clip_rect = input_box.inflate(-12, -8)
        screen.set_clip(clip_rect)
        screen.blit(txt_surface, (input_box.x + 8, input_box.y + (input_box.height - txt_surface.get_height()) // 2))
        screen.set_clip(None)
    else:
        placeholder = font.render('Type your word here…', True, COLOR_TEXT_MUTED)
        screen.blit(placeholder, (input_box.x + 8, input_box.y + (input_box.height - placeholder.get_height()) // 2))

    # Buttons
    draw_button(screen, button_rect, button_text, hovered=button_rect.collidepoint(mouse_pos))
    draw_button(screen, generate_button_rect, generate_button_text, hovered=generate_button_rect.collidepoint(mouse_pos))

    # Tip text: place it below the Save/Copy/Clear row to avoid overlapping other controls
    tip_text = "Tip: Use simple sketches and images with clear light/dark contrast."
    render_wrapped_text(
        screen,
        tip_text,
        font,
        COLOR_TEXT_MUTED,
        CONTROL_X,
        clear_button_rect.bottom + 10,
        CONTROL_W,
    )

    # Sliders
    lbl_w = font.render('Width: ' + str(art_width), True, COLOR_TEXT_MUTED)
    screen.blit(lbl_w, (CONTROL_X, width_slider_rect.y - 22))
    draw_slider(screen, width_slider_rect, art_width, width_min, width_max)

    lbl_h = font.render('Height: ' + str(art_height), True, COLOR_TEXT_MUTED)
    screen.blit(lbl_h, (CONTROL_X, height_slider_rect.y - 22))
    draw_slider(screen, height_slider_rect, art_height, height_min, height_max)

    # Zoom & Pan sliders
    lbl_density = font.render('Text Density: ' + str(density_value) + '%', True, COLOR_TEXT_MUTED)
    screen.blit(lbl_density, (CONTROL_X, density_slider_rect.y - 22))
    draw_slider(screen, density_slider_rect, density_value, density_min, density_max)
    lbl_zoom = font.render('Zoom: ' + str(zoom_value) + '%', True, COLOR_TEXT_MUTED)
    screen.blit(lbl_zoom, (CONTROL_X, zoom_slider_rect.y - 22))
    draw_slider(screen, zoom_slider_rect, zoom_value, zoom_min, zoom_max)
    lbl_panx = font.render('X Offset: ' + str(panx_value), True, COLOR_TEXT_MUTED)
    screen.blit(lbl_panx, (CONTROL_X, panx_slider_rect.y - 22))
    draw_slider(screen, panx_slider_rect, panx_value, panx_min, panx_max)
    lbl_pany = font.render('Y Offset: ' + str(pany_value), True, COLOR_TEXT_MUTED)
    screen.blit(lbl_pany, (CONTROL_X, pany_slider_rect.y - 22))
    draw_slider(screen, pany_slider_rect, pany_value, pany_min, pany_max)

    # Aspect lock and mode toggles
    draw_checkbox(screen, aspect_checkbox_rect, aspect_lock)
    screen.blit(aspect_label_text, (aspect_checkbox_rect.x + 28, aspect_checkbox_rect.y - 2))

    draw_button(screen, word_mode_rect, word_mode_text, hovered=word_mode_rect.collidepoint(mouse_pos), active=(char_mode == 'word'))
    draw_button(screen, density_mode_rect, density_mode_text, hovered=density_mode_rect.collidepoint(mouse_pos), active=(char_mode == 'density'))

    # Save/Copy/Clear
    draw_button(screen, save_button_rect, save_button_text, hovered=save_button_rect.collidepoint(mouse_pos))
    draw_button(screen, copy_button_rect, copy_button_text, hovered=copy_button_rect.collidepoint(mouse_pos))
    draw_button(screen, clear_button_rect, clear_button_text, hovered=clear_button_rect.collidepoint(mouse_pos))

    # ASCII panel content (scaled & panned)
    padding = 16
    if ascii_canvas:
        # Scale by zoom
        scale = max(zoom_min, min(zoom_max, zoom_value)) / 100.0
        target_w = max(1, int(ascii_canvas.get_width() * scale))
        target_h = max(1, int(ascii_canvas.get_height() * scale))
        scaled = pygame.transform.smoothscale(ascii_canvas, (target_w, target_h))
        # Clip to panel and blit with pan offsets
        view = pygame.Rect(ascii_panel_rect.x + padding, ascii_panel_rect.y + padding,
                           ascii_panel_rect.width - 2 * padding, ascii_panel_rect.height - 2 * padding)
        screen.set_clip(view)
        screen.blit(scaled, (view.x + panx_value, view.y + pany_value))
        screen.set_clip(None)

    # Status message at bottom-left
    if status_message:
        status_surface = instruction_font.render(status_message, True, COLOR_STATUS)
        screen.blit(status_surface, (SIDEBAR_W + 20, HEIGHT - 40))
    pygame.display.flip()

running = True
redraw_needed = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.MOUSEBUTTONDOWN:
            if input_box.collidepoint(event.pos):
                active = True
                color = color_active
                redraw_needed = True
            else:
                active = False
                color = color_inactive
                redraw_needed = True
            # Check if width slider knob is clicked
            width_knob_x = int(width_slider_rect.x + ((art_width - width_min) / (width_max - width_min)) * width_slider_rect.width)
            if pygame.Rect(width_knob_x-10, width_slider_rect.y-8, 20, width_slider_rect.height+16).collidepoint(event.pos):
                width_dragging = True
                redraw_needed = True
            # Check if height slider knob is clicked
            height_knob_x = int(height_slider_rect.x + ((art_height - height_min) / (height_max - height_min)) * height_slider_rect.width)
            if pygame.Rect(height_knob_x-10, height_slider_rect.y-8, 20, height_slider_rect.height+16).collidepoint(event.pos):
                height_dragging = True
                redraw_needed = True
            # Density knob click
            density_knob_x = int(density_slider_rect.x + ((density_value - density_min) / (density_max - density_min)) * density_slider_rect.width)
            if pygame.Rect(density_knob_x-10, density_slider_rect.y-8, 20, density_slider_rect.height+16).collidepoint(event.pos):
                density_dragging = True
                redraw_needed = True
            # Zoom knob click
            zoom_knob_x = int(zoom_slider_rect.x + ((zoom_value - zoom_min) / (zoom_max - zoom_min)) * zoom_slider_rect.width)
            if pygame.Rect(zoom_knob_x-10, zoom_slider_rect.y-8, 20, zoom_slider_rect.height+16).collidepoint(event.pos):
                zoom_dragging = True
                redraw_needed = True
            # Pan X knob click
            panx_knob_x = int(panx_slider_rect.x + ((panx_value - panx_min) / (panx_max - panx_min)) * panx_slider_rect.width)
            if pygame.Rect(panx_knob_x-10, panx_slider_rect.y-8, 20, panx_slider_rect.height+16).collidepoint(event.pos):
                panx_dragging = True
                redraw_needed = True
            # Pan Y knob click
            pany_knob_x = int(pany_slider_rect.x + ((pany_value - pany_min) / (pany_max - pany_min)) * pany_slider_rect.width)
            if pygame.Rect(pany_knob_x-10, pany_slider_rect.y-8, 20, pany_slider_rect.height+16).collidepoint(event.pos):
                pany_dragging = True
                redraw_needed = True
            # Check if aspect lock toggle clicked
            if aspect_checkbox_rect.collidepoint(event.pos):
                aspect_lock = not aspect_lock
                # Adjust counterpart dimension immediately to maintain aspect
                if aspect_lock and image_path:
                    # Fit height to width by default
                    art_height = max(height_min, min(height_max, int(round(art_width / image_aspect))))
                    update_ascii_art()
                redraw_needed = True

            # Check if import image button is clicked
            if button_rect.collidepoint(event.pos):
                image_path = select_image()
                if image_path:
                    status_message = "Image selected!"
                else:
                    status_message = "No image selected."
                redraw_needed = True
            # Check if generate button is clicked
            if generate_button_rect.collidepoint(event.pos):
                if not image_path:
                    status_message = "Please import an image first."
                elif not text:
                    status_message = "Please enter your word first."
                else:
                    if art_width < 10 or art_height < 5:
                        status_message = "Width/height too small."
                    else:
                        update_ascii_art()
                        status_message = "ASCII art generated!"
                redraw_needed = True
            # Save button
            if save_button_rect.collidepoint(event.pos):
                if ascii_art:
                    root = tk.Tk(); root.withdraw()
                    save_path = filedialog.asksaveasfilename(defaultextension='.txt', filetypes=[('Text Files','*.txt')])
                    if save_path:
                        try:
                            with open(save_path, 'w', encoding='utf-8') as f:
                                f.write('\n'.join(ascii_art))
                            status_message = 'Saved to ' + save_path
                        except Exception as e:
                            status_message = 'Save failed'
                    root.destroy()
                else:
                    status_message = 'No art to save'
                redraw_needed = True
            # Copy button
            if copy_button_rect.collidepoint(event.pos):
                if ascii_art:
                    root = tk.Tk(); root.withdraw()
                    try:
                        root.clipboard_clear()
                        root.clipboard_append('\n'.join(ascii_art))
                        root.update()
                        status_message = 'Copied to clipboard'
                    except Exception:
                        status_message = 'Copy failed'
                    root.destroy()
                else:
                    status_message = 'No art to copy'
                redraw_needed = True
            # Clear button
            if clear_button_rect.collidepoint(event.pos):
                ascii_art = []
                ascii_art_surfaces = []
                status_message = 'Cleared'
                redraw_needed = True
            # Mode toggles
            if word_mode_rect.collidepoint(event.pos):
                char_mode = 'word'
                update_ascii_art(); redraw_needed = True
            if density_mode_rect.collidepoint(event.pos):
                char_mode = 'density'
                update_ascii_art(); redraw_needed = True
        if event.type == pygame.MOUSEBUTTONUP:
            width_dragging = False
            height_dragging = False
            density_dragging = False
            zoom_dragging = False
            panx_dragging = False
            pany_dragging = False
        if event.type == pygame.MOUSEMOTION:
            if width_dragging:
                rel_x = event.pos[0] - width_slider_rect.x
                rel_x = max(0, min(width_slider_rect.width, rel_x))
                new_width = int(width_min + (rel_x / width_slider_rect.width) * (width_max - width_min))
                if aspect_lock and image_path:
                    art_height = max(height_min, min(height_max, int(round(new_width / image_aspect))))
                art_width = new_width
                update_ascii_art()
                redraw_needed = True
            if height_dragging:
                rel_x = event.pos[0] - height_slider_rect.x
                rel_x = max(0, min(height_slider_rect.width, rel_x))
                new_height = int(height_min + (rel_x / height_slider_rect.width) * (height_max - height_min))
                if aspect_lock and image_path:
                    art_width = max(width_min, min(width_max, int(round(new_height * image_aspect))))
                art_height = new_height
                update_ascii_art()
                redraw_needed = True
            if density_dragging:
                rel_x = event.pos[0] - density_slider_rect.x
                rel_x = max(0, min(density_slider_rect.width, rel_x))
                density_value = int(density_min + (rel_x / density_slider_rect.width) * (density_max - density_min))
                update_ascii_art()
                redraw_needed = True
            if zoom_dragging:
                rel_x = event.pos[0] - zoom_slider_rect.x
                rel_x = max(0, min(zoom_slider_rect.width, rel_x))
                zoom_value = int(zoom_min + (rel_x / zoom_slider_rect.width) * (zoom_max - zoom_min))
                redraw_needed = True
            if panx_dragging:
                rel_x = event.pos[0] - panx_slider_rect.x
                rel_x = max(0, min(panx_slider_rect.width, rel_x))
                panx_value = int(panx_min + (rel_x / panx_slider_rect.width) * (panx_max - panx_min))
                redraw_needed = True
            if pany_dragging:
                rel_x = event.pos[0] - pany_slider_rect.x
                rel_x = max(0, min(pany_slider_rect.width, rel_x))
                pany_value = int(pany_min + (rel_x / pany_slider_rect.width) * (pany_max - pany_min))
                redraw_needed = True
        if event.type == pygame.KEYDOWN:
            if active:
                if event.key == pygame.K_RETURN:
                    pass
                elif event.key == pygame.K_BACKSPACE:
                    text = text[:-1]
                    redraw_needed = True
                else:
                    text += event.unicode
                    redraw_needed = True
            if event.key == pygame.K_g:
                if not image_path:
                    status_message = "Please import an image first."
                elif not text:
                    status_message = "Please enter your word first."
                else:
                    if art_width < 10 or art_height < 5:
                        status_message = "Width/height too small."
                    else:
                        update_ascii_art()
                        status_message = "ASCII art generated!"
                redraw_needed = True
    if redraw_needed:
        redraw_screen()
        redraw_needed = False
    pygame.display.flip()
