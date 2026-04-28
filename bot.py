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

# ------------------ Cover Command ------------------
@bot.command(name="ทำปก")
async def make_cover(ctx, *, title: str):

    # -------- Design Config --------
    FONT_SIZE = 90
    LINE_SPACING = 20
    START_Y = 990

    MAIN_COLOR = (255, 255, 255, 255)
    HIGHLIGHT_COLOR = (188, 234, 47, 255)

    # --------------------------------

    if not ctx.message.attachments:
        await ctx.send("ลืมแนบรูปครับ!")
        return

    attachment = ctx.message.attachments[0]

    # -------- Load User Image --------
    async with aiohttp.ClientSession() as session:
        async with session.get(attachment.url) as resp:
            data = io.BytesIO(await resp.read())
            user_image = Image.open(data).convert("RGBA")

    # -------- Load Template --------
    template = Image.open("template.png").convert("RGBA")
    t_width, t_height = template.size

    # -------- Cover + Center Crop --------
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

    # -------- Overlay Template --------
    final_image.paste(template, (0, 0), template)

    # -------- Draw Text --------
    draw = ImageDraw.Draw(final_image)

    try:
        font = ImageFont.truetype("font.ttf", FONT_SIZE)

        # แยกหลายบรรทัด (รองรับ Enter)
        lines = title.split("\n")
        current_y = START_Y

        for line in lines:

            # --- แยก [color] ---
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

            # --- คำนวณความกว้าง ---
            total_width = 0
            widths = []

            for text, _ in parts:
                bbox = draw.textbbox((0, 0), text, font=font)
                w = bbox[2] - bbox[0]
                widths.append(w)
                total_width += w

            # --- center ---
            start_x = (t_width - total_width) // 2
            current_x = start_x

            # --- draw ทีละ segment ---
            for i, (text, color) in enumerate(parts):
                draw.text(
                    (current_x, current_y),
                    text,
                    font=font,
                    fill=color,
                    stroke_width=2,
                    stroke_fill=(0, 0, 0)
                )
                current_x += widths[i]

            # --- ขยับลงบรรทัดถัดไป ---
            current_y += FONT_SIZE + LINE_SPACING

    except Exception as e:
        print("Text Error:", e)

    # -------- Send Back --------
    with io.BytesIO() as buffer:
        final_image.save(buffer, "PNG")
        buffer.seek(0)
        await ctx.send(file=discord.File(buffer, "cover.png"))

# ------------------ Run ------------------
keep_alive()
bot.run(os.environ.get("TOKEN"))
