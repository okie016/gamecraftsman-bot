import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io
import aiohttp
import os
from flask import Flask
from threading import Thread

# --- ระบบ Web Server สำหรับ Render.com ---
app = Flask('')
@app.route('/')
def home():
    return "GameCraftsman Bot is Live!"
def run():
    app.run(host='0.0.0.0', port=8000)
def keep_alive():
    t = Thread(target=run)
    t.start()

# --- ตั้งค่าบอท ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command(name="ทำปก")
async def make_cover(ctx, *, title: str):
    # --- [ส่วนตั้งค่าดีไซน์] ---
    FONT_SIZE = 87             # ขนาดฟอนต์
    TEXT_POSITION = (1936.9204, 895.9883) # ตำแหน่งข้อความ (X, Y)
    TEXT_COLOR = (255, 255, 255, 255) # สีขาว (R, G, B, Alpha)
    # -----------------------
# คำนวณหาจุดกึ่งกลาง (สูตร: (ความกว้างภาพ - ความกว้างข้อความ) / 2)
    bbox = draw.textbbox((0, 0), title, font=font)
    text_width = bbox[2] - bbox[0]
    
    # ถ้าอยากจัดกลางแกน X แต่ Fix ความสูงแกน Y ไว้ที่ 850
    center_x = (template.width - text_width) // 2
    draw.text((center_x, 1936.9204), title, font=font, fill=TEXT_COLOR)
    if not ctx.message.attachments:
        await ctx.send("ลูกพี่ลืมแนบรูปภาพครับ!")
        return

    attachment = ctx.message.attachments[0]
    
    async with aiohttp.ClientSession() as session:
        async with session.get(attachment.url) as resp:
            data = io.BytesIO(await resp.read())
            # โหลดรูปจากแชทและแปลงเป็น RGBA เพื่อความโปร่งใส
            user_image = Image.open(data).convert("RGBA")

    # 1. โหลด Template (หน้ากาก)
    template = Image.open("template.png").convert("RGBA")
    t_width, t_height = template.size

    # 2. ปรับขนาดรูปจากแชทให้ Fit ขอบบน-ล่าง (Maintain Aspect Ratio)
    # คำนวณอัตราส่วนเพื่อให้ความสูงเท่ากับ Template เป๊ะๆ
    ratio = t_height / user_image.height
    new_width = int(user_image.width * ratio)
    user_image = user_image.resize((new_width, t_height), Image.Resampling.LANCZOS)
    
    # 3. สร้าง Canvas เปล่า และคำนวณตำแหน่งเพื่อให้รูปอยู่กึ่งกลาง (Horizontal Center)
    final_image = Image.new("RGBA", (t_width, t_height))
    
    # คำนวณจุดเริ่มวางแกน X (ถ้ากว้างกว่า Template จะโดนตัดขอบข้างออกเท่าๆ กัน)
    offset_x = (t_width - new_width) // 2
    
    # 4. วางเลเยอร์
    # วางรูปพื้นหลังที่จัดกึ่งกลางแล้ว (offset_x อาจเป็นค่าลบถ้ารูปกว้าง ซึ่งจะทำให้ Center พอดี)
    final_image.paste(user_image, (offset_x, 0))
    # วาง Template ทับด้านบน
    final_image.paste(template, (0, 0), template)
    
    # 5. เขียนข้อความ (เลเยอร์บนสุด)
    try:
        font = ImageFont.truetype("font.ttf", FONT_SIZE)
        draw = ImageDraw.Draw(final_image)
        draw.text(TEXT_POSITION, title, font=font, fill=TEXT_COLOR)
    except Exception as e:
        print(f"Font Error: {e}")

    # 6. ส่งรูปกลับเข้า Discord
    with io.BytesIO() as image_binary:
        # เซฟเป็น PNG เพื่อรักษาความคมชัด
        final_image.save(image_binary, 'PNG')
        image_binary.seek(0)
        await ctx.send(file=discord.File(fp=image_binary, filename='gamecraftsman_cover.png'))

keep_alive()
bot.run(os.environ.get('TOKEN'))
