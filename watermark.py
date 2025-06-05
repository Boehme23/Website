from PIL import Image, ImageDraw, ImageFont


def add_watermark(image_path, watermark_text, output_path):
    """
    Opens an image, adds a text watermark, and saves it to the output_path.
    Returns the output_path if successful, None otherwise.
    """
    try:
        img = Image.open(image_path).convert(
            "RGBA"
        )  # Open and ensure RGBA for transparency
        width, height = img.size
        # Make a new image for the watermark text that's the same size as the original
        txt_img = Image.new(
            "RGBA", (width, height), (255, 255, 255, 0)
        )  # Transparent layer
        draw = ImageDraw.Draw(txt_img)  # Draw on the transparent layer
        # Font
        try:
            font_path = "arial.ttf"
            font_size = int(height / 5)
            font = ImageFont.truetype(font_path, font_size)
        except IOError:
            print(f"Warning: Font '{font_path}' not found. Using default PIL font.")
            font_size = 70
            font = ImageFont.load_default()
        # Calculate text size and position
        try:
            bbox = font.getbbox(watermark_text)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
        except AttributeError:
            text_width, text_height = draw.textsize(watermark_text, font=font)
        padding = 10
        x = (width - text_width) / 2
        y = (height - text_height) / 2
        # Add text watermark
        draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 128))
        # Composite the text layer onto the original image
        img_with_watermark = Image.alpha_composite(img, txt_img)
        # If the output is JPEG, convert the RGBA image to RGB as JPEG doesn't support alpha
        if output_path.lower().endswith((".jpg", ".jpeg")):
            img_with_watermark = img_with_watermark.convert("RGB")
        img_with_watermark.save(output_path)
        return output_path
    except FileNotFoundError:
        print(f"Error: Input image file not found at {image_path}")
        return None
    except Exception as e:
        print(
            f"Error adding watermark: {e}"
        )  # This will now correctly show other errors if they occur
        return None
