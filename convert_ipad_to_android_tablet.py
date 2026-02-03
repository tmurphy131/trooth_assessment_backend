#!/usr/bin/env python3
"""
Convert iPad App Store Screenshots to Google Play Store Tablet format

Takes the existing iPad 12.9" screenshots and converts them to 
Android tablet dimensions for Google Play Store.

Google Play Store tablet requirements:
- 7" tablet: 1200x1920 (16:10 portrait)
- 10" tablet: 1600x2560 (16:10 portrait)

Requirements: pip install Pillow
"""

from PIL import Image
import os

# Configuration
INPUT_DIR = "site_files/appstore_final/ipad_12.9"
OUTPUT_DIR = "site_files/playstore_final"

# Google Play Store tablet sizes (portrait orientation)
TABLET_SIZES = {
    "tablet_7inch": (1200, 1920),    # 7" tablet (16:10)
    "tablet_10inch": (1600, 2560),   # 10" tablet (16:10)
}

# Mapping of iPad files to their proper names (preserving order)
FILE_MAPPINGS = [
    {
        "input": "01_appstore_apprenticeDashboard_final.png",
        "output": "01_your_spiritual_journey_final.png",
        "order": 1
    },
    {
        "input": "02_appstore_apprenticeAssessment_final.png",
        "output": "02_biblical_assessments_final.png",
        "order": 2
    },
    {
        "input": "03_appstore_apprenticeDashboardReport_final.png",
        "output": "03_ai-powered_insights_final.png",
        "order": 3
    },
    {
        "input": "04_appStore_spiritualGiftResults_final.png",
        "output": "04_spiritual_gifts_final.png",
        "order": 4
    },
    {
        "input": "05_appstore_apprenticeProgress_final.png",
        "output": "05_track_your_growth_final.png",
        "order": 5
    },
    {
        "input": "06_appstore_MentorDashboard_final.png",
        "output": "06_mentor_dashboard_final.png",
        "order": 6
    },
    {
        "input": "07_appstore_mentorReport_final.png",
        "output": "07_detailed_reports_final.png",
        "order": 7
    },
    {
        "input": "08_appstore_mentorResources_final.png",
        "output": "08_mentor_resources_final.png",
        "order": 8
    },
    {
        "input": "09_appstore_apprenticeResources_final.png",
        "output": "09_learning_resources_final.png",
        "order": 9
    },
]


def convert_image(input_path, output_path, target_size):
    """
    Convert an image to target size while maintaining aspect ratio.
    Adds letterboxing/pillarboxing if needed with black background.
    """
    img = Image.open(input_path)
    
    # Get original dimensions
    orig_width, orig_height = img.size
    target_width, target_height = target_size
    
    # Check if source is landscape and target is portrait
    # If so, we need to handle the rotation/fitting
    source_is_landscape = orig_width > orig_height
    target_is_portrait = target_height > target_width
    
    if source_is_landscape and target_is_portrait:
        # Source is landscape (iPad), target is portrait (Android tablet)
        # Option 1: Rotate the image
        # Option 2: Fit landscape into portrait with letterboxing
        # We'll go with fitting (letterboxing) to preserve the original design
        pass
    
    # Calculate scaling to fit within target while preserving aspect ratio
    scale_w = target_width / orig_width
    scale_h = target_height / orig_height
    scale = min(scale_w, scale_h)
    
    new_width = int(orig_width * scale)
    new_height = int(orig_height * scale)
    
    # Resize image
    resized = img.resize((new_width, new_height), Image.LANCZOS)
    
    # Create new image with black background
    result = Image.new('RGB', target_size, (26, 26, 26))  # Dark background matching brand
    
    # Center the resized image
    x_offset = (target_width - new_width) // 2
    y_offset = (target_height - new_height) // 2
    
    # Handle RGBA images
    if resized.mode == 'RGBA':
        result.paste(resized, (x_offset, y_offset), resized)
    else:
        result.paste(resized, (x_offset, y_offset))
    
    return result


def main():
    print("🎨 Converting iPad Screenshots to Google Play Store Tablet Format")
    print("=" * 70)
    print(f"Input directory: {INPUT_DIR}")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    print("Target sizes:")
    for name, (w, h) in TABLET_SIZES.items():
        print(f"  - {name}: {w}x{h}")
    print()
    
    # Create output directories
    for size_name in TABLET_SIZES.keys():
        os.makedirs(os.path.join(OUTPUT_DIR, size_name), exist_ok=True)
    
    for size_name, target_size in TABLET_SIZES.items():
        print(f"\n📐 Creating {size_name} ({target_size[0]}x{target_size[1]})...")
        print("-" * 50)
        
        created = 0
        for mapping in FILE_MAPPINGS:
            input_path = os.path.join(INPUT_DIR, mapping["input"])
            
            if not os.path.exists(input_path):
                print(f"  ⚠️  Skipping {mapping['input']} - file not found")
                continue
            
            output_path = os.path.join(OUTPUT_DIR, size_name, mapping["output"])
            
            print(f"  📱 Converting: {mapping['input']}")
            
            result = convert_image(input_path, output_path, target_size)
            result.save(output_path, 'PNG', quality=95)
            
            print(f"     ✅ Saved: {mapping['output']}")
            created += 1
        
        print(f"  → Created {created} screenshots for {size_name}")
    
    print()
    print("=" * 70)
    print("✨ All tablet screenshots converted!")
    print()
    print("📁 Output folders:")
    for size_name in TABLET_SIZES.keys():
        print(f"   {OUTPUT_DIR}/{size_name}/")
    print()
    print("💡 Note: iPad screenshots were landscape (2732x2048).")
    print("   They've been letterboxed to fit portrait tablet format.")
    print("   The dark background matches the app's brand colors.")


if __name__ == "__main__":
    main()
