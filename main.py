from flask import Flask, request, jsonify, send_file
from PIL import Image, ImageDraw, ImageFont
import io, os, re, requests

app = Flask('')

# ------------------ Config ------------------
FONT_SIZE    = 95
LINE_SPACING = 24
START_Y      = 960
TARGET_SIZE  = (1200, 1500)

MAIN_COLOR      = (255, 255, 255, 255)
HIGHLIGHT_COLOR = (188, 234, 47, 255)


# ------------------ Core ------------------
def generate_cover(image_url: str, headline: str) -> bytes:

    # -------- Load Image --------
    resp = requests.get(image_url, timeout=15)
    resp.raise_for_status()
    user_image = Image.open(io.BytesIO(resp.content)).convert("RGBA")

    # -------- Load Template --------
    template = Image.open("template.png").convert("RGBA")
    template = template.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    t_width, t_height = template.size

    # -------- Cover Crop --------
    img_ratio      = user_image.width / user_image.height
    template_ratio = t_width / t_height
    scale = t_height / user_image.height if img_ratio > template_ratio else t_width / user_image.width

    new_size = (int(user_image.width * scale), int(user_image.height * scale))
    resized  = user_image.resize(new_size, Image.Resampling.LANCZOS)

    left   = (resized.width  - t_width)  // 2
    top    = (resized.height - t_height) // 2
    cropped = resized.crop((left, top, left + t_width, top + t_height))

    final_image = Image.new("RGBA", (t_width, t_height))
    final_image.paste(cropped, (0, 0))

    # -------- Apply Template Mask --------
    final_image.paste(template, (0, 0), template)

    # -------- Draw Text --------
    draw = ImageDraw.Draw(final_image)
    font = ImageFont.truetype("font.ttf", FONT_SIZE)

    lines     = headline.split("\n")
    current_y = START_Y

    for line in lines:
        parts_raw = re.split(r'(\[color\].*?\[/color\])', line)

        parts = []
        for part in parts_raw:
            if not part:
                continue
            if part.startswith('[color]') and part.endswith('[/color]'):
                content = part.replace('[color]', '').replace('[/color]', '')
                parts.append((content, HIGHLIGHT_COLOR))
            else:
                parts.append((part, MAIN_COLOR))

        widths      = []
        total_width = 0
        for text, _ in parts:
            bbox = draw.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
            widths.append(w)
            total_width += w

        current_x = (t_width - total_width) // 2
        for i, (text, color) in enumerate(parts):
            draw.text(
                (current_x, current_y), text,
                font=font, fill=color,
                stroke_width=2, stroke_fill=(0, 0, 0)
            )
            current_x += widths[i]

        current_y += FONT_SIZE + LINE_SPACING

    # -------- Flatten to JPG --------
    background = Image.new("RGB", final_image.size, (20, 20, 20))
    background.paste(final_image, mask=final_image.split()[3])

    buf = io.BytesIO()
    background.save(buf, "JPEG", quality=95)
    return buf.getvalue()


# ------------------ Routes ------------------
@app.route('/')
def home():
    return "GameCraftsman Render API is Live!"


@app.route('/render', methods=['GET', 'POST'])
def render():
    """
    GET  /render?image_url=https://...&headline=บรรทัด1|บรรทัด2
    POST /render  { "image_url": "...", "headline": "บรรทัด1\nบรรทัด2" }

    หมายเหตุ: GET ใช้ | แทน \n สำหรับขึ้นบรรทัดใหม่
    Returns: JPEG image
    """
    if request.method == 'GET':
        image_url = request.args.get('image_url', '').strip()
        headline  = request.args.get('headline', '').strip().replace('|', '\n')
    else:
        body      = request.get_json(force=True, silent=True) or {}
        image_url = body.get('image_url', '').strip()
        headline  = body.get('headline', '').strip()

    if not image_url:
        return jsonify({"error": "image_url is required"}), 400
    if not headline:
        return jsonify({"error": "headline is required"}), 400

    try:
        jpg_bytes = generate_cover(image_url, headline)
    except requests.HTTPError as e:
        return jsonify({"error": f"ดาวน์โหลดรูปไม่ได้: {e}"}), 400
    except FileNotFoundError as e:
        return jsonify({"error": f"ไฟล์หายไป: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return send_file(
        io.BytesIO(jpg_bytes),
        mimetype='image/jpeg',
        as_attachment=True,
        download_name='cover.jpg'
    )


# ------------------ Run ------------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)
