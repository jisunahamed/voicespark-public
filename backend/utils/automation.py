import os
import os
import logging
import re
import subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
from urllib.parse import urljoin
from collections import Counter
# os.environ["PLAYWRIGHT_BROWSERS_PATH"] = '/vercel/.cache/ms-playwright/'
from .chatbot import ChatGPT
from bs4 import BeautifulSoup, Comment
import re
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
]


def launch_browser(playwright):
    launch_options = {
        "headless": True,
        "args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
        ],
    }

    for browser_path in CHROME_PATHS:
        if os.path.exists(browser_path):
            return playwright.chromium.launch(executable_path=browser_path, **launch_options)

    return playwright.chromium.launch(**launch_options)


def get_logos(page, link):
    images_logo = []
    elements = page.locator("xpath=//header//img | //nav//img | //*[contains(translate(@class,'LOGO','logo'),'logo')]//img | //*[contains(translate(@id,'LOGO','logo'),'logo')]//img | //img[contains(translate(@alt,'LOGO','logo'),'logo')]"
            ).all()
    for element in elements:
        src = element.get_attribute("src")
        if src:
            full_url = urljoin(link, src)
            attrs = " ".join(filter(None, [
                src,
                element.get_attribute("alt"),
                element.get_attribute("class"),
                element.get_attribute("id"),
            ])).lower()
            if 'logo' in attrs:
                images_logo.append(full_url)
    icon_hrefs = page.evaluate("""
        () => [...document.querySelectorAll("link[rel*='icon'], link[rel='apple-touch-icon']")]
            .map(el => el.href)
            .filter(Boolean)
    """)
    images_logo.extend(icon_hrefs)
    if images_logo:
        return list(dict.fromkeys(images_logo[:3]))
    else:
        return []

def extract_brand_style(page, link, logos):
    style_data = page.evaluate("""
        () => {
            const colorProps = [
                "color",
                "backgroundColor",
                "borderTopColor",
                "borderRightColor",
                "borderBottomColor",
                "borderLeftColor"
            ];
            const colors = [];
            const fonts = [];
            const elements = [
                document.body,
                ...document.querySelectorAll("header, nav, main, section, footer, h1, h2, h3, p, a, button, [class*='brand'], [class*='hero']")
            ].filter(Boolean).slice(0, 300);
            for (const el of elements) {
                const style = window.getComputedStyle(el);
                for (const prop of colorProps) {
                    const value = style[prop];
                    if (value && value !== "rgba(0, 0, 0, 0)" && value !== "transparent") {
                        colors.push(value);
                    }
                }
                if (style.fontFamily) fonts.push(style.fontFamily);
            }
            const metaTheme = document.querySelector("meta[name='theme-color']")?.content;
            if (metaTheme) colors.push(metaTheme);
            return { colors, fonts };
        }
    """)
    return {
        "logos": [{"url": url, "source": "website"} for url in logos],
        "colors": normalize_colors(style_data.get("colors", [])),
        "fonts": normalize_fonts(style_data.get("fonts", [])),
        "visual_identity": "",
        "visual_style": {"label": "Website Inspired", "image_url": ""},
    }

def normalize_colors(values):
    colors = []
    for value in values:
        if not value:
            continue
        value = value.strip()
        hex_match = re.fullmatch(r"#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})", value)
        if hex_match:
            colors.append(expand_hex(value).upper())
            continue
        rgb_match = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", value)
        if rgb_match:
            r, g, b = [max(0, min(255, int(part))) for part in rgb_match.groups()]
            if (r, g, b) not in {(255, 255, 255), (0, 0, 0)}:
                colors.append(f"#{r:02X}{g:02X}{b:02X}")
    ranked = [color for color, _ in Counter(colors).most_common()]
    result = []
    for color in ranked:
        if color not in result:
            result.append(color)
        if len(result) == 8:
            break
    return result

def expand_hex(value):
    value = value.lstrip("#")
    if len(value) == 3:
        value = "".join(ch * 2 for ch in value)
    return f"#{value}"

def normalize_fonts(values):
    fonts = []
    for value in values:
        family = value.split(",")[0].strip().strip('"').strip("'")
        if family and family.lower() not in {"serif", "sans-serif", "monospace", "system-ui"}:
            fonts.append(family)
    ranked = [font for font, _ in Counter(fonts).most_common()]
    title = ranked[0] if ranked else "Inter"
    body = ranked[1] if len(ranked) > 1 else title
    return [
        {"role": "title", "family": title, "weight": "Bold"},
        {"role": "body", "family": body, "weight": "Regular"},
    ]

def get_images(page, first_name, last_name, link):
    images = []
    # images_logo = []
    # elements = page.locator("xpath=//header//img | //nav//img | //*[contains(@class,'logo')]//img | //*[contains(@id,'logo')]//img"
    #         )
    # for element in elements:
    #     src = element.get_attribute("src")
    #     if src:
    #         full_url = urljoin(link, src)
    #         if 'logo' in src:
    #             images.append(full_url)
    # print('logo image', images)
    for img in page.query_selector_all("img"):
        src = img.get_attribute("src")
        if src:
            full_url = urljoin(link, src)
            attrs = img.evaluate("el => Array.from(el.attributes).map(a => a.value)")
            if any(first_name.lower() in val.lower() and last_name.lower() in val.lower() for val in attrs):
                images.append(full_url)
            # if 'logo' in src and 'http' not in src:
            #     images_logo.append(full_url)
    return images

def scrape_page(page, link):
    page.goto(link, wait_until="domcontentloaded", timeout=30000)
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except:
        pass
    html = page.content()
    return html, page
    pass


def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")

    # Remove unwanted tags entirely
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    # Get only text nodes, stripping all tags
    texts = soup.find_all(string=True)

    # Clean up
    lines = [t.strip() for t in texts]
    clean = "\n".join(line for line in lines if line)

    return clean

def fix_url(url):
    url = url.strip()
    parsed = urlparse(url)
    if not parsed.scheme:
        url = "https://" + url
    return url


def same_site_url(candidate, base_url):
    candidate_host = urlparse(candidate).netloc.lower().removeprefix("www.")
    base_host = urlparse(base_url).netloc.lower().removeprefix("www.")
    return candidate_host == base_host


def pick_info_links(hrefs):
    priority_terms = (
        "about",
        "company",
        "contact",
        "services",
        "solution",
        "pricing",
        "portfolio",
        "case",
    )
    ranked = []
    for href in hrefs:
        lower_href = href.lower()
        score = sum(1 for term in priority_terms if term in lower_href)
        if score:
            ranked.append((score, href))
    ranked.sort(key=lambda item: (-item[0], len(item[1])))
    return [href for _, href in ranked[:3]]

def analyse_link(link, first_name = 'samiul', last_name = 'ehsan'):
    # result = subprocess.run(
    #     ["python", "-m", "playwright", "install", "--dry-run"],
    #     capture_output=True,
    #     text=True
    # )
    #
    # # Extract the cache path from the output
    # for line in result.stdout.split('\n'):
    #     if 'Install location:' in line:
    #         path = line.split('Install location:')[1].strip()
    #         # Go up to the ms-playwright folder
    #         browsers_path = os.path.dirname(path)
    #         os.environ["PLAYWRIGHT_BROWSERS_PATH"] = browsers_path
    #         break
    fixed_link = fix_url(link)
    browser = None
    with sync_playwright() as p:
        browser = launch_browser(p)
        page = browser.new_page()
        page.goto(fixed_link, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except:
            pass
        # print(page.content())
        hrefs = page.evaluate("""
                              () => [...new Set(
                                  [...document.querySelectorAll(`
                    header a[href],
                    nav a[href],
                    footer a[href],
                    [class*='header'] a[href],
                    [class*='navbar'] a[href],
                    [class*='footer'] a[href],
                    [id*='header'] a[href],
                    [id*='footer'] a[href]
                `)]
                                      .map(el => el.href)
                              )]
                              """)
        hrefs = list(set(hrefs))
        hrefs = [
            hr for hr in hrefs
            if same_site_url(hr, fixed_link) and hr.rstrip("/") != fixed_link.rstrip("/") and "#" not in hr
        ]
        hrefs = pick_info_links(hrefs)
        html = page.content()
        text = extract_text(html)
        # print(hrefs)
        screenshot_bytes = page.screenshot(full_page=False)
        html_list = [text]


        logos = get_logos(page, fixed_link)
        brand_style = extract_brand_style(page, fixed_link, logos)
        images = get_images(page, first_name, last_name, fixed_link) + logos
        context = browser.new_context()
        context.clear_cookies()  # clear all cookies before loading
        page.close()
        page = context.new_page()
        for hrs in hrefs:
            try:
                html, page = scrape_page(page, hrs)
                text = extract_text(html)
                html_list.append(text)
                html_list = list(set(html_list))
                images = list(set(images + get_images(page, first_name, last_name, fixed_link)))
            except Exception as exc:
                print('additional page scrape failed', hrs, type(exc).__name__)
        # for img in page.query_selector_all("img"):
        #     src = img.get_attribute("src")
        #     if src:
        #         full_url = urljoin(link, src)
        #         attrs = img.evaluate("el => Array.from(el.attributes).map(a => a.value)")
        #         if any(first_name.lower() in val.lower() and last_name.lower() in val.lower() for val in attrs):
        #             images.append(full_url)
        #         if 'logo' in full_url:
        #             images.append(full_url)
                # print('got one', img)

        logger.debug("website analysis extracted %s images and %s html chars", len(images), len(''.join(html_list)))
        browser.close()
        return {'html':''.join(html_list), 'images':images, 'screenshot':screenshot_bytes, "additional_links":hrefs, "brand_style":brand_style}
if __name__ == '__main__':
    analyse_link('https://www.udemy.com/')
