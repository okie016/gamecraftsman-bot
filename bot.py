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

def get_styled_parts(text):
    """แยกข้อความออกมาเป็น list ของ (text, is_highlight)"""
    parts = []
    # Regex สำหรับจับคู่ [color]ข้อความ[/color]
    segments = re.split(r'(\[color\].*?\[/color\])', text)
    for seg in segments:
        if seg.startswith('[color]') and seg.endswith('[/color]'):
            content = seg.replace('[color]', '').replace('[/color]', '')
            parts.append((content, True))
        elif seg:
            parts.append((seg, False))
    return parts

@bot.command(name="ทำปก")
async def make_cover(ctx, *, title: str):
    # --- [ตั้งค่าดีไซน์] ---
    FONT_SIZE = 87
    TEXT_Y_POSITION = 1090
    MAIN_COLOR = (255, 255, 255, 255)      
    HIGHLIGHT_COLOR = (188, 234, 47, 255)   # สีเหลืองทอง
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
    
    # 2. ระบบวาดข้อความ (ใหม่หมด)
    draw = ImageDraw.Draw(final_image)
    try:
        font = ImageFont.truetype("font.ttf", FONT_SIZE)
        parts = get_styled_parts(title)
        
        # คำนวณความกว้างรวมของทุกส่วนก่อน
        total_width = 0
        prepared_parts = []
        for content, is_hl in parts:
            # ใช้พารามิเตอร์เพื่อให้วัดค่าภาษาไทยได้แม่นขึ้น
            bbox = draw.textbbox((0, 0), content, font=font)
            w = bbox[2] - bbox[0]
            total_width += w
            prepared_parts.append({
                'text': content, 
                'color': HIGHLIGHT_COLOR if is_hl else MAIN_COLOR, 
                'width': w
            })

        # จุดเริ่มวาด X เพื่อให้ก้อนทั้งหมดอยู่กลางภาพพอดี
        current_x = (t_width - total_width) // 2
        
        for p in prepared_parts:
            # วาดทีละส่วนต่อกัน
            draw.text((current_x, TEXT_Y_POSITION), p['text'], font=font, fill=p['color'])
            current_x += p['width']
            
    except Exception as e:
        print(f"Render Error: {e}")

    with io.BytesIO() as image_binary:
        final_image.save(image_binary, 'PNG')
        image_binary.seek(0)
        await ctx.send(file=discord.File(fp=image_binary, filename='cover.png'))

if __name__ == "__main__":
    keep_alive()
    bot.run(os.environ.get('TOKEN'))
