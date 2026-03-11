/**
 * WashDog — AI Post Generator
 * Drives the Instagram editor programmatically via Puppeteer.
 *
 * Usage:
 *   node generate_post.js --cat info --style 1 \
 *     --badge "Anuncio" \
 *     --headline "¡Ven cuando quieras, sin reserva!" \
 *     --hl "sin reserva" \
 *     --subtitle "Autolavado sin necesidad de reservar 🐾" \
 *     --note "Servicio de peluquería sólo con reserva" \
 *     --url "www.washdog.cl" \
 *     --out /tmp/post.png
 *
 *   # With a photo (for templates that have a drop zone):
 *   node generate_post.js --cat info --style 3 --photo /path/to/photo.jpg --out /tmp/post.png
 */

const puppeteer = require('/Users/enriqueibarra/washdog-website/node_modules/puppeteer');
const path      = require('path');
const fs        = require('fs');

// ── Parse CLI args ────────────────────────────────────────────────────────────
const args = {};
process.argv.slice(2).forEach((a, i, arr) => {
  if (a.startsWith('--')) args[a.slice(2)] = arr[i + 1] ?? true;
});

const EDITOR_PATH = path.resolve(
  '/Users/enriqueibarra/washdog-website/public/tools/editor-app.html'
);
const OUT_PATH = args.out || `/tmp/washdog-post-${Date.now()}.png`;

// Fields to fill (only those provided via CLI)
const FIELD_IDS = ['badge','headline','hl','subtitle','note','url',
                   'name','loc','body','chips','meta','quote',
                   'step1','sub1','step2','sub2','step3','sub3'];

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page    = await browser.newPage();

  // Load editor directly (no auth gate on static file)
  await page.goto(`file://${EDITOR_PATH}`, { waitUntil: 'networkidle0' });
  await new Promise(r => setTimeout(r, 600));

  // ── 1. Set category ─────────────────────────────────────────────────────────
  if (args.cat) {
    await page.evaluate((cat) => {
      const btn = [...document.querySelectorAll('.cat-btn')]
        .find(b => b.getAttribute('onclick')?.includes(`'${cat}'`));
      if (btn) btn.click();
    }, args.cat);
    await new Promise(r => setTimeout(r, 200));
  }

  // ── 2. Set style ─────────────────────────────────────────────────────────────
  if (args.style) {
    await page.evaluate((s) => setStyle(parseInt(s)), args.style);
    await new Promise(r => setTimeout(r, 200));
  }

  // ── 3. Fill fields ───────────────────────────────────────────────────────────
  for (const id of FIELD_IDS) {
    if (args[id] !== undefined) {
      await page.evaluate((fieldId, value) => {
        const el = document.querySelector(`[data-field="${fieldId}"]`);
        if (el) {
          el.value = value;
          el.dispatchEvent(new Event('input', { bubbles: true }));
        }
      }, id, args[id]);
    }
  }
  await new Promise(r => setTimeout(r, 300));

  // ── 4. Inject photo into drop zone (if provided) ─────────────────────────────
  if (args.photo) {
    const photoB64 = 'data:image/jpeg;base64,' +
      fs.readFileSync(path.resolve(args.photo)).toString('base64');
    const zoneId = args.zone || args.cat; // default zone = category name
    await page.evaluate((zid, b64) => {
      images[zid] = b64;
      renderPost();
    }, zoneId, photoB64);
    await new Promise(r => setTimeout(r, 300));
  }

  // ── 5. Capture via html2canvas (same as the export button) ────────────────────
  const dataUrl = await page.evaluate(async () => {
    const el = document.querySelector('.post');
    const canvas = await html2canvas(el, {
      scale: 2,
      useCORS: true,
      allowTaint: true,
      backgroundColor: null,
      logging: false,
    });
    return canvas.toDataURL('image/png');
  });

  // ── 6. Save PNG ───────────────────────────────────────────────────────────────
  const base64 = dataUrl.replace(/^data:image\/png;base64,/, '');
  fs.mkdirSync(path.dirname(OUT_PATH), { recursive: true });
  fs.writeFileSync(OUT_PATH, Buffer.from(base64, 'base64'));

  await browser.close();
  console.log(`[post] ✓ Saved: ${OUT_PATH}`);
})();
