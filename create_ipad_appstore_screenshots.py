#!/usr/bin/env python3
"""
Generate iPad App Store Screenshots with text overlays for T[root]H Discipleship

Creates iPad 12.9" screenshots (2732x2048 landscape) with:
- Gradient background
- Device frame mockup effect
- Text headline above screenshot
- Subtext below headline

Requirements: pip install Pillow
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Configuration
SITE_FILES_DIR = "site_files"
OUTPUT_DIR = "site_files/appstore_final/ipad_12.9"

# iPad 12.9" landscape dimensions
CANVAS_WIDTH = 2732
CANVAS_HEIGHT = 2048

# Brand colors
BACKGROUND_TOP = (26, 26, 26)      # Dark black #1A1A1A
BACKGROUND_BOTTOM = (40, 40, 40)   # Slightly lighter
GOLD = (212, 175, 55)              # TroothGold #D4AF37
WHITE = (255, 255, 255)
GRAY = (180, 180, 180)

# iPad screenshot configurations - matching iPhone text exactly
SCREENSHOTS = [
    {
        "file": "ipad_apprenticeDashboard.png",
        "headline": "Your Spiritual Journey",
        "subtext": "Track progress & grow in faith",
        "order": 1
    },
    {
        "file": "ipad_apprenticeAssessment.png",
        "headline": "Biblical Assessments",
        "subtext": "Discover your spiritual strengths",
        "order": 2
    },
    {
        "file": "ipad_apprenticeDashboardReport.png",
        "headline": "AI-Powered Insights",
        "subtext": "Personalized feedback & guidance",
        "order": 3
    },
    {
        "file": "ipad_spiritualGiftResults.png",
        "headline": "Spiritual Gifts",
        "subtext": "Uncover how God has equipped you",
        "order": 4
    },
    {
        "file": "ipad_apprenticeProgress.png",
        "headline": "Track Your Growth",
        "subtext": "See your discipleship journey unfold",
        "order": 5
    },
    {
        "file": "ipad_mentorDashboard.png",
        "headline": "Mentor Dashboard",
        "subtext": "Guide apprentices with purpose",
        "order": 6
    },
    {
        "file": "ipad_mentorReport.png",
        "headline": "Detailed Reports",
        "subtext": "Insights to guide your mentoring",
        "order": 7
    },
    {
        "file": "ipad_mentorResources.png",
        "headline": "Mentor Resources",
        "subtext": "Tools for effective discipleship",
        "order": 8
    },
    {
        "file": "ipad_apprenticeResources.png",
        "headline": "Learning Resources",
        "subtext": "Grow deeper in your faith",
        "order": 9
    },
]


def create_gradient(width, height, top_color, bottom_color):
    """Create a vertical gradient image."""
    img = Image.new('RGB', (width, height), top_color)
    draw = ImageDraw.Draw(img)
    
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * ratio)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * ratio)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))
    
    return img


def add_rounded_corners(image, radius):
    """Add rounded corners to an image."""
    # Create a mask with rounded corners
    mask = Image.new('L', image.size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle([(0, 0), image.size], radius=radius, fill=255)
    
    # Apply the mask
    output = Image.new('RGBA', image.size, (0, 0, 0, 0))
    output.paste(image, (0, 0))
    output.putalpha(mask)
    
    return output


def load_font(size, bold=False):
    """Load a font, falling back to default if needed."""
    font_paths = [
        # macOS system fonts
        "/System/Library/Fonts/SFProDisplay-Bold.otf" if bold else "/System/Library/Fonts/SFProDisplay-Regular.otf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
    ]
    
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    
    # Fallback to default
    return ImageFont.load_default()


def create_screenshot(config):
    """Create a single iPad App Store screenshot with text overlay."""
    input_path = os.path.join(SITE_FILES_DIR, config["file"])
    
    if not os.path.exists(input_path):
        print(f"⚠️  Skipping {config['file']} - file not found")
        return None
    
    # Create gradient background
    canvas = create_gradient(CANVAS_WIDTH, CANVAS_HEIGHT, BACKGROUND_TOP, BACKGROUND_BOTTOM)
    draw = ImageDraw.Draw(canvas)
    
    # Font sizes for iPad (larger than iPhone)
    headline_size = 140
    subtext_size = 72
    
    # Load fonts
    headline_font = load_font(headline_size, bold=True)
    subtext_font = load_font(subtext_size, bold=False)
    
    # Calculate text positions (CENTERED)
    text_area_top = 120
    
    # Draw headline (gold color) - CENTERED
    headline = config["headline"]
    headline_bbox = draw.textbbox((0, 0), headline, font=headline_font)
    headline_width = headline_bbox[2] - headline_bbox[0]
    headline_x = (CANVAS_WIDTH - headline_width) // 2
    headline_y = text_area_top
    draw.text((headline_x, headline_y), headline, font=headline_font, fill=GOLD)
    
    # Draw subtext (gray color) - CENTERED
    subtext = config["subtext"]
    subtext_bbox = draw.textbbox((0, 0), subtext, font=subtext_font)
    subtext_width = subtext_bbox[2] - subtext_bbox[0]
    subtext_x = (CANVAS_WIDTH - subtext_width) // 2
    subtext_y = headline_y + 160
    draw.text((subtext_x, subtext_y), subtext, font=subtext_font, fill=GRAY)
    
    # Load and resize screenshot
    screenshot = Image.open(input_path)
    
    # Calculate screenshot size and position (much larger, centered)
    available_width = CANVAS_WIDTH - 300
    available_height = CANVAS_HEIGHT - subtext_y - 350
    
    # Scale screenshot to fit - MUCH LARGER (95% of available space)
    scale_w = available_width / screenshot.width
    scale_h = available_height / screenshot.height
    scale = min(scale_w, scale_h) * 0.95
    
    new_width = int(screenshot.width * scale)
    new_height = int(screenshot.height * scale)
    screenshot = screenshot.resize((new_width, new_height), Image.LANCZOS)
    
    # Add rounded corners to screenshot
    corner_radius = 60
    screenshot = screenshot.convert('RGBA')
    screenshot = add_rounded_corners(screenshot, corner_radius)
    
    # Add subtle shadow effect
    shadow_offset = 25
    shadow_color = (0, 0, 0, 100)
    shadow = Image.new('RGBA', (new_width + shadow_offset * 2, new_height + shadow_offset * 2), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        [(shadow_offset, shadow_offset), (new_width + shadow_offset, new_height + shadow_offset)],
        radius=corner_radius,
        fill=shadow_color
    )
    
    # Position screenshot (centered horizontally, below text with less gap)
    screenshot_x = (CANVAS_WIDTH - new_width) // 2
    screenshot_y = subtext_y + 150
    
    # Convert canvas to RGBA for compositing
    canvas = canvas.convert('RGBA')
    
    # Paste shadow
    canvas.paste(shadow, (screenshot_x - shadow_offset, screenshot_y - shadow_offset), shadow)
    
    # Paste screenshot
    canvas.paste(screenshot, (screenshot_x, screenshot_y), screenshot)
    
    # Convert back to RGB for saving
    final = Image.new('RGB', canvas.size, BACKGROUND_TOP)
    final.paste(canvas, (0, 0), canvas)
    
    return final


def main():
    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("🎨 Creating iPad App Store Screenshots for T[root]H Discipleship")
    print("=" * 60)
    print(f"Size: iPad 12.9\" ({CANVAS_WIDTH}x{CANVAS_HEIGHT} landscape)")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    
    created = 0
    for config in SCREENSHOTS:
        print(f"  📱 {config['headline']}")
        
        result = create_screenshot(config)
        
        if result:
            # Match iPhone naming convention
            output_filename = f"{config['order']:02d}_appstore_{config['file'].replace('ipad_', '').replace('.png', '_final.png')}"
            output_path = os.path.join(OUTPUT_DIR, output_filename)
            result.save(output_path, 'PNG', quality=95)
            print(f"     ✅ Saved: {output_filename}")
            created += 1
    
    print()
    print("=" * 60)
    print(f"✨ Created {created} iPad screenshots!")
    print()
    print(f"📁 Output folder: {OUTPUT_DIR}/")
    print()
    print("📝 Upload order for App Store:")
    for config in sorted(SCREENSHOTS, key=lambda x: x["order"]):
        print(f"   {config['order']}. {config['headline']}")


if __name__ == "__main__":
    main()
