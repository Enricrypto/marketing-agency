# WashDog — Instagram Visual System

Complete programmatic social media branding system.

---

## Folder Structure

```
social_assets/
├── icons/
│   ├── highlight-icons/
│   │   └── _preview.html       ← 8 highlight icons (Servicios, Autolavado, etc.)
│   └── content-icons/
│       └── _preview.html       ← 6 content category icons
│
├── templates/
│   ├── post/
│   │   ├── post-tip.html       ← Dog Tip (text + image variant)
│   │   ├── post-park.html      ← Park Recommendation
│   │   ├── post-service.html   ← Service Explanation
│   │   └── post-client.html    ← Client Feature
│   └── carousel/
│       └── carousel-tip.html   ← 5-slide carousel (adaptable to any topic)
│
├── styles/
│   ├── brand.css               ← Colors, gradients, bubble patterns, components
│   └── typography.css          ← Font scale (Poppins + Inter)
│
├── hashtags/
│   └── hashtags.json           ← 3 rotating sets + grouped library
│
└── captions/
    └── caption-templates.md    ← 5 caption frameworks + hooks + guidelines
```

---

## Color Palette

| Token      | Hex       | Use                          |
|------------|-----------|------------------------------|
| Blue       | `#2F80ED` | Primary, CTAs, dark sections |
| Yellow     | `#F2C94C` | Accents, highlights, CTA pills |
| Aqua       | `#BEE9F7` | Water theme, light backgrounds |
| Charcoal   | `#1F2933` | Text, dark sections          |
| White      | `#FFFFFF` | Backgrounds, text on dark    |

## Fonts

| Role      | Font    | Weight    |
|-----------|---------|-----------|
| Headlines | Poppins | 700–900   |
| Body      | Inter   | 400–600   |

---

## Instagram Bio (SEO-optimized)

```
🐶 Peluquería y autolavado para perros
🚿 Báñalo tú mismo · 30 min

📍 Ñuñoa — Irarrázaval 2086-B
📬 Newsletter: Santiago a Cuatro Patas

⬇️ washdog.cl
```

Keywords covered: peluquería canina, autolavado perros, Ñuñoa, Santiago

---

## Content Grid Pattern (Instagram)

Repeat this 9-post cycle:

| Tip           | Cliente       | Servicio      |
|---------------|---------------|---------------|
| Parque        | Carrusel      | Comunidad     |
| Servicio      | Tip           | Newsletter    |

---

## Export Templates to PNG (for Instagram upload)

### Option 1 — Chrome (manual)
1. Open the HTML file in Chrome
2. DevTools → Toggle Device Toolbar (`Cmd+Shift+M`)
3. Set to **1080 × 1080**
4. Right-click → **Capture full size screenshot**

### Option 2 — CLI (automated, recommended)
```bash
# Install
npm install -g capture-website-cli

# Export all posts
capture-website templates/post/post-tip.html     --width=1080 --height=1080 --output=exports/post-tip.png
capture-website templates/post/post-park.html    --width=1080 --height=1080 --output=exports/post-park.png
capture-website templates/post/post-service.html --width=1080 --height=1080 --output=exports/post-service.png
capture-website templates/post/post-client.html  --width=1080 --height=1080 --output=exports/post-client.png

# Export carousel slides (each)
capture-website templates/carousel/carousel-tip.html --width=1080 --height=1080 --output=exports/carousel-tip-all.png
```

### Option 3 — Python (integrate with Marketing OS)
```python
import subprocess

def export_template(html_path: str, output_path: str, width=1080, height=1080):
    subprocess.run([
        "capture-website", html_path,
        f"--width={width}", f"--height={height}",
        f"--output={output_path}"
    ])
```

### Option 4 — Puppeteer (Node.js, most reliable)
```javascript
const puppeteer = require('puppeteer')

async function exportSlide(htmlPath, outputPath) {
  const browser = await puppeteer.launch()
  const page = await browser.newPage()
  await page.setViewport({ width: 1080, height: 1080, deviceScaleFactor: 2 }) // 2x = 2160px Retina
  await page.goto(`file://${htmlPath}`)
  await page.screenshot({ path: outputPath, type: 'png' })
  await browser.close()
}
```

---

## Highlight Icons — How to Upload

1. Open `icons/highlight-icons/_preview.html` in Chrome
2. DevTools → 1080×1080 viewport
3. Screenshot each circular icon
4. Crop to 1:1 square
5. In Instagram → Profile → Highlights → Edit Cover → Upload

---

## Content Pillar Definitions

| Pillar            | Frequency   | Format        | Goal                        |
|-------------------|-------------|---------------|-----------------------------|
| Dog Tip           | 2× / week   | Carousel      | Saves + authority           |
| Parque/Café       | 1× / week   | Single post   | Shares + newsletter funnel  |
| Cliente           | 1× / week   | Single post   | Trust + engagement          |
| Servicio          | 1× / week   | Single/Reel   | Conversion                  |
| Newsletter promo  | 1× / week   | Story + post  | Subscriber growth           |

---

## Newsletter → Instagram Automation Flow

The existing `run_newsletter.py` already extracts:
- `sections["lugar"]` → Park Recommendation post
- `sections["tip"]`   → Dog Tip post
- `sections["evento"]`→ Community/Event post

The `instagram.py` module in `newsletter/` handles posting.
Extend it to render HTML templates with injected content → screenshot → post.
