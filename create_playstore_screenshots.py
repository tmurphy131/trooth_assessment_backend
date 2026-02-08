#!/usr/bin/env python3
"""
Generate Google Play Store Screenshots with text overlays for T[root]H Discipleship

Creates Android phone screenshots (1080x1920) with:
- Gradient background
- Device frame mockup effect
- Text headline above screenshot
- Subtext below headline

Requirements: pip install Pillow
"""

from PIL import Image, ImageDraw, ImageFont
import os

# Configuration
INPUT_DIR = "site_files/android_screenshots/phone_screens"
OUTPUT_DIR = "site_files/playstore_final"

# Device sizes - Google Play Store requirements
SIZES = {
    "phone": (1080, 1920),           # Standard Android phone
    "phone_7inch": (1080, 2160),     # Taller phone (19.5:9)
}

# Default dimensions (most common)
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920

# Brand colors (matching iOS version for parity)
BACKGROUND_TOP = (26, 26, 26)      # Dark black #1A1A1A
BACKGROUND_BOTTOM = (40, 40, 40)   # Slightly lighter
GOLD = (212, 175, 55)              # TroothGold #D4AF37
WHITE = (255, 255, 255)
GRAY = (180, 180, 180)

# Screenshot configurations with headlines (same as iOS for parity)
SCREENSHOTS = [
    {
        "file": "01_android_apprenticeDashboard.png",
        "headline": "Your Spiritual Journey",
        "subtext": "Track progress & grow in faith",
        "order": 1
    },
    {
        "file": "02_android_apprenticeAssessment.png",
        "headline": "Biblical Assessments",
        "subtext": "Discover your spiritual strengths",
        "order": 2
    },
    {
        "file": "03_android_apprenticeAssessmentReport.png",
        "headline": "AI-Powered Insights",
        "subtext": "Personalized feedback & guidance",
        "order": 3
    },
    {
        "file": "04_android_spiritualGiftResults.png",
        "headline": "Spiritual Gifts",
        "subtext": "Uncover how God has equipped you",
        "order": 4
    },
    {
        "file": "05_android_apprenticeProgress.png",
        "headline": "Track Your Growth",
        "subtext": "See your discipleship journey unfold",
        "order": 5
    },
    {
        "file": "06_android_MentorDashboard.png",
        "headline": "Mentor Dashboard",
        "subtext": "Guide apprentices with purpose",
        "order": 6
    },
    {
        "file": "07_android_mentorReport.png",
        "headline": "Detailed Reports",
        "subtext": "Insights to guide your mentoring",
        "order": 7
    },
    {
        "file": "08_android_mentorResources.png",
        "headline": "Mentor Resources",
        "subtext": "Tools for effective discipleship",
        "order": 8
    },
    {
        "file": "09_android_apprenticeResources.png",
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
        # Linux fonts (for CI/CD)
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    
    # Fallback to default
    return ImageFont.load_default()


def create_screenshot(config, canvas_width, canvas_height):
    """Create a single Play Store screenshot with text overlay."""
    input_path = os.path.join(INPUT_DIR, config["file"])
    
    if not os.path.exists(input_path):
        print(f"⚠️  Skipping {config['file']} - file not found")
        return None
    
    # Create gradient background
    canvas = create_gradient(canvas_width, canvas_height, BACKGROUND_TOP, BACKGROUND_BOTTOM)
    draw = ImageDraw.Draw(canvas)
    
    # Scale fonts based on canvas width (base is 1080 for standard phone)
    font_scale = canvas_width / 1080
    headline_size = int(84 * font_scale)
    subtext_size = int(48 * font_scale)
    
    # Load fonts
    headline_font = load_font(headline_size, bold=True)
    subtext_font = load_font(subtext_size, bold=False)
    
    # Calculate text positions (top portion of canvas)
    text_area_top = int(140 * font_scale)
    
    # Draw headline (gold color)
    headline = config["headline"]
    headline_bbox = draw.textbbox((0, 0), headline, font=headline_font)
    headline_width = headline_bbox[2] - headline_bbox[0]
    headline_x = (canvas_width - headline_width) // 2
    headline_y = text_area_top
    draw.text((headline_x, headline_y), headline, font=headline_font, fill=GOLD)
    
    # Draw subtext (gray color)
    subtext = config["subtext"]
    subtext_bbox = draw.textbbox((0, 0), subtext, font=subtext_font)
    subtext_width = subtext_bbox[2] - subtext_bbox[0]
    subtext_x = (canvas_width - subtext_width) // 2
    subtext_y = headline_y + int(105 * font_scale)
    draw.text((subtext_x, subtext_y), subtext, font=subtext_font, fill=GRAY)
    
    # Load and resize screenshot
    screenshot = Image.open(input_path)
    
    # Calculate screenshot size and position
    # Leave space for text at top, some padding at bottom
    available_height = canvas_height - subtext_y - int(160 * font_scale)
    screenshot_max_width = canvas_width - int(80 * font_scale)
    
    # Scale screenshot to fit
    scale_w = screenshot_max_width / screenshot.width
    scale_h = available_height / screenshot.height
    scale = min(scale_w, scale_h)
    
    new_width = int(screenshot.width * scale)
    new_height = int(screenshot.height * scale)
    screenshot = screenshot.resize((new_width, new_height), Image.LANCZOS)
    
    # Add rounded corners to screenshot
    corner_radius = int(36 * font_scale)
    screenshot = screenshot.convert('RGBA')
    screenshot = add_rounded_corners(screenshot, corner_radius)
    
    # Add subtle shadow effect
    shadow_offset = int(12 * font_scale)
    shadow_color = (0, 0, 0, 80)
    shadow = Image.new('RGBA', (new_width + shadow_offset * 2, new_height + shadow_offset * 2), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle(
        [(shadow_offset, shadow_offset), (new_width + shadow_offset, new_height + shadow_offset)],
        radius=corner_radius,
        fill=shadow_color
    )
    
    # Position screenshot
    screenshot_x = (canvas_width - new_width) // 2
    screenshot_y = subtext_y + int(120 * font_scale)
    
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
    # Create output directories
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    for size_name in SIZES.keys():
        os.makedirs(os.path.join(OUTPUT_DIR, size_name), exist_ok=True)
    
    print("🎨 Creating Google Play Store Screenshots for T[root]H Discipleship")
    print("=" * 65)
    print(f"Input directory: {INPUT_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    print(f"Generating sizes:")
    for name, (w, h) in SIZES.items():
        print(f"  - {name}: {w}x{h}")
    print()
    
    for size_name, (width, height) in SIZES.items():
        print(f"\n📐 Creating {size_name} ({width}x{height})...")
        print("-" * 45)
        
        created = 0
        for config in SCREENSHOTS:
            print(f"  📱 {config['headline']}")
            
            result = create_screenshot(config, width, height)
            
            if result:
                output_filename = f"{config['order']:02d}_{config['headline'].replace(' ', '_').lower()}_final.png"
                output_path = os.path.join(OUTPUT_DIR, size_name, output_filename)
                result.save(output_path, 'PNG', quality=95)
                print(f"     ✅ Saved: {output_filename}")
                created += 1
        
        print(f"  → Created {created} screenshots for {size_name}")
    
    print()
    print("=" * 65)
    print("✨ All Google Play Store screenshots created!")
    print()
    print("📁 Output folders:")
    for size_name, (w, h) in SIZES.items():
        print(f"   {OUTPUT_DIR}/{size_name}/")
    print()
    print("📝 Upload order for Google Play Store:")
    for config in sorted(SCREENSHOTS, key=lambda x: x["order"]):
        print(f"   {config['order']}. {config['headline']}")
    print()
    print("💡 Google Play Store tips:")
    print("   - Upload 2-8 screenshots per device type")
    print("   - First 3 screenshots are most visible")
    print("   - Use 'phone' folder for standard listings")


if __name__ == "__main__":
    main()
