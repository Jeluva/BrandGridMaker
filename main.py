import os
import time
import requests
from io import BytesIO
from PIL import Image
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import StaleElementReferenceException

# ————— CONFIGURACIÓN —————
# Estilo de búsqueda refinado: street style casual urbano skater
SEARCH_PREFIX = "streetwear"
BASE_BRANDS = ["Broken Planet","Maison Margiela","Trapstar","Stone Island","Prada","Casablanca","Acne Studios","Gallery Dept","Nike Tech","Amiri","Stussy", "Louis Vuitton", "Denim Tears", "Chrome Hearts","Syna World","Corteiz","Bape","Polo Ralph Lauren","Dior","Fear of God Essentials","Supreme","Balenciaga","sp5der","Burberry"]
BRANDS = [f"{SEARCH_PREFIX} {b}" for b in BASE_BRANDS]
IMAGES_PER_BRAND = 4
GRID_COLS = 2
GRID_ROWS = 2
THUMB_SIZE = (540, 540)
OUTPUT_DIR = "grids"
SEARCH_SCROLLS = 10
# TikTok vertical 9:16
TARGET_SIZE = (1080, 1920)
# Archivo para evitar repeticiones
USED_URLS_FILE = "used_urls.txt"

# Carga URLs ya usadas
if os.path.exists(USED_URLS_FILE):
    with open(USED_URLS_FILE, "r") as f:
        used_urls = set(line.strip() for line in f)
else:
    used_urls = set()

# Inicia Selenium en headless
def setup_driver():
    opts = Options()
    opts.add_argument("--headless")
    return webdriver.Chrome(options=opts)

# Extrae URLs de pines con la mayor resolución y filtra usados
def fetch_pinterest_images(driver, query, count):
    url = f"https://www.pinterest.com/search/pins/?q={query.replace(' ', '%20')}"
    driver.get(url)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "img[srcset]"))
    )
    urls = []
    scrolls = 0
    while len(urls) < count and scrolls < SEARCH_SCROLLS:
        imgs = driver.find_elements(By.CSS_SELECTOR, "img[srcset]")
        for img in imgs:
            try:
                srcset = img.get_attribute("srcset")
            except StaleElementReferenceException:
                continue
            if not srcset:
                continue
            # Selecciona la URL más grande
            entries = [e.strip().split(' ') for e in srcset.split(',')]
            high_res = entries[-1][0]
            if high_res not in urls and high_res not in used_urls:
                urls.append(high_res)
                if len(urls) >= count:
                    break
        driver.execute_script("window.scrollBy(0, window.innerHeight);")
        scrolls += 1
        time.sleep(1)
    return urls[:count]

# Descarga y redimensiona

def download_and_resize(url, size):
    resp = requests.get(url, timeout=10)
    img = Image.open(BytesIO(resp.content)).convert("RGB")
    return img.resize(size, resample=Image.LANCZOS)

# Construye grid

def build_grid(images, cols, rows, thumb_size):
    w, h = cols * thumb_size[0], rows * thumb_size[1]
    grid = Image.new("RGB", (w, h), (30,30,30))
    for idx, img in enumerate(images):
        x = (idx % cols) * thumb_size[0]
        y = (idx // cols) * thumb_size[1]
        grid.paste(img, (x, y))
    return grid

# Script principal
if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    driver = setup_driver()

    for brand_query, base in zip(BRANDS, BASE_BRANDS):
        print(f"🔍 Buscando {IMAGES_PER_BRAND} imágenes de {base} ({brand_query})...")
        candidates = fetch_pinterest_images(driver, brand_query, IMAGES_PER_BRAND * 2)
        thumbs = []
        selected = []
        for url in candidates:
            try:
                resp = requests.get(url, timeout=10)
                img = Image.open(BytesIO(resp.content)).convert("RGB")
            except Exception:
                continue
            w, h = img.size
            # Solo vertical, sin asegurar rostros ni texto
            if h > w:
                thumbs.append(img.resize(THUMB_SIZE, resample=Image.LANCZOS))
                selected.append(url)
                if len(thumbs) >= IMAGES_PER_BRAND:
                    break

        # Completar
        while len(thumbs) < IMAGES_PER_BRAND:
            thumbs.append(thumbs[-1].copy())

        print("🎨 Creando grid para", base)
        grid = build_grid(thumbs, GRID_COLS, GRID_ROWS, THUMB_SIZE)
        final = grid.resize(TARGET_SIZE, resample=Image.LANCZOS)

        filename = base.replace(" ", "_")
        out_path = os.path.join(OUTPUT_DIR, f"{filename}.png")
        final.save(out_path)
        print("✅ Guardado:", out_path)

        # Registrar usados
        used_urls.update(selected)

    driver.quit()
    # Guardar archivo de usados
    with open(USED_URLS_FILE, "w") as f:
        for u in used_urls:
            f.write(u + "\n")

