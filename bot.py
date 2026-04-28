import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io, aiohttp, os, re
from flask import Flask
from threading import Thread

# --- [ระบบ Web Server] ---
app = Flask('')
@app.route('/')
def home(): return "GameCraftsman Bot is Live!"

def run(): 
    app.run(host='0.0.0.0', port=8000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- [ตั้งค่าบอท] ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command(name="ทำปก")
async def make_cover(ctx, *, title: str):
    
    # --- [ส่วนตั้งค่าดีไซน์] ---
    FONT_SIZE = 87
    TEXT_Y_POSITION = 1090
    MAIN_COLOR = (255, 255, 255, 255)       # สีขาว
    HIGHLIGHT_COLOR = (188, 234, 47, 255)  # สีทอง
    # -----------------------

    if not ctx.message.attachments:
        await ctx.send("ลูกพี่ลืมแนบรูปภาพครับ!")
        return

    attachment = ctx.message.attachments[0]

    # --- โหลดรูปจาก Discord ---
    async with aiohttp.ClientSession() as session:
        async with session.get(attachment.url) as resp:
            data = io.BytesIO(await resp.read())
            user_image = Image.open(data).convert("RGBA")

    # --- โหลด template ---
    template = Image.open("template.png").convert("RGBA")
    t_width, t_height = template.size

    # --- จัดภาพพื้นหลัง (Center & Fit) ---
    ratio = t_height / user_image.height
    new_width = int(user_image.width * ratio)
    user_image = user_image.resize((new_width, t_height), Image.Resampling.LANCZOS)

    final_image = Image.new("RGBA", (t_width, t_height))
    offset_x = (t_width - new_width) // 2

    final_image.paste(user_image, (offset_x, 0))
    final_image.paste(template, (0, 0), template)

    # --- วาดข้อความ ---
    draw = ImageDraw.Draw(final_image)

    try:
        font = ImageFont.truetype("font.ttf", FONT_SIZE)

        # 1. แยกข้อความตาม [color]
        parts_raw = re.split(r'(\[color\].*?\[/color\])', title)

        parts = []
        for part in parts_raw:
            if not part:
                continue

            if part.startswith('[color]') and part.endswith('[/color]'):
                content = part.replace('[color]', '').replace('[/color]', '')
                parts.append((content, HIGHLIGHT_COLOR))
            else:
                parts.append((part, MAIN_COLOR))

        # 2. คำนวณความกว้างรวม
        total_width = 0
        widths = []

        for text, _ in parts:
            bbox = draw.textbbox((0, 0), text, font=font)
            w = bbox[2] - bbox[0]
            widths.append(w)
            total_width += w

        # 3. หา position center
        start_x = (t_width - total_width) // 2
        current_x = start_x

        # 4. วาดทีละส่วน (ไม่มี duplicate แล้ว)
        for i, (text, color) in enumerate(parts):
            draw.text(
                (current_x, TEXT_Y_POSITION),
                text,
                font=font,
                fill=color,
                stroke_width=2,            # ขอบตัวอักษร (เพิ่มความอ่านง่าย)
                stroke_fill=(0, 0, 0)
            )
            current_x += widths[i]

    except Exception as e:
        print(f"Render Error: {e}")

    # --- ส่งรูปกลับ Discord ---
    with io.BytesIO() as image_binary:
        final_image.save(image_binary, 'PNG')
        image_binary.seek(0)
        await ctx.send(file=discord.File(fp=image_binary, filename='cover.png'))

# --- รันบอท ---
keep_alive()
bot.run(os.environ.get('TOKEN'))
