import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io, aiohttp, os, re
from flask import Flask
from threading import Thread

# ------------------ Web Server ------------------
app = Flask('')

@app.route('/')
def home():
    return "Bot is Live!"

def run():
    app.run(host='0.0.0.0', port=8000)

def keep_alive():
    Thread(target=run).start()

# ------------------ Discord Bot ------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# ------------------ Config กลาง ------------------
TARGET_SIZE     = (1200, 1500)
FONT_FILE       = "font.ttf"

MAIN_COLOR      = (255, 255, 255, 255)
HIGHLIGHT_COLOR = (188, 234, 47, 255)

# ค่าที่แต่ละคำสั่งใช้ — แก้ตัวเลขในนี้ได้เลย ไม่ต้องไปแก้โค้ดข้างล่าง
#
#   image_fit    "cover" = ครอบเต็มกรอบแล้วครอปกลาง / "top" = ย่อ-ขยายแล้วชิดขอบบน
#   image_scale  1.0 = พอดีกรอบ, 1.5 = ขยาย 150%
#   align        "center" = จัดกลาง / "left" = ชิดซ้ายที่ start_x
#   anchor       "top"    = บรรทัดแรกอยู่ที่ text_top เสมอ (ข้อความยาว)
#                "center" = จัดบล็อกข้อความให้อยู่กลางกรอบ text_top..text_bottom (ข้อความสั้น)
#   side_margin  ระยะขอบซ้าย-ขวาที่ห้ามตัวหนังสือล้ำออกไป (ถ้าล้ำ ฟอนต์จะย่อลงอัตโนมัติ)

STYLE_NEWS = {                    # !ทำปก   — ข่าวเกม ข้อความยาวถึง 4 บรรทัด
    "template":     "template.png",
    "image_fit":    "cover",
    "image_scale":  1.0,
    "image_shift":  (0, 0),
    "font_size":    89,
    "min_font":     52,
    "line_spacing": 24,
    "align":        "center",
    "start_x":      0,
    "anchor":       "top",
    "text_top":     960,
    "text_bottom":  1390,
    "side_margin":  60,
}

STYLE_NEWS_SHORT = {              # !ทำปก3 — ข่าวเกม ข้อความสั้น 2-3 บรรทัด
    "template":     "template.png",
    "image_fit":    "cover",
    "image_scale":  1.0,
    "image_shift":  (0, 0),
    "font_size":    104,          # ตัวใหญ่ขึ้นเพราะบรรทัดน้อยกว่า
    "min_font":     52,           # ถ้าบรรทัดยาวเกิน ฟอนต์จะย่อลงมาถึงขนาดนี้
    "line_spacing": 28,
    "align":        "center",
    "start_x":      0,
    "anchor":       "center",     # 👈 หัวใจของเวอร์ชันสั้น: ลอยอยู่กลางพื้นที่ดำ ไม่เหลือช่องว่างท้ายภาพ
    "text_top":     985,
    "text_bottom":  1390,
    "side_margin":  60,
}

STYLE_INSIGHT = {                 # !ทำปก2 — บทความอินไซต์
    "template":     "template2.png",
    "image_fit":    "top",
    "image_scale":  1.5,
    "image_shift":  (0, 0),
    "font_size":    77,
    "min_font":     46,
    "line_spacing": 20,
    "align":        "left",
    "start_x":      82,
    "anchor":       "top",
    "text_top":     1150,
    "text_bottom":  1440,
    "side_margin":  82,
}

# ------------------ Text Helpers ------------------
def parse_line(line):
    """แยก 1 บรรทัดเป็นชิ้น ๆ พร้อมสี — [color]...[/color] = สีไฮไลต์"""
    parts = []
    for raw in re.split(r'(\[color\].*?\[/color\])', line):
        if not raw:
            continue
        if raw.startswith('[color]') and raw.endswith('[/color]'):
            parts.append((raw[len('[color]'):-len('[/color]')], HIGHLIGHT_COLOR))
        else:
            parts.append((raw, MAIN_COLOR))
    return parts


def line_width(draw, parts, font):
    return sum(draw.textlength(text, font=font) for text, _ in parts)


def fit_font(draw, lines, base_size, min_size, max_width):
    """ย่อฟอนต์ลงทีละนิดจนกว่าบรรทัดที่ยาวที่สุดจะไม่ล้นกรอบ"""
    size = base_size
    while size > min_size:
        font = ImageFont.truetype(FONT_FILE, size)
        if max(line_width(draw, parts, font) for parts in lines) <= max_width:
            return font
        size -= 2
    return ImageFont.truetype(FONT_FILE, min_size)


def measure_ink(draw, lines, font, spacing):
    """ความสูงจริงของบล็อกข้อความ (วัดจากหมึกจริง ไม่ใช่กรอบ em) ไว้จัดกลางให้ตรงตา"""
    pitch = font.size + spacing
    top, bottom = None, None
    for i, parts in enumerate(lines):
        text = "".join(t for t, _ in parts) or " "
        bbox = draw.textbbox((0, i * pitch), text, font=font)
        top    = bbox[1] if top    is None else min(top, bbox[1])
        bottom = bbox[3] if bottom is None else max(bottom, bbox[3])
    return top, bottom


def draw_headline(image, headline, style):
    draw  = ImageDraw.Draw(image)
    width = image.width

    raw_lines = headline.split("\n")
    while raw_lines and not raw_lines[0].strip():     # ตัดบรรทัดว่างหัว-ท้ายทิ้ง
        raw_lines.pop(0)
    while raw_lines and not raw_lines[-1].strip():
        raw_lines.pop()
    if not raw_lines:
        return

    lines = [parse_line(line) for line in raw_lines]

    if style["align"] == "left":
        max_width = width - style["start_x"] - style["side_margin"]
    else:
        max_width = width - style["side_margin"] * 2

    font    = fit_font(draw, lines, style["font_size"], style["min_font"], max_width)
    spacing = style["line_spacing"]
    pitch   = font.size + spacing

    if style["anchor"] == "center":
        # จัดกลางจากหมึกจริง เพื่อให้ช่องว่างบน-ล่างเท่ากันจริง ๆ
        ink_top, ink_bottom = measure_ink(draw, lines, font, spacing)
        box_center = (style["text_top"] + style["text_bottom"]) / 2
        current_y  = box_center - (ink_top + ink_bottom) / 2
    else:
        current_y = style["text_top"]

    for parts in lines:
        if style["align"] == "left":
            current_x = style["start_x"]
        else:
            current_x = (width - line_width(draw, parts, font)) / 2

        for text, color in parts:
            draw.text((current_x, current_y), text, font=font, fill=color)
            current_x += draw.textlength(text, font=font)

        current_y += pitch


# ------------------ Image Helpers ------------------
def compose_image(user_image, style):
    template = Image.open(style["template"]).convert("RGBA")
    template = template.resize(TARGET_SIZE, Image.Resampling.LANCZOS)
    t_width, t_height = template.size

    img_ratio      = user_image.width / user_image.height
    template_ratio = t_width / t_height

    final_image = Image.new("RGBA", (t_width, t_height))

    if style["image_fit"] == "cover":
        # ครอบเต็มกรอบแล้วครอปกลาง
        if img_ratio > template_ratio:
            scale = t_height / user_image.height
        else:
            scale = t_width / user_image.width
        scale *= style["image_scale"]

        resized = user_image.resize(
            (max(1, int(user_image.width * scale)), max(1, int(user_image.height * scale))),
            Image.Resampling.LANCZOS
        )

        left = (resized.width  - t_width)  // 2
        top  = (resized.height - t_height) // 2
        final_image.paste(resized.crop((left, top, left + t_width, top + t_height)), (0, 0))
    else:
        # ย่อ-ขยายแล้ววางชิดขอบบน
        if img_ratio > template_ratio:
            scale = t_width / user_image.width
        else:
            scale = t_height / user_image.height
        scale *= style["image_scale"]

        resized = user_image.resize(
            (max(1, int(user_image.width * scale)), max(1, int(user_image.height * scale))),
            Image.Resampling.LANCZOS
        )

        shift_x, shift_y = style["image_shift"]
        final_image.paste(resized, (((t_width - resized.width) // 2) + shift_x, shift_y))

    # -------- Apply Template (Mask) --------
    final_image.paste(template, (0, 0), template)
    return final_image


def render_cover(image_bytes, headline, style):
    """รับรูปดิบ + ข้อความ คืนไฟล์ JPEG พร้อมส่ง"""
    user_image  = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
    final_image = compose_image(user_image, style)

    draw_headline(final_image, headline, style)

    background = Image.new("RGB", final_image.size, (20, 20, 20))
    background.paste(final_image, mask=final_image.split()[3])

    buffer = io.BytesIO()
    background.save(buffer, "JPEG", quality=95)
    buffer.seek(0)
    return buffer


# ------------------ Command Runner ------------------
async def send_cover(ctx, title, style, filename):
    if not ctx.message.attachments:
        await ctx.send("ลืมแนบรูปครับ!")
        return

    attachment = ctx.message.attachments[0]

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(attachment.url) as resp:
                resp.raise_for_status()
                image_bytes = await resp.read()
    except Exception as e:
        print("Download Error:", e)
        await ctx.send("โหลดรูปไม่สำเร็จครับ ลองแนบใหม่อีกที")
        return

    try:
        buffer = render_cover(image_bytes, title, style)
    except Exception as e:
        print("Render Error:", e)
        await ctx.send("ทำปกไม่สำเร็จครับ (ไฟล์รูปอาจไม่รองรับ)")
        return

    await ctx.send(file=discord.File(buffer, filename))


# ------------------ Commands ------------------
@bot.command(name="ทำปก")
async def make_cover(ctx, *, title: str):
    """ข่าวเกม — ข้อความยาวได้ถึง 4 บรรทัด"""
    await send_cover(ctx, title, STYLE_NEWS, "cover.jpg")


@bot.command(name="ทำปก3", aliases=["ทำปกสั้น"])
async def make_cover_short(ctx, *, title: str):
    """ข่าวเกม — ข้อความสั้น 2-3 บรรทัด ตัวใหญ่ขึ้นและจัดกลางพื้นที่ดำ"""
    await send_cover(ctx, title, STYLE_NEWS_SHORT, "cover.jpg")


@bot.command(name="ทำปก2")
async def make_cover_2(ctx, *, title: str):
    """บทความอินไซต์"""
    await send_cover(ctx, title, STYLE_INSIGHT, "cover2.jpg")


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "ใส่ข้อความด้วยครับ เช่น\n"
            "`!ทำปก บรรทัด1` (ข้อความยาว 4 บรรทัด)\n"
            "`!ทำปก3 บรรทัด1` (ข้อความสั้น 2-3 บรรทัด)\n"
            "`!ทำปก2 บรรทัด1` (บทความอินไซต์)\n"
            "ครอบคำที่อยากให้เป็นสีเขียวด้วย [color]คำนั้น[/color]"
        )
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        print("Command Error:", error)


# ------------------ Run ------------------
if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get("TOKEN"))
