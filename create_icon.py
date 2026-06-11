"""生成智分宝桌面图标 icon.ico"""
from PIL import Image, ImageDraw, ImageFont
import os, math

SIZE = 256
img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
draw = ImageDraw.Draw(img)

# ── 绿色圆形背景 ──
draw.ellipse([4, 4, 252, 252], fill=(46, 125, 50, 255))
draw.ellipse([10, 10, 246, 246], fill=(56, 142, 60, 255))

# ── 高光（左上角月牙形，增加质感） ──
draw.ellipse([30, 30, 130, 130], fill=(255, 255, 255, 28))
draw.ellipse([20, 20, 110, 110], fill=(255, 255, 255, 16))

# ── 白色回收标志 ♻ ──
font = None
for name in ["seguiemj.ttf", "seguisym.ttf", "segoeuiss.ttf",
             "segoeui.ttf", "arial.ttf", "msyh.ttc", "simsun.ttc"]:
    try:
        font = ImageFont.truetype(name, 148)
        break
    except (IOError, OSError):
        continue

if font:
    draw.text((SIZE // 2, SIZE // 2 - 8), "♻",
              fill=(255, 255, 255, 255), font=font, anchor="mm")
else:
    # 手工画回收三角
    cx, cy = SIZE // 2, SIZE // 2
    for deg in [0, 120, 240]:
        a = math.radians(deg)
        px = cx + 65 * math.cos(a)
        py = cy - 65 * math.sin(a)
        pts = []
        for da in [-20, 0, 20]:
            aa = a + math.radians(da)
            pts.append((px + 28 * math.cos(aa), py - 28 * math.sin(aa)))
        draw.polygon(pts, fill=(255, 255, 255, 255))
    draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(46, 125, 50, 255))

# ── 底部 "智分宝" 文字 ──
font_sm = None
for name in ["msyh.ttc", "msyhbd.ttc", "simhei.ttf", "arial.ttf"]:
    try:
        font_sm = ImageFont.truetype(name, 26)
        break
    except (IOError, OSError):
        continue
if font_sm:
    draw.text((SIZE // 2, 215), "智分宝",
              fill=(255, 255, 255, 200), font=font_sm, anchor="mm")

# ── 保存多尺寸 .ico ──
output = os.path.join(os.path.dirname(__file__), "icon.ico")
img.save(output, format="ICO", sizes=[(256, 256), (64, 64), (48, 48), (32, 32), (16, 16)])
print(f"[OK] Icon saved: {output}")
