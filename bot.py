import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io, aiohttp, os, re
from flask import Flask
from threading import Thread

# --- [ระบบ Web Server สำหรับ Render] ---
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
    # --- [ส่วนตั้งค่าดีไซน์ - แก้ตรงนี้ได้เลย] ---
    FONT_SIZE = 80             
    TEXT_Y_POSITION = 850      # ปรับความสูงต่ำที่ตัวเลขนี้
    MAIN_COLOR = (255, 255, 255, 255)      
    HIGHLIGHT_COLOR = (188, 234, 47, 255)   # สีเหลืองทอง
    # -------------------------------------

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

    # 1. จัดการรูปพื้นหลัง (Center & Fit Height)
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
        
        # ลบ Tag ออกเพื่อคำนวณความกว้างของข้อความเพียวๆ
        clean_text = title.replace('[color]', '').replace('[/color]', '')
        
        # วัดขนาดข้อความทั้งหมดแบบก้อนเดียว (กลับมาใช้การวัดมาตรฐานที่เสถียรที่สุด)
        bbox = draw.textbbox((0, 0), clean_text, font=font)
        total_text_width = bbox[2] - bbox[0]
        
        # จุดเริ่มวาด X เพื่อให้ก้อนทั้งหมดอยู่กลางภาพพอดี
        current_x = (t_width - total_text_width) // 2
        
        # แยกส่วนเพื่อวาดทีละสี
        parts = re.split(r'(\[color\].*?\[/color\])', title)
        for part in parts:
            if not part: continue
            
            if part.startswith('[color]') and part.endswith('[/color]'):
                content = part.replace('[color]', '').replace('[/color]', '')
                color = HIGHLIGHT_COLOR
            else:
                content = part
                color = MAIN_COLOR
            
            # วาดข้อความส่วนนั้นๆ
            draw.text((current_x, TEXT_Y_POSITION), content, font=font, fill=color)
            
            # ขยับพิกัด X ไปข้างหน้าตามความกว้างของส่วนที่เพิ่งวาด
            part_bbox = draw.textbbox((0, 0), content, font=font)
            current_x += (part_bbox[2] - part_bbox[0])
            
    except Exception as e:
        print(f"Render Error: {e}")

    with io.BytesIO() as image_binary:
        final_image.save(image_binary, 'PNG')
        image_binary.seek(0)
        await ctx.send(file=discord.File(fp=image_binary, filename='cover.png'))

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('TOKEN'))
