/**
 * WashDog — Instagram Story Generator
 * Generates 8 ready-to-post Story images (1080×1920px)
 * One per Highlight category, matching WashDog brand.
 */

const puppeteer = require('/Users/enriqueibarra/washdog-website/node_modules/puppeteer');
const fs        = require('fs');
const path      = require('path');

const LOGO_PATH = path.join(__dirname, '../brand/washdog-social-trimmed.png');
const LOGO_B64  = 'data:image/png;base64,' + fs.readFileSync(LOGO_PATH).toString('base64');

const OUT_DIR = path.join(__dirname, 'png');
fs.mkdirSync(OUT_DIR, { recursive: true });

// Brand colors
const C = {
  charcoal: '#1F2933',
  blue:     '#2F80ED',
  yellow:   '#F2C94C',
  aqua:     '#BEE9F7',
  white:    '#FFFFFF',
};

const stories = [
  {
    slug: '1-servicios',
    bg: C.blue,
    accent: C.yellow,
    textColor: C.white,
    icon: '🐾',
    title: 'Nuestros Servicios',
    lines: [
      '🛁 Baño profesional',
      '   desde $10.000',
      '',
      '✂️ Peluquería canina',
      '   desde $20.000',
      '',
      '🚿 Autolavado',
      '   tú lo bañas, nosotros',
      '   ponemos todo',
      '',
      '🐱 Peluquería para gatos',
      '   $40.000',
    ],
    cta: 'Reserva en washdog.cl',
  },
  {
    slug: '2-peluqueria',
    bg: C.charcoal,
    accent: C.yellow,
    textColor: C.white,
    icon: '✂️',
    title: 'Peluquería Canina',
    lines: [
      'Corte profesional adaptado',
      'a la raza y pelaje de',
      'tu perro.',
      '',
      '• Corte de temporada',
      '• Corte higiénico incluido',
      '• Productos hipoalergénicos',
      '• Atención individual',
    ],
    cta: 'Agenda tu hora → washdog.cl',
  },
  {
    slug: '3-autolavado',
    bg: C.aqua,
    accent: C.blue,
    textColor: C.charcoal,
    icon: '🚿',
    title: 'Autolavado',
    lines: [
      'Tú bañas a tu perro.',
      'Nosotros ponemos todo:',
      '',
      '• Tinas profesionales',
      '• Shampoo premium',
      '• Secadores de alta potencia',
      '• Toallas incluidas',
      '',
      'Sin ensuciar tu casa.',
      'Sin mojar el baño.',
    ],
    cta: 'Disponible todo el día',
  },
  {
    slug: '4-tips',
    bg: C.yellow,
    accent: C.charcoal,
    textColor: C.charcoal,
    icon: '💡',
    title: 'Tip de la Semana',
    lines: [
      '¿Con qué frecuencia',
      'bañar a tu perro?',
      '',
      'Pelo corto: cada 4–6 semanas',
      'Pelo largo: cada 3–4 semanas',
      'Piel sensible: cada 6–8 semanas',
      '',
      'Bañarlo muy seguido reseca',
      'la piel. Espaciarlo mucho',
      'acumula suciedad y olores.',
    ],
    cta: 'Más tips → washdog.cl/newsletter',
  },
  {
    slug: '5-clientes',
    bg: C.charcoal,
    accent: C.yellow,
    textColor: C.white,
    icon: '⭐',
    title: 'Lo Dicen Nuestros Clientes',
    lines: [
      '"Mi perro salió feliz y',
      'oliendo increíble."',
      '— Catalina, Ñuñoa',
      '',
      '"Excelente atención,',
      'muy cuidadosos con mi',
      'golden retriever."',
      '— Rodrigo, Providencia',
      '',
      '"El autolavado es ideal,',
      'mis perros son enormes."',
      '— Francisca, Las Condes',
    ],
    cta: '⭐ Deja tu reseña en Google',
  },
  {
    slug: '6-faq',
    bg: C.blue,
    accent: C.white,
    textColor: C.white,
    icon: '❓',
    title: 'Preguntas Frecuentes',
    lines: [
      '¿Necesito reservar?',
      'Sí, agenda en washdog.cl',
      '',
      '¿Aceptan perros grandes?',
      'Sí, todas las razas y tamaños.',
      '',
      '¿Cuánto demora el baño?',
      'Entre 45 min y 2 hrs según raza.',
      '',
      '¿Puedo quedarme?',
      'Sí, el local es abierto.',
    ],
    cta: '📍 Av. Irarrázaval 2086-B, Ñuñoa',
  },
  {
    slug: '7-newsletter',
    bg: C.charcoal,
    accent: C.yellow,
    textColor: C.white,
    icon: '📧',
    title: 'Santiago a Cuatro Patas',
    lines: [
      'Nuestro newsletter semanal',
      'para dueños de perros',
      'en Santiago.',
      '',
      '• Tips de cuidado canino',
      '• Parques dog-friendly',
      '• Ofertas exclusivas',
      '',
      'Gratis. Cada sábado.',
      'Para dueños de perros',
      'que se preocupan de verdad.',
    ],
    cta: 'Suscríbete → washdog.cl/newsletter',
  },
  {
    slug: '8-contacto',
    bg: C.yellow,
    accent: C.charcoal,
    textColor: C.charcoal,
    icon: '📍',
    title: 'Encuéntranos',
    lines: [
      'Av. Irarrázaval 2086-B',
      'Ñuñoa, Santiago',
      '',
      '🕐 Lunes a Domingo',
      '   10:00 – 20:00',
      '',
      '📱 WhatsApp',
      '   +56 9 8723 0388',
      '',
      '🌐 washdog.cl',
      '📸 @washdogexpress',
    ],
    cta: 'Reserva tu hora online',
  },
];

function buildHTML(story) {
  const lineItems = story.lines
    .map(l => l === ''
      ? `<div style="height:18px"></div>`
      : `<div style="line-height:1.5;font-size:${l.startsWith('  ') ? '34' : '38'}px;opacity:${l.startsWith('  ') ? '0.75' : '1'}">${l.trim()}</div>`
    ).join('\n');

  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * { margin:0; padding:0; box-sizing:border-box; }
  body {
    width: 1080px; height: 1920px;
    background: ${story.bg};
    font-family: -apple-system, 'Helvetica Neue', sans-serif;
    color: ${story.textColor};
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 100px 90px;
    position: relative;
    overflow: hidden;
  }
  .bg-circle {
    position: absolute;
    border-radius: 50%;
    opacity: 0.06;
    background: ${story.textColor};
  }
  .icon {
    font-size: 160px;
    margin-bottom: 48px;
    line-height: 1;
  }
  .title {
    font-size: 72px;
    font-weight: 900;
    letter-spacing: -1px;
    color: ${story.accent};
    margin-bottom: 56px;
    text-align: center;
    line-height: 1.1;
  }
  .lines {
    font-size: 38px;
    font-weight: 500;
    text-align: left;
    width: 100%;
    max-width: 860px;
    line-height: 1.55;
  }
  .divider {
    width: 80px;
    height: 6px;
    background: ${story.accent};
    border-radius: 3px;
    margin: 56px auto;
  }
  .cta {
    font-size: 40px;
    font-weight: 800;
    color: ${story.accent};
    text-align: center;
    margin-top: 64px;
    padding: 28px 48px;
    border: 4px solid ${story.accent};
    border-radius: 60px;
    letter-spacing: 0.02em;
  }
  .brand {
    position: absolute;
    bottom: 72px;
    width: 180px;
    height: 180px;
    border-radius: 50%;
    object-fit: cover;
    opacity: 0.9;
    filter: ${story.bg === '#F2C94C' || story.bg === '#BEE9F7' ? 'none' : 'drop-shadow(0 0 10px rgba(255,255,255,0.2))'};
  }
</style>
</head>
<body>
  <div class="bg-circle" style="width:900px;height:900px;top:-200px;right:-200px;"></div>
  <div class="bg-circle" style="width:500px;height:500px;bottom:-100px;left:-150px;"></div>
  <div class="icon">${story.icon}</div>
  <div class="title">${story.title}</div>
  <div class="lines">${lineItems}</div>
  <div class="divider"></div>
  <div class="cta">${story.cta}</div>
  <img class="brand" src="${LOGO_B64}" alt="Washdog">
</body>
</html>`;
}

(async () => {
  const browser = await puppeteer.launch({ headless: 'new' });
  const page    = await browser.newPage();
  await page.setViewport({ width: 1080, height: 1920, deviceScaleFactor: 1 });

  for (const story of stories) {
    const html    = buildHTML(story);
    const outPath = path.join(OUT_DIR, `${story.slug}.png`);
    await page.setContent(html, { waitUntil: 'load' });
    await page.screenshot({ path: outPath, fullPage: false });
    console.log(`✅ ${story.slug}.png`);
  }

  await browser.close();
  console.log(`\nDone! Stories saved to: ${OUT_DIR}`);
})();
