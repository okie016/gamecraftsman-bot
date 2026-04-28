import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io
import aiohttp
import os
from flask import Flask
from threading import Thread

# --- 1. ระบบ Web Server (หลอกให้ Render.com ไม่หลับ) ---
app = Flask('')
@app.route('/')
def home():
    return "GameCraftsman Bot is Live!"

def run():
    app.run(host='0.0.0.0', port=8000)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- 2. ตั้งค่าบอท Discord ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command(name="ทำปก")
async def make_cover(ctx, *, title: str):
    # --- [ส่วนตั้งค่าดีไซน์ - ปรับแก้ตรงนี้ได้เลย] ---
    FONT_SIZE = 80             # ขนาดตัวอักษร
    TEXT_Y_POSITION = 850      # ระยะห่างจากขอบบน (แกน Y) ส่วนแกน X จะจัดกลางให้อัตโนมัติ
    TEXT_COLOR = (255, 255, 255, 255) # สีขาว (RGBA)
    # ------------------------------------------

    # เช็กว่ามีการแนบรูปมาไหม
    if not ctx.message.attachments:
        await ctx.send("ลูกพี่ลืมแนบรูปภาพครับ! รบกวนอัปโหลดรูปแล้วใส่แคปชันว่า !ทำปก [พาดหัว] ด้วยครับ")
        return

    attachment = ctx.message.attachments[0]
    
    # ดึงรูปจาก Discord
    async with aiohttp.ClientSession() as session:
        async with session.get(attachment.url) as resp:
            if resp.status != 200:
                await ctx.send("ดึงรูปภาพไม่สำเร็จ ลองใหม่อีกครั้งนะครับ")
                return
            data = io.BytesIO(await resp.read())
            user_image = Image.open(data).convert("RGBA")

    try:
        # 3. โหลดไฟล์ Template และเตรียมพื้นที่
        template = Image.open("template.png").convert("RGBA")
        t_width, t_height = template.size

        # 4. จัดการรูปพื้นหลัง (Fit Height & Center Width)
        # ปรับความสูงรูปให้เท่ากับ Template โดยรักษาอัตราส่วน (Aspect Ratio)
        ratio = t_height / user_image.height
        new_width = int(user_image.width * ratio)
        user_image = user_image.resize((new_width, t_height), Image.Resampling.LANCZOS)
        
        # สร้างแคนวาสใหม่และวางรูปให้อยู่ตรงกลางแกน X
        final_image = Image.new("RGBA", (t_width, t_height))
        offset_x = (t_width - new_width) // 2
        final_image.paste(user_image, (offset_x, 0))
        
        # 5. วาง Template ทับ (ส่วนที่เจาะใสจะมองเห็นรูปข้างล่าง)
        final_image.paste(template, (0, 0), template)
        
        # 6. เขียนพาดหัว (จัดกึ่งกลางอัตโนมัติ)
        draw = ImageDraw.Draw(final_image)
        # ตรวจสอบว่ามีไฟล์ฟอนต์ไหม ถ้าไม่มีจะใช้ฟอนต์ระบบแทน
        try:
            font = ImageFont.truetype("font.ttf", FONT_SIZE)
        except:
            font = ImageFont.load_default()
            print("Warning: font.ttf not found, using default font.")

        # คำนวณหาจุดกึ่งกลางของข้อความ
        bbox = draw.textbbox((0, 0), title, font=font)
        text_width = bbox[2] - bbox[0]
        center_text_x = (t_width - text_width) // 2
        
        # วาดข้อความลงบนภาพ
        draw.text((center_text_x, TEXT_Y_POSITION), title, font=font, fill=TEXT_COLOR)

        # 7. ส่งไฟล์กลับ
        with io.BytesIO() as image_binary:
            final_image.save(image_binary, 'PNG')
            image_binary.seek(0)
            await ctx.send(file=discord.File(fp=image_binary, filename='gamecraftsman_cover.png'))

    except Exception as e:
        await ctx.send(f"เกิดข้อผิดพลาดหลังบ้าน: {str(e)}")
        print(f"Error: {e}")

# เริ่มรันระบบ
if __name__ == "__main__":
    keep_alive() # เปิดเว็บหลอกสำหรับ Render.com
    
    # ดึง Token จาก Environment Variable ที่ตั้งไว้ใน Render
    token = os.environ.get('TOKEN')
    if token:
        bot.run(token)
    else:
        print("Error: No TOKEN found in environment variables.")
