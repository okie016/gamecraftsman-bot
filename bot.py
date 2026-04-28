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
    # --- [ตั้งค่าดีไซน์] ---
    FONT_SIZE = 87
    TEXT_Y_POSITION = 1090      # กำหนดแค่ความสูง (แกน Y) ส่วนแกน X จะกลางเป๊ะๆ
    MAIN_COLOR = (255, 255, 255, 255)      
    HIGHLIGHT_COLOR = (188, 234, 47, 255)
    # -------------------

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
    
    # 2. ระบบวาดข้อความ (Alignment Fix)
    draw = ImageDraw.Draw(final_image)
    try:
        font = ImageFont.truetype("font.ttf", FONT_SIZE)
        
        # แยกส่วนข้อความ [color]...[/color]
        parts = re.split(r'(\[color\].*?\[/color\])', title)
        
        # คำนวณหาความกว้างรวมของ "ทุกส่วน" ก่อนเริ่มวาด
        total_width = 0
        render_data = []
        for part in parts:
            if part.startswith('[color]') and part.endswith('[/color]'):
                content = part.replace('[color]', '').replace('[/color]', '')
                color = HIGHLIGHT_COLOR
            else:
                content = part
                color = MAIN_COLOR
            
            if content:
                # วัดขนาดแต่ละส่วน (ใช้ anchor='lt' เพื่อความแม่นยำ)
                bbox = draw.textbbox((0, 0), content, font=font, anchor='lt')
                w = bbox[2] - bbox[0]
                total_width += w
                render_data.append({'text': content, 'color': color, 'width': w})

        # จุดเริ่มวาด X ที่ทำให้ "ก้อนทั้งหมด" อยู่กลางภาพพอดี
        current_x = (t_width - total_width) // 2
        
        for item in render_data:
            # วาดต่อกันไปเรื่อยๆ โดยใช้จุดเริ่มจากกึ่งกลางที่คำนวณไว้
            draw.text((current_x, TEXT_Y_POSITION), item['text'], font=font, fill=item['color'], anchor='lt')
            current_x += item['width']
            
    except Exception as e:
        print(f"Render Error: {e}")

    with io.BytesIO() as image_binary:
        final_image.save(image_binary, 'PNG')
        image_binary.seek(0)
        await ctx.send(file=discord.File(fp=image_binary, filename='cover.png'))

keep_alive()
bot.run(os.environ.get('TOKEN'))
