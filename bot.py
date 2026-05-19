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

# ------------------ Command ------------------
@bot.command(name="ทำปก")
async def make_cover(ctx, *, title: str):

    # -------- Config --------
    FONT_SIZE = 95
    LINE_SPACING = 24
    START_Y = 960

    MAIN_COLOR = (255, 255, 255, 255)
    HIGHLIGHT_COLOR = (188, 234, 47, 255)

    TARGET_SIZE = (1200, 1500)  # 👈 บังคับสัดส่วนตรงนี้

    # -----------------------

    if not ctx.message.attachments:
        await ctx.send("ลืมแนบรูปครับ!")
        return

    attachment = ctx.message.attachments[0]

    # -------- Load Image --------
    async with aiohttp.ClientSession() as session:
        async with session.get(attachment.url) as resp:
            data = io.BytesIO(await resp.read())
            user_image = Image.open(data).convert("RGBA")

    # -------- Load Template --------
    template = Image.open("template.png").convert("RGBA")
    template = template.resize(TARGET_SIZE, Image.Resampling.LANCZOS)

    t_width, t_height = template.size

    # -------- Cover Crop --------
    img_ratio = user_image.width / user_image.height
    template_ratio = t_width / t_height

    if img_ratio > template_ratio:
        scale = t_height / user_image.height
    else:
        scale = t_width / user_image.width

    new_size = (
        int(user_image.width * scale),
        int(user_image.height * scale)
    )

    resized = user_image.resize(new_size, Image.Resampling.LANCZOS)

    left = (resized.width - t_width) // 2
    top = (resized.height - t_height) // 2
    right = left + t_width
    bottom = top + t_height

    cropped = resized.crop((left, top, right, bottom))

    final_image = Image.new("RGBA", (t_width, t_height))
    final_image.paste(cropped, (0, 0))

    # -------- Apply Template (Mask) --------
    final_image.paste(template, (0, 0), template)

    # -------- Draw Text --------
    draw = ImageDraw.Draw(final_image)

    try:
        font = ImageFont.truetype("font.ttf", FONT_SIZE)

        lines = title.split("\n")
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

            total_width = 0
            widths = []

            for text, _ in parts:
                bbox = draw.textbbox((0, 0), text, font=font)
                w = bbox[2] - bbox[0]
                widths.append(w)
                total_width += w

            start_x = (t_width - total_width) // 2
            current_x = start_x

            for i, (text, color) in enumerate(parts):
                draw.text(
                    (current_x, current_y),
                    text,
                    font=font,
                    fill=color,
                    stroke_width=0,
                    stroke_fill=(0, 0, 0)
                )
                current_x += widths[i]

            current_y += FONT_SIZE + LINE_SPACING

    except Exception as e:
        print("Text Error:", e)

    # -------- 🔥 FIX: Convert to JPG --------
    background = Image.new("RGB", final_image.size, (20, 20, 20))  # สีพื้นหลัง
    background.paste(final_image, mask=final_image.split()[3])

    # -------- Send --------
    with io.BytesIO() as buffer:
        background.save(buffer, "JPEG", quality=95)
        buffer.seek(0)
        await ctx.send(file=discord.File(buffer, "cover.jpg"))


@bot.command(name="ทำปก2")
async def make_cover_2(ctx, *, title: str):

    # -------- Config สำหรับ Template 2 --------
    FONT_SIZE = 78
    LINE_SPACING = 22
    START_X = 85  # ปรับระยะห่างจากขอบซ้ายตรงนี้
    START_Y = 970

    # เพิ่ม Setting สำหรับปรับขนาดภาพ (1.0 = พอดีกรอบแบบไม่โดนตัด 0.8 = ย่อลง 80% 1.2 = ขยาย 120%)
    IMAGE_SCALE = 1.2

    # เลื่อนตำแหน่งภาพ
    IMAGE_SHIFT_X = 0  
    IMAGE_SHIFT_Y = 0  

    MAIN_COLOR = (255, 255, 255, 255)
    HIGHLIGHT_COLOR = (188, 234, 47, 255)

    TARGET_SIZE = (1200, 1500)

    TEMPLATE_FILE = "template2.png"
    FONT_FILE = "font.ttf"
    # -----------------------

    if not ctx.message.attachments:
        await ctx.send("ลืมแนบรูปครับ!")
        return

    attachment = ctx.message.attachments[0]

    # -------- Load Image --------
    async with aiohttp.ClientSession() as session:
        async with session.get(attachment.url) as resp:
            data = io.BytesIO(await resp.read())
            user_image = Image.open(data).convert("RGBA")

    # -------- Load Template --------
    template = Image.open(TEMPLATE_FILE).convert("RGBA")
    template = template.resize(TARGET_SIZE, Image.Resampling.LANCZOS)

    t_width, t_height = template.size

    # -------- Resize Image (Not Fit/Crop) --------
    img_ratio = user_image.width / user_image.height
    template_ratio = t_width / t_height

    if img_ratio > template_ratio:
        base_scale = t_width / user_image.width
    else:
        base_scale = t_height / user_image.height

    final_scale = base_scale * IMAGE_SCALE

    new_size = (
        int(user_image.width * final_scale),
        int(user_image.height * final_scale)
    )

    resized = user_image.resize(new_size, Image.Resampling.LANCZOS)

    final_image = Image.new("RGBA", (t_width, t_height))

    # ---- แก้ไขให้ชิดบนตรงนี้ ----
    paste_x = ((t_width - resized.width) // 2) + IMAGE_SHIFT_X
    paste_y = 0 + IMAGE_SHIFT_Y # บังคับให้แกน Y เริ่มที่ 0 เพื่อให้ชิดบน

    final_image.paste(resized, (paste_x, paste_y))

    # -------- Apply Template (Mask) --------
    final_image.paste(template, (0, 0), template)

    # -------- Draw Text --------
    draw = ImageDraw.Draw(final_image)

    try:
        font = ImageFont.truetype(FONT_FILE, FONT_SIZE)

        lines = title.split("\n")
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

            current_x = START_X 

            for i, (text, color) in enumerate(parts):
                draw.text(
                    (current_x, current_y),
                    text,
                    font=font,
                    fill=color,
                    stroke_width=0,
                    stroke_fill=(0, 0, 0)
                )
                bbox = draw.textbbox((0, 0), text, font=font)
                w = bbox[2] - bbox[0]
                current_x += w  

            current_y += FONT_SIZE + LINE_SPACING

    except Exception as e:
        print("Text Error e")

    # -------- FIX Convert to JPG --------
    background = Image.new("RGB", final_image.size, (20, 20, 20))
    background.paste(final_image, mask=final_image.split()[3])

    # -------- Send --------
    with io.BytesIO() as buffer:
        background.save(buffer, "JPEG", quality=95)
        buffer.seek(0)
        await ctx.send(file=discord.File(buffer, "cover2.jpg"))

# ------------------ Run ------------------
keep_alive()
bot.run(os.environ.get("TOKEN"))
