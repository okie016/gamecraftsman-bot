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
    
    # 2. ระบบวาดข้อความ (Fixed Align Center & Color Logic)
    draw = ImageDraw.Draw(final_image)
    try:
        font = ImageFont.truetype("font.ttf", FONT_SIZE)

        # แยกข้อความเป็นส่วนๆ เพื่อหาความกว้างรวม (สำหรับการ Align Center)
        # Regex นี้จะช่วยแยกส่วนที่เป็น [color] ออกจากข้อความปกติ
        parts_data = []
        full_clean_text = ""
        
        raw_parts = re.split(r'(\[color\].*?\[/color\])', title)
        
        total_text_width = 0
        for part in raw_parts:
            if not part: continue
            
            is_highlight = False
            content = part
            if part.startswith('[color]') and part.endswith('[/color]'):
                content = part.replace('[color]', '').replace('[/color]', '')
                is_highlight = True
            
            # คำนวณความกว้างของส่วนนี้
            bbox = draw.textbbox((0, 0), content, font=font)
            part_width = bbox[2] - bbox[0]
            
            parts_data.append({
                'content': content,
                'width': part_width,
                'is_highlight': is_highlight
            })
            total_text_width += part_width

        # หาจุดเริ่มวาด x เพื่อให้ทั้งประโยคอยู่ตรงกลาง
        current_x = (t_width - total_text_width) // 2

        # เริ่มวาดทีละส่วนต่อกัน
        for p in parts_data:
            text_color = HIGHLIGHT_COLOR if p['is_highlight'] else MAIN_COLOR
            # วาดข้อความ
            draw.text((current_x, TEXT_Y_POSITION), p['content'], font=font, fill=text_color)
            # ขยับตำแหน่ง x ไปข้างหน้าตามความกว้างของข้อความที่เพิ่งวาด
            current_x += p['width']
            
    except Exception as e:
        print(f"Render Error: {e}")

    with io.BytesIO() as image_binary:
        final_image.save(image_binary, 'PNG')
        image_binary.seek(0)
        await ctx.send(file=discord.File(fp=image_binary, filename='cover.png'))

keep_alive()
bot.run(os.environ.get('TOKEN'))
