
import subprocess
import shutil
from pathlib import Path
from PIL import Image
from rembg import remove, new_session

SESSION = new_session("isnet-general-use")


def process_photo(input_path, output_path):
    image = Image.open(input_path).convert("RGBA")
    result = remove(image, session=SESSION)
    result.thumbnail((512, 512))

    sticker = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    x = (512 - result.width) // 2
    y = (512 - result.height) // 2
    sticker.alpha_composite(result, (x, y))

    sticker.save(output_path, optimize=True)
    return output_path


def process_video(input_path, output_path):
    work_dir = Path("frames")
    transparent_dir = work_dir / "transparent"

    shutil.rmtree(work_dir, ignore_errors=True)
    transparent_dir.mkdir(parents=True, exist_ok=True)

    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(input_path),
            "-t", "3", "-vf", "fps=20",
            str(work_dir / "frame_%04d.png")
        ], check=True, stdout=subprocess.DEVNULL,
           stderr=subprocess.DEVNULL, timeout=60)

        frames = sorted(work_dir.glob("frame_*.png"))

        if not frames or len(frames) > 60:
            raise ValueError("Invalid frame count")

        for frame in frames:
            image = Image.open(frame).convert("RGBA")
            result = remove(image, session=SESSION)
            result.thumbnail((512, 512))

            canvas = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
            x = (512 - result.width) // 2
            y = (512 - result.height) // 2
            canvas.alpha_composite(result, (x, y))
            canvas.save(transparent_dir / frame.name, optimize=True)

        subprocess.run([
            "ffmpeg", "-y",
            "-framerate", "20",
            "-i", str(transparent_dir / "frame_%04d.png"),
            "-vf",
            "scale=512:512:force_original_aspect_ratio=decrease,"
            "pad=512:512:(ow-iw)/2:(oh-ih):color=0x00000000",
            "-c:v", "libvpx-vp9",
            "-pix_fmt", "yuva420p",
            "-crf", "50", "-b:v", "0",
            "-auto-alt-ref", "0",
            str(output_path)
        ], check=True, stdout=subprocess.DEVNULL,
           stderr=subprocess.DEVNULL, timeout=120)

        if Path(output_path).stat().st_size > 256 * 1024:
            raise ValueError("Sticker exceeds 256 KB")

        return output_path

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
