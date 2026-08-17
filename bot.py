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
#   size         ขนาดปกที่ออก ถ้าไม่ใส่ = ใช้ขนาดจริงของไฟล์เทมเพลต (กันเทมเพลตสัดส่วนอื่นถูกบีบ)
#   fit_height   True = ย่อฟอนต์ถ้าข้อความสูงเกินกรอบ text_top..text_bottom (ใช้ตอนพื้นที่แคบ)

STYLE_2LINE = {                   # !ทำปก2 — ข่าวเกม พาดหัว 2 บรรทัด
    "template":     "template3.png",       # ไฟล์จริง 2500x3125 ย่อลงเป็น 1200x1500 ให้เท่าคำสั่งอื่น
    "template_fallback": "template.png",   # ถ้าไฟล์หาย จะใช้อันนี้แทนเพื่อไม่ให้บอทล่ม
    "size":         TARGET_SIZE,
    "image_fit":    "cover",
    "image_scale":  1.0,
    "image_shift":  (0, 0),
    "font_size":    104,          # 2 บรรทัดมีที่เหลือเยอะ ตัวใหญ่ได้เต็มที่
    "min_font":     52,
    "line_spacing": 28,
    "align":        "center",
    "start_x":      0,
    "anchor":       "center",     # จัดกลางกรอบ ไม่เหลือช่องว่างท้ายภาพ
    "fit_height":   True,         # โซนใต้แบดจ์แคบ ถ้าสูงเกินกรอบให้ย่อฟอนต์ลงด้วย
    "text_top":     1097,         # แบดจ์ใน template3 อยู่ที่ y 1031-1082 (ต่ำกว่า template.png 120px)
    "text_bottom":  1420,
    "side_margin":  60,
}

STYLE_3LINE = {                   # !ทำปก3 — ข่าวเกม พาดหัว 3 บรรทัด
    "template":     "template3.png",
    "template_fallback": "template.png",
    "size":         TARGET_SIZE,
    "image_fit":    "cover",
    "image_scale":  1.0,
    "image_shift":  (0, 0),
    "font_size":    92,           # เล็กกว่าแบบ 2 บรรทัด เพราะโซนใต้แบดจ์สูงแค่ 323px
    "min_font":     52,
    "line_spacing": 28,
    "align":        "center",
    "start_x":      0,
    "anchor":       "center",
    "fit_height":   True,
    "text_top":     1097,
    "text_bottom":  1420,
    "side_margin":  60,
}

STYLE_4LINE = {                   # !ทำปก4 — ข่าวเกม พาดหัว 4 บรรทัด (ของเดิม ไม่เปลี่ยน)
    "template":     "template.png",
    "size":         TARGET_SIZE,
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

STYLE_INSIGHT = {                 # !ทำปกInsight — บทความอินไซต์
    "template":     "template2.png",
    "size":         TARGET_SIZE,
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


def fit_font(draw, lines, base_size, min_size, max_width, spacing, max_height=None):
    """ย่อฟอนต์ลงทีละนิดจนกว่าข้อความจะไม่ล้นกรอบ
       max_height = None คือไม่สนความสูง (ใช้กับสไตล์ที่พื้นที่ด้านล่างเหลือเฟือ)"""
    size = base_size
    while size > min_size:
        font = ImageFont.truetype(FONT_FILE, size)
        if max(line_width(draw, parts, font) for parts in lines) <= max_width:
            if max_height is None:
                return font
            ink_top, ink_bottom = measure_ink(draw, lines, font, spacing)
            if (ink_bottom - ink_top) <= max_height:
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

    spacing    = style["line_spacing"]
    max_height = (style["text_bottom"] - style["text_top"]) if style.get("fit_height") else None

    font  = fit_font(draw, lines, style["font_size"], style["min_font"],
                     max_width, spacing, max_height)
    pitch = font.size + spacing

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
def open_template(style):
    """เปิดไฟล์เทมเพลต ถ้าไม่มีให้ถอยไปใช้ตัวสำรอง (บอทจะได้ไม่ล่มตอนยังไม่ได้วางไฟล์)"""
    name = style["template"]
    if not os.path.exists(name) and style.get("template_fallback"):
        print(f"ไม่พบ {name} — ใช้ {style['template_fallback']} แทนไปก่อน")
        name = style["template_fallback"]

    template = Image.open(name).convert("RGBA")

    # ไม่ระบุ size = ใช้ขนาดจริงของเทมเพลต เทมเพลตสัดส่วนอื่นจะได้ไม่ถูกบีบ
    size = style.get("size")
    if size and template.size != tuple(size):
        template = template.resize(tuple(size), Image.Resampling.LANCZOS)
    return template


def compose_image(user_image, style):
    template = open_template(style)
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
def count_lines(title):
    return len([l for l in title.split("\n") if l.strip()])


async def send_cover(ctx, title, style, filename, expect_lines=None):
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

    # พิมพ์มาไม่ตรงจำนวนบรรทัดของคำสั่ง ทำให้อยู่ดีแต่บอกคำสั่งที่เหมาะกว่าให้
    note = ""
    if expect_lines is not None:
        n = count_lines(title)
        if n != expect_lines and 2 <= n <= 4:
            note = f"(นี่ {n} บรรทัด ถ้าอยากได้ขนาดที่พอดีกว่านี้ลองใช้ `!ทำปก{n}` ครับ)"
        elif n > 4:
            note = f"(นี่ {n} บรรทัด เยอะกว่าที่ปกรองรับ ตัวหนังสือจะเล็กลงมากนะครับ)"

    await ctx.send(content=note or None, file=discord.File(buffer, filename))


# ------------------ Commands ------------------
@bot.command(name="ทำปก2")
async def make_cover_2(ctx, *, title: str):
    """ข่าวเกม — พาดหัว 2 บรรทัด"""
    await send_cover(ctx, title, STYLE_2LINE, "cover.jpg", expect_lines=2)


@bot.command(name="ทำปก3")
async def make_cover_3(ctx, *, title: str):
    """ข่าวเกม — พาดหัว 3 บรรทัด"""
    await send_cover(ctx, title, STYLE_3LINE, "cover.jpg", expect_lines=3)


@bot.command(name="ทำปก4", aliases=["ทำปก"])
async def make_cover_4(ctx, *, title: str):
    """ข่าวเกม — พาดหัว 4 บรรทัด (เดิมคือ !ทำปก)"""
    await send_cover(ctx, title, STYLE_4LINE, "cover.jpg", expect_lines=4)


@bot.command(name="ทำปกInsight", aliases=["ทำปกinsight", "ทำปกINSIGHT", "ทำปกอินไซต์"])
async def make_cover_insight(ctx, *, title: str):
    """บทความอินไซต์ (เดิมคือ !ทำปก2)"""
    await send_cover(ctx, title, STYLE_INSIGHT, "insight.jpg")


HELP_TEXT = (
    "ใส่ข้อความด้วยครับ เช่น\n"
    "`!ทำปก2 บรรทัด1` — ข่าวเกม 2 บรรทัด\n"
    "`!ทำปก3 บรรทัด1` — ข่าวเกม 3 บรรทัด\n"
    "`!ทำปก4 บรรทัด1` — ข่าวเกม 4 บรรทัด\n"
    "`!ทำปกInsight บรรทัด1` — บทความอินไซต์\n"
    "ครอบคำที่อยากให้เป็นสีเขียวด้วย [color]คำนั้น[/color] และอย่าลืมแนบรูปมาด้วย"
)


@bot.command(name="ทำปกช่วย", aliases=["ทำปกhelp", "ทำปก?"])
async def make_cover_help(ctx):
    """ดูวิธีใช้ทุกคำสั่ง"""
    await ctx.send(HELP_TEXT)


@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(HELP_TEXT)
    elif isinstance(error, commands.CommandNotFound):
        return
    else:
        print("Command Error:", error)


# ------------------ Run ------------------
if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get("TOKEN"))
