from pathlib import Path
from PIL import Image, ImageFilter
from skimage.data import immunohistochemistry

site = Path(__file__).parent / "site"
image = Image.fromarray(immunohistochemistry())
region = (128, 128, 320, 320)
image.save(site / "reference.png")
image.paste(image.crop(region).filter(ImageFilter.GaussianBlur(3)), region[:2])
image.save(site / "defocus.png")
