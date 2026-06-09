"""
模型权重下载脚本

用法:
    python download_model.py                 # 从 GitHub Releases 下载
    python download_model.py --url <URL>     # 从自定义 URL 下载

说明:
    模型文件 best.pt (~6 MB) 默认已通过 Git 直接跟踪在 models/ 目录下。
    此脚本作为备用下载方式，在以下场景使用：
    - 从 GitHub Releases 单独获取模型（无需克隆完整仓库）
    - 模型文件被误删除后的快速恢复
"""
import os
import sys
import urllib.request
import argparse

# ── 默认下载地址（GitHub Releases） ──
# 第一次发布 Release 后，把下方 URL 替换为实际的 Release 下载链接
# 格式: https://github.com/<用户名>/<仓库名>/releases/download/<标签>/best.pt
DEFAULT_URL = (
    "https://github.com/Patience-creat/garbage-project/releases/download/v1.0/best.pt"
)

MODEL_DIR = "models"
MODEL_FILE = os.path.join(MODEL_DIR, "best.pt")


def download_model(url: str) -> None:
    """从指定 URL 下载模型权重"""
    os.makedirs(MODEL_DIR, exist_ok=True)

    if os.path.isfile(MODEL_FILE):
        size = os.path.getsize(MODEL_FILE) / 1024 / 1024
        print(f"✅ 模型已存在: {MODEL_FILE} ({size:.1f} MB)")
        return

    print(f"⬇️  正在下载模型权重...")
    print(f"   来源: {url}")
    print(f"   目标: {MODEL_FILE}")
    print()

    def report(block: int, chunk: int, total: int) -> None:
        if total > 0:
            downloaded = block * chunk / 1024 / 1024
            total_mb = total / 1024 / 1024
            pct = downloaded / total_mb * 100
            bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
            sys.stdout.write(f"\r   [{bar}] {downloaded:.1f}/{total_mb:.1f} MB ({pct:.0f}%)")
            sys.stdout.flush()

    try:
        urllib.request.urlretrieve(url, MODEL_FILE, reporthook=report)
        print("\n✅ 模型下载完成！")
    except Exception as e:
        print(f"\n❌ 下载失败: {e}")
        print()
        print("请手动下载模型文件：")
        print(f"  1. 访问 {url}")
        print(f"  2. 将 best.pt 放入 {MODEL_DIR}/ 目录")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="下载垃圾分类检测模型权重")
    parser.add_argument("--url", default=DEFAULT_URL, help="模型下载 URL")
    args = parser.parse_args()
    download_model(args.url)


if __name__ == "__main__":
    main()
