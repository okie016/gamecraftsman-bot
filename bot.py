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
def run(): app.run(host='0.0.0.0', port=8000)
def keep_alive():
    t = Thread(target=run); t.start()

# --- [ตั้งค่าบอท] ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command(name="ทำปก")
async def make_cover(ctx, *, title: str):
    # --- [ส่วนตั้งค่าดีไซน์] ---
    FONT_SIZE = 87             
    TEXT_Y_POSITION = 1090     
    MAIN_COLOR = (255, 255, 255, 255)      # สีขาว
    HIGHLIGHT_COLOR = (188, 234, 47, 255)   # สีเหลืองทอง
    # -----------------------

    if not ctx.message.attachments:
        await ctx.send("ลูกพี่ลืมแนบรูปภาพครับ!")
        return

    attachment = ctx.message.attachments[0]
    async with aiohttp.ClientSession() as session:
        async with session.get(attachment.url) as resp:
            data = io.BytesIO(await resp.read())
            user_image = Image.open(data).convert("RGBA")

    template = Image.open("template.png").convert("RGBA")
    t_width, t_height = template.size

    # 1. จัดการรูปพื้นหลัง (Center & Fit)
    ratio = t_height / user_image.height
    new_width = int(user_image.width * ratio)
    user_image = user_image.resize((new_width, t_height), Image.Resampling.LANCZOS)
    final_image = Image.new("RGBA", (t_width, t_height))
    offset_x = (t_width - new_width) // 2
    final_image.paste(user_image, (offset_x, 0))
    final_image.paste(template, (0, 0), template)
    
    # 2. ระบบวาดข้อความ (Multi-Color Layering Logic)
    draw = ImageDraw.Draw(final_image)
    try:
        font = ImageFont.truetype("font.ttf", FONT_SIZE)

        # เตรียมข้อความ: 1.แบบเพียวๆ 2.แบบเว้นช่องว่างเพื่อเตรียมทับสี
        clean_text = title.replace('[color]', '').replace('[/color]', '')
        
        # หาจุดกึ่งกลางของข้อความทั้งหมด
        bbox = draw.textbbox((0, 0), clean_text, font=font)
        text_width = bbox[2] - bbox[0]
        start_x = (t_width - text_width) // 2

        # ขั้นตอนที่ A: วาดข้อความทั้งหมดเป็นสีขาว (MAIN_COLOR) ไว้ก่อน
        draw.text((start_x, TEXT_Y_POSITION), clean_text, font=font, fill=MAIN_COLOR)

        # ขั้นตอนที่ B: วาดสี HIGHLIGHT ทับเฉพาะส่วนที่อยู่ใน [color]
        # เราจะใช้วิธีหาตำแหน่งของคำในประโยคเพื่อวาดให้ตรงล็อค
        current_x_offset = start_x
        parts = re.split(r'(\[color\].*?\[/color\])', title)
        
        for part in parts:
            if not part: continue
            
            if part.startswith('[color]') and part.endswith('[/color]'):
                content = part.replace('[color]', '').replace('[/color]', '')
                # วาดทับลงไปในตำแหน่งปัจจุบัน
                draw.text((current_x_offset, TEXT_Y_POSITION), content, font=font, fill=HIGHLIGHT_COLOR)
                measured_text = content
            else:
                measured_text = part
            
            # ขยับ Offset ตามความกว้างของข้อความที่ผ่านไป
            p_bbox = draw.textbbox((0, 0), measured_text, font=font)
            current_x_offset += (p_bbox[2] - p_bbox[0])
            
    except Exception as e:
        print(f"Render Error: {e}")

    with io.BytesIO() as image_binary:
        final_image.save(image_binary, 'PNG')
        image_binary.seek(0)
        await ctx.send(file=discord.File(fp=image_binary, filename='cover.png'))

keep_alive()
bot.run(os.environ.get('TOKEN'))
