import discord
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
import io
import aiohttp
import os
from flask import Flask
from threading import Thread

# --- ส่วนสร้างเว็บหลอกให้ Render.com ไม่ปิดบอทเรา ---
app = Flask('')
@app.route('/')
def home():
    return "GameCraftsman Bot is running!"
def run():
    app.run(host='0.0.0.0', port=8000)
def keep_alive():
    t = Thread(target=run)
    t.start()
# ------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.command()
async def ทำปก(ctx, *, title: str):
    if not ctx.message.attachments:
        await ctx.send("ลูกพี่ลืมแนบรูปภาพครับ!")
        return

    attachment = ctx.message.attachments[0]
    
    async with aiohttp.ClientSession() as session:
        async with session.get(attachment.url) as resp:
            data = io.BytesIO(await resp.read())
            user_image = Image.open(data).convert("RGBA")

    template = Image.open("template.png").convert("RGBA")
    font = ImageFont.truetype("font.ttf", 80) 
    
    user_image = user_image.resize(template.size) 
    final_image = Image.new("RGBA", template.size)
    
    final_image.paste(user_image, (0, 0)) 
    final_image.paste(template, (0, 0), template) 
    
    draw = ImageDraw.Draw(final_image)
    draw.text((100, 100), title, font=font, fill=(255, 255, 255)) 
    
    with io.BytesIO() as image_binary:
        final_image.save(image_binary, 'PNG')
        image_binary.seek(0)
        await ctx.send(file=discord.File(fp=image_binary, filename='cover.png'))

# ปลุกเซิร์ฟเวอร์หลอกให้ตื่น
keep_alive()
# ดึง Token จากระบบของ Render มาใช้ (ปลอดภัยกว่าพิมพ์ลงไปตรงๆ)
bot.run(os.environ.get('TOKEN'))