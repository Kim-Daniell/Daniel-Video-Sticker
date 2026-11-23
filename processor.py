
import subprocess
import shutil
from pathlib import Path

from PIL import Image
from rembg import remove, new_session


SESSION = new_session("isnet-general-use")

CANVAS_SIZE = (512, 512)


def prepare_frame(input_path, output_path, remove_background=True):
    """
    آماده‌سازی یک فریم با ابعاد 512 در 512
    """

    image = Image.open(input_path).convert("RGBA")

    if remove_background:
        image = remove(image, session=SESSION)

    image.thumbnail(CANVAS_SIZE)

    canvas = Image.new(
        "RGBA",
        CANVAS_SIZE,
        (0, 0, 0, 0)
    )

    x = (512 - image.width) // 2
    y = (512 - image.height) // 2

    canvas.alpha_composite(image, (x, y))

    canvas.save(output_path, optimize=True)

    return output_path


def process_photo(
    input_path,
    output_path,
    remove_background=True
):
    """
    ساخت استیکر عکس با فرمت WebP
    """

    output_path = Path(output_path)
    temp_path = output_path.with_name("photo_temp.png")

    try:
        prepare_frame(
            input_path,
            temp_path,
            remove_background
        )

        image = Image.open(temp_path).convert("RGBA")

        # تلاش برای ساخت فایل زیر محدودیت حجم تلگرام
        for quality in (90, 80, 70, 60, 50):
            image.save(
                output_path,
                "WEBP",
                quality=quality,
                method=6
            )

            if output_path.stat().st_size <= 512 * 1024:
                return output_path

        raise ValueError("Sticker exceeds 512 KB")

    finally:
        temp_path.unlink(missing_ok=True)


def process_video(
    input_path,
    output_path,
    remove_background=True
):
    """
    ساخت استیکر ویدیویی WebM با VP9
    """

    work_dir = Path("frames")
    transparent_dir = work_dir / "transparent"

    shutil.rmtree(work_dir, ignore_errors=True)
    transparent_dir.mkdir(parents=True, exist_ok=True)

    try:
        # استخراج فریم‌ها
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i", str(input_path),
                "-t", "3",
                "-vf", "fps=20",
                str(work_dir / "frame_%04d.png")
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60
        )

        frames = sorted(work_dir.glob("frame_*.png"))

        if not frames or len(frames) > 60:
            raise ValueError("Invalid frame count")

        # پردازش فریم‌ها
        for frame in frames:
            output_frame = transparent_dir / frame.name

            prepare_frame(
                frame,
                output_frame,
                remove_background
            )

        # ساخت ویدیوی نهایی
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-framerate", "20",
                "-i", str(transparent_dir / "frame_%04d.png"),
                "-c:v", "libvpx-vp9",
                "-pix_fmt", "yuva420p",
                "-crf", "40",
                "-b:v", "0",
                "-auto-alt-ref", "0",
                "-an",
                str(output_path)
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=120
        )

        if Path(output_path).stat().st_size > 256 * 1024:
            raise ValueError("Sticker exceeds 256 KB")

        return output_path

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
