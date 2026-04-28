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

def draw_styled_text(draw, text, font, y_position, container_width, default_color, highlight_color):
    """ฟังก์ชันวาดข้อความแยกสีและจัดกึ่งกลางบรรทัดเดียว"""
    # แยกส่วนประกอบด้วย Tag [color]...[/color]
    parts = re.split(r'(\[color\].*?\[/color\])', text)
    
    # 1. คำนวณความกว้างรวมทั้งหมดก่อนเพื่อหาจุดเริ่มวางให้กึ่งกลาง
    total_width = 0
    display_parts = []
    
    for part in parts:
        if part.startswith('[color]') and part.endswith('[/color]'):
            content = part.replace('[color]', '').replace('[/color]', '')
            color = highlight_color
        else:
            content = part
            color = default_color
        
        if content:
            bbox = draw.textbbox((0, 0), content, font=font)
            w = bbox[2] - bbox[0]
            total_width += w
            display_parts.append({'text': content, 'color': color, 'width': w})

    # 2. เริ่มวาดจากจุดที่ทำให้ก้อนทั้งหมดอยู่กลางภาพ
    current_x = (container_width - total_width) // 2
    
    for p in display_parts:
        draw.text((current_x, y_position), p['text'], font=font, fill=p['color'])
        current_x += p['width']

@bot.command(name="ทำปก")
async def make_cover(ctx, *, title: str):
    # --- [ตั้งค่าดีไซน์] ---
    FONT_SIZE = 80
    TEXT_Y_POSITION = 1100
    MAIN_COLOR = (255, 255, 255, 255)      # สีขาว
    HIGHLIGHT_COLOR = (188, 234, 47, 255)   # สีทอง (ปรับเปลี่ยนได้ตามใจชอบ)
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

    # จัดการรูปพื้นหลัง
    ratio = t_height / user_image.height
    new_width = int(user_image.width * ratio)
    user_image = user_image.resize((new_width, t_height), Image.Resampling.LANCZOS)
    
    final_image = Image.new("RGBA", (t_width, t_height))
    offset_x = (t_width - new_width) // 2
    final_image.paste(user_image, (offset_x, 0))
    final_image.paste(template, (0, 0), template)
    
    # วาดข้อความด้วยระบบ Styled Text
    draw = ImageDraw.Draw(final_image)
    try:
        font = ImageFont.truetype("font.ttf", FONT_SIZE)
        draw_styled_text(draw, title, font, TEXT_Y_POSITION, t_width, MAIN_COLOR, HIGHLIGHT_COLOR)
    except Exception as e:
        print(f"Error: {e}")

    with io.BytesIO() as image_binary:
        final_image.save(image_binary, 'PNG')
        image_binary.seek(0)
        await ctx.send(file=discord.File(fp=image_binary, filename='cover.png'))

keep_alive()
bot.run(os.environ.get('TOKEN'))
