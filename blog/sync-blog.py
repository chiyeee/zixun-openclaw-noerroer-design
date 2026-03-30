#!/usr/bin/env python3
"""
Nexscope Blog Sync Script v3
- Generates article HTML from markdown (100% template parity)
- Auto-updates homepage article grid
- Auto-updates corresponding category page
- Auto-updates corresponding author page

Usage:
    python3 sync-blog.py                    # Sync all articles
    python3 sync-blog.py article-slug.md    # Sync specific article
"""

import os, re, sys, yaml, markdown
from datetime import datetime
from html import escape

SOURCE_DIR = "/tmp/ns-blog-preview"
TARGET_DIR = "/tmp/template-repo/blog"
TEMPLATE_FILE = os.path.join(TARGET_DIR, "product-research-7-methods.html")

# ─── Author Mapping ───
AUTHORS = {
    "Henk Nie": {
        "avatar_html": '<div class="author-avatar" style="padding:0;overflow:hidden"><img src="images/authors/henk-nie.jpg" alt="Henk Nie" style="width:100%;height:100%;object-fit:cover;border-radius:50%"></div>',
        "page": "final-author-henk-nie.html",
    },
    "Nexscope Team": {
        "avatar_html": '<div class="author-avatar" style="padding:0;overflow:hidden;background:white"><img src="images/authors/nexscope-team.png" alt="Nexscope Team" style="width:100%;height:100%;object-fit:contain;border-radius:50%"></div>',
        "page": "final-author.html",
    },
    "Zhiyi Wu": {
        "avatar_html": '<div class="author-avatar" style="padding:0;overflow:hidden"><img src="images/authors/zhiyi-wu.jpg" alt="Zhiyi Wu" style="width:100%;height:100%;object-fit:cover;border-radius:50%"></div>',
        "page": "final-author-zhiyi-wu.html",
    },
}

# ─── Category → Page Link ───
CATEGORY_LINKS = {
    "Product Research": "final-category-product-research.html",
    "PPC & Ads": "final-category-ppc.html",
    "Listing Optimization": "final-category-listing.html",
    "Profit & FBA": "final-category-profit.html",
    "Sourcing & Supply": "final-category-sourcing.html",
    "Market Intelligence": "final-category-market.html",
    "AI for Amazon Sellers": "final-category-ai.html",
    "AI for Ecommerce": "final-category-ai.html",
    "AI & Automation": "final-category-ai.html",
    "Tool Reviews": "final-category-tools.html",
    "Seller Guides": "final-category-guides.html",
    "Nexscope News": "final-category-news.html",
}

# ─── Category Tag Colors (for author/category pages with inline style) ───
CATEGORY_COLORS = {
    "Product Research": {"bg": "#EFF6FF", "color": "#3B82F6"},
    "PPC & Ads": {"bg": "#F5F3FF", "color": "#7C3AED"},
    "Listing Optimization": {"bg": "#ECFDF5", "color": "#059669"},
    "Profit & FBA": {"bg": "#FFFBEB", "color": "#D97706"},
    "Sourcing & Supply": {"bg": "#FEF2F2", "color": "#DC2626"},
    "Market Intelligence": {"bg": "#ECFEFF", "color": "#0891B2"},
    "AI & Automation": {"bg": "#EEF2FF", "color": "#4F46E5"},
    "AI for Amazon Sellers": {"bg": "#EEF2FF", "color": "#4F46E5"},
    "AI for Ecommerce": {"bg": "#EEF2FF", "color": "#4F46E5"},
    "Tool Reviews": {"bg": "#FDF2F8", "color": "#DB2777"},
    "Seller Guides": {"bg": "#FFFBEB", "color": "#B45309"},
    "Nexscope News": {"bg": "#EFF6FF", "color": "#3B82F6"},
}

# ─── CTA Text ───
CTA_MAP = {
    "Product Research": ("Find your winning niche in minutes", "Discover high-opportunity products with proven research methods", "Start Your Research Now →"),
    "Seller Guides": ("Start selling smarter today", "AI-powered insights to launch and grow your ecommerce business", "Get Started Free →"),
    "AI for Amazon Sellers": ("Automate your Amazon workflow", "AI-powered tools to save hours on research, listing, and optimization", "Try Nexscope Free →"),
    "AI for Ecommerce": ("Automate your Amazon workflow", "AI-powered tools to save hours on research, listing, and optimization", "Try Nexscope Free →"),
    "AI & Automation": ("Automate your Amazon workflow", "AI-powered tools to save hours on research, listing, and optimization", "Try Nexscope Free →"),
}


# ═══════════════════════════════════════════════════════════
# MARKDOWN → HTML CONVERSION
# ═══════════════════════════════════════════════════════════

def parse_frontmatter(content):
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return yaml.safe_load(parts[1]), parts[2].strip()
    return {}, content


def md_to_html(md_text, cover_image=""):
    html = markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'toc'])
    # Remove ALL H1 tags
    html = re.sub(r'<h1[^>]*>.*?</h1>\s*', '', html)
    # Remove "Table of Contents" H2 + content until next real H2
    html = re.sub(r'<h2[^>]*>Table of Contents</h2>.*?(?=<h2[^>]*>(?!Table))', '', html, flags=re.DOTALL)
    # Remove cover image duplicates
    if cover_image:
        ce = re.escape(cover_image)
        html = re.sub(r'<p>\s*<img[^>]*src="' + ce + r'"[^>]*/?\s*>\s*</p>\s*', '', html)
        html = re.sub(r'<img[^>]*src="' + ce + r'"[^>]*/?\s*>\s*', '', html)
    # Add IDs to h2 tags
    def add_h2_id(m):
        text = re.sub(r'<[^>]+>', '', m.group(1))
        slug = re.sub(r'[^\w\s-]', '', text.lower()).strip()
        slug = re.sub(r'\s+', '-', slug)
        return f'<h2 id="{slug}">{m.group(1)}</h2>'
    html = re.sub(r'<h2>(.*?)</h2>', add_h2_id, html)
    return html


def calc_read_time(html):
    text = re.sub(r'<[^>]+>', ' ', html)
    return max(1, round(len(text.split()) / 238))


def extract_faqs(md_text):
    faq_section = re.search(r'##\s*(?:FAQ|Frequently Asked Questions)(.*?)(?=\n## |\Z)', md_text, re.DOTALL | re.IGNORECASE)
    if not faq_section:
        return []
    text = faq_section.group(1)
    pairs = re.findall(r'###\s*(.*?)\n\n(.*?)(?=\n###|\Z)', text, re.DOTALL)
    faqs = []
    for q, a in pairs:
        q = q.strip()
        a = re.sub(r'\*\*(.*?)\*\*', r'\1', a.strip())
        a = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', a)
        a_first = a.split('\n\n')[0].replace('\n', ' ').strip()
        if q and a_first:
            faqs.append({"q": q, "a": a_first})
    return faqs


def build_faq_schema(faqs):
    if not faqs:
        return ""
    entities = []
    for faq in faqs:
        q = faq['q'].replace('"', '\\"')
        a = faq['a'].replace('"', '\\"')
        entities.append(f'        {{"@type": "Question", "name": "{q}", "acceptedAnswer": {{"@type": "Answer", "text": "{a}"}}}}')
    joined = ",\n".join(entities)
    return f'''
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": [
{joined}
      ]
    }}
    </script>'''


def build_article_schema(meta, author_name, author_page):
    title = meta.get('title', '').replace('"', '\\"')
    desc = meta.get('description', '').replace('"', '\\"')
    img = meta.get('og:image', '')
    pub = meta.get('date', '2026-03-27')
    mod = meta.get('lastUpdated', pub)
    return f'''
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "Article",
      "headline": "{title}",
      "description": "{desc}",
      "image": "{img}",
      "author": {{
        "@type": "Person",
        "name": "{author_name}",
        "url": "https://chiyeee.github.io/zixun-openclaw-noerroer-design/blog/{author_page}"
      }},
      "publisher": {{
        "@type": "Organization",
        "name": "Nexscope",
        "logo": {{ "@type": "ImageObject", "url": "https://www.nexscope.ai/logo.png" }}
      }},
      "datePublished": "{pub}T00:00:00Z",
      "dateModified": "{mod}T00:00:00Z",
      "mainEntityOfPage": {{ "@type": "WebPage" }}
    }}
    </script>'''


# ═══════════════════════════════════════════════════════════
# ARTICLE CARD HTML GENERATORS
# ═══════════════════════════════════════════════════════════

def make_homepage_card(article):
    """Card for homepage (no inline tag color, uses CSS)."""
    return f'''            <a href="{article["filename"]}" class="article-card" data-title="{escape(article["title"])}">
                <img src="{article["og_image"]}" alt="{escape(article["category"])}">
                <div class="article-card-content">
                    <span class="article-tag">{escape(article["category"])}</span>
                    <h3>{escape(article["title"])}</h3>
                    <div class="article-card-meta">
                        <span>{article["display_date"]}</span> · <span>{article["read_time"]} min read</span>
                    </div>
                    <div class="article-card-readmore">Read Now →</div>
                </div>
            </a>'''


def make_category_card(article):
    """Card for category pages (no inline tag color)."""
    return f'''            <a href="{article["filename"]}" class="article-card">
                <img src="{article["og_image"]}" alt="{escape(article["category"])}">
                <div class="article-card-content">
                    <span class="article-tag">{escape(article["category"])}</span>
                    <h3>{escape(article["title"])}</h3>
                    <div class="article-card-meta">{article["display_date"]} · {article["read_time"]} min read</div>
                </div>
            </a>'''


def make_author_card(article):
    """Card for author pages (with inline tag color)."""
    colors = CATEGORY_COLORS.get(article["category"], {"bg": "#EFF6FF", "color": "#3B82F6"})
    return f'''            <a href="{article["filename"]}" class="article-card">
                <img src="{article["og_image"]}" alt="{escape(article["category"])}">
                <div class="article-card-content">
                    <span class="article-tag" style="background:{colors["bg"]};color:{colors["color"]}">{escape(article["category"])}</span>
                    <h3>{escape(article["title"])}</h3>
                    <div class="article-card-meta">{article["display_date"]} · {article["read_time"]} min read</div>
                </div>
            </a>'''


# ═══════════════════════════════════════════════════════════
# PAGE UPDATERS
# ═══════════════════════════════════════════════════════════

def _card_already_exists(page_html, filename):
    """Check if an article card already exists on a page."""
    return f'href="{filename}"' in page_html


def _insert_card_replacing_placeholder(page_html, new_card_html):
    """Replace the LAST placeholder card (href="#") with the new real card.
    If no placeholder left, prepend to grid (newest first)."""
    
    # Find all placeholder cards (href="#")
    placeholder_pattern = r'            <a href="#" class="article-card">\s*<img src="https://via\.placeholder\.com[^"]*"[^>]*>\s*<div class="article-card-content">.*?</div>\s*</a>'
    placeholders = list(re.finditer(placeholder_pattern, page_html, re.DOTALL))
    
    if placeholders:
        # Replace the FIRST placeholder (top of grid = most visible)
        first = placeholders[0]
        page_html = page_html[:first.start()] + new_card_html + page_html[first.end():]
        return page_html
    
    # No placeholders left — prepend after <div class="articles-grid">
    grid_match = re.search(r'(<div class="articles-grid"[^>]*>)\s*\n', page_html)
    if grid_match:
        insert_pos = grid_match.end()
        page_html = page_html[:insert_pos] + new_card_html + "\n" + page_html[insert_pos:]
    
    return page_html


def update_homepage(article):
    """Add article card to homepage, replacing a placeholder."""
    hp_path = os.path.join(TARGET_DIR, "final-index.html")
    with open(hp_path) as f:
        html = f.read()
    
    if _card_already_exists(html, article["filename"]):
        print(f"    📌 Homepage: already has {article['filename']}")
        return
    
    card = make_homepage_card(article)
    html = _insert_card_replacing_placeholder(html, card)
    
    with open(hp_path, 'w') as f:
        f.write(html)
    print(f"    📌 Homepage: added card")


def update_category_page(article):
    """Add article card to the corresponding category page."""
    cat_page = CATEGORY_LINKS.get(article["category"])
    if not cat_page:
        print(f"    ⚠️  No category page for: {article['category']}")
        return
    
    cp_path = os.path.join(TARGET_DIR, cat_page)
    if not os.path.exists(cp_path):
        print(f"    ⚠️  Category page not found: {cat_page}")
        return
    
    with open(cp_path) as f:
        html = f.read()
    
    if _card_already_exists(html, article["filename"]):
        print(f"    📂 Category ({cat_page}): already has {article['filename']}")
        return
    
    card = make_category_card(article)
    html = _insert_card_replacing_placeholder(html, card)
    
    with open(cp_path, 'w') as f:
        f.write(html)
    print(f"    📂 Category ({cat_page}): added card")


def update_author_page(article):
    """Add article card to the corresponding author page."""
    author_info = AUTHORS.get(article["author"])
    if not author_info:
        print(f"    ⚠️  No author config for: {article['author']}")
        return
    
    ap_path = os.path.join(TARGET_DIR, author_info["page"])
    if not os.path.exists(ap_path):
        print(f"    ⚠️  Author page not found: {author_info['page']}")
        return
    
    with open(ap_path) as f:
        html = f.read()
    
    if _card_already_exists(html, article["filename"]):
        print(f"    👤 Author ({article['author']}): already has {article['filename']}")
        return
    
    card = make_author_card(article)
    html = _insert_card_replacing_placeholder(html, card)
    
    with open(ap_path, 'w') as f:
        f.write(html)
    print(f"    👤 Author ({article['author']}): added card")


# ═══════════════════════════════════════════════════════════
# ARTICLE SYNC (Markdown → HTML)
# ═══════════════════════════════════════════════════════════

def sync_article(md_filename):
    md_path = os.path.join(SOURCE_DIR, md_filename)
    with open(md_path) as f:
        content = f.read()
    
    meta, body_md = parse_frontmatter(content)
    if not meta.get("title"):
        print(f"  ⚠️  No frontmatter: {md_filename}")
        return None
    
    # Read template
    with open(TEMPLATE_FILE) as f:
        template = f.read()
    
    # Get head section (all CSS)
    head_end = template.find('</head>')
    head_section = template[:head_end]
    
    # Extract TOC + ScrollSpy JS
    all_scripts = re.findall(r'(<script>.*?</script>)', template, re.DOTALL)
    toc_js = ""
    for s in all_scripts:
        if 'application/ld+json' not in s and 'toc' in s.lower():
            toc_js = s
            break
    if not toc_js:
        for s in reversed(all_scripts):
            if 'application/ld+json' not in s:
                toc_js = s
                break
    
    # Build new head
    new_head = re.sub(r'<title>.*?</title>', f'<title>{meta["title"]}</title>', head_section)
    new_head = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{meta.get("description", "")}">', new_head)
    
    # Convert body
    og_image = meta.get("og:image", "")
    body_html = md_to_html(body_md, cover_image=og_image)
    read_time = calc_read_time(body_html)
    faqs = extract_faqs(body_md)
    
    # Author
    author_name = meta.get("author", "Nexscope Team")
    author = AUTHORS.get(author_name, AUTHORS["Nexscope Team"])
    
    # Date
    date_str = str(meta.get("lastUpdated", meta.get("date", "2026-03-27")))
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        display_date = dt.strftime("Updated %b %d, %Y")
    except:
        display_date = f"Updated {date_str}"
    
    # Category
    category = meta.get("category", "")
    cat_link = CATEGORY_LINKS.get(category, "final-index.html")
    
    # Split at FAQ
    faq_split = re.search(r'(<h2[^>]*>(?:Frequently Asked Questions|FAQ))', body_html)
    if faq_split:
        body_before_faq = body_html[:faq_split.start()]
        body_faq_and_after = body_html[faq_split.start():]
    else:
        body_before_faq = body_html
        body_faq_and_after = ""
    
    # CTA
    cta_title, cta_desc, cta_btn = CTA_MAP.get(category, ("Grow your ecommerce business", "AI-powered intelligence for smarter selling decisions", "Get Started Free →"))
    
    # Schemas
    article_schema = build_article_schema(meta, author_name, author['page'])
    faq_schema = build_faq_schema(faqs)
    
    # Assemble HTML
    output = f'''{new_head}
</head>
<body>
    <nav>
        <div class="nav-container">
            <div class="nav-logo" onclick="window.location.href='final-index.html'">
                <div class="nav-logo-icon">N</div>
                <span class="nav-logo-text">Nexscope</span>
            </div>
            <a href="final-index.html" class="nav-link">Blog</a>
        </div>
    </nav>
    
    <div class="breadcrumbs">
        <a href="final-index.html">Home</a> / <a href="final-index.html">Blog</a> / <a href="{cat_link}">{category}</a> / <span style="color: #3B82F6;">{meta["title"][:50]}...</span>
    </div>
    
    <div class="main-container">
        <article>
            <img src="{og_image}" alt="{meta["title"]}">
            
            <h1>{meta["title"]}</h1>
            
            <div class="author-section">
                {author["avatar_html"]}
                <div class="author-info">
                    <p>Written by <a href="{author["page"]}" class="author-link">{author_name}</a></p>
                    <p style="color: #6B7280; font-size: 12px;">{display_date} &bull; {read_time} min read</p>
                </div>
            </div>
            
            {body_before_faq}
            
            <div class="bottom-cta">
                <h3>{cta_title}</h3>
                <p>{cta_desc}</p>
                <a href="https://www.nexscope.ai">Get Started Free →</a>
                <div class="bottom-cta-small">No coding required • Instant access</div>
            </div>
            
            {body_faq_and_after}
        </article>
        
        <aside>
            <div class="toc-wrapper">
                <div class="toc">
                    <div class="toc-title">Table of Contents</div>
                    <ul class="toc-list" id="toc-list"></ul>
                </div>
                
                <div class="cta-card-sidebar">
                    <h3>{cta_title}</h3>
                    <a href="https://www.nexscope.ai" class="cta-btn-primary">{cta_btn}</a>
                </div>
            </div>
        </aside>
    </div>
    
    <footer>
        <p>© 2026 Nexscope Inc. All rights reserved.</p>
    </footer>
    {article_schema}
    {faq_schema}
    {toc_js}
</body>
</html>'''
    
    # Output filename
    slug = meta.get("slug", "")
    if slug:
        out_name = slug.strip("/").split("/")[-1] + ".html"
    else:
        out_name = os.path.splitext(md_filename)[0] + ".html"
    
    out_path = os.path.join(TARGET_DIR, out_name)
    with open(out_path, 'w') as f:
        f.write(output)
    
    print(f"  ✅ {md_filename} → {out_name} ({read_time} min, {category}, {author_name})")
    
    return {
        "filename": out_name,
        "title": meta["title"],
        "category": category,
        "author": author_name,
        "read_time": read_time,
        "display_date": display_date,
        "og_image": og_image,
    }


# ═══════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════

def main():
    print("🔄 Nexscope Blog Sync v3\n")
    print(f"   Source: {SOURCE_DIR}")
    print(f"   Target: {TARGET_DIR}\n")
    
    if len(sys.argv) > 1:
        md_files = [sys.argv[1]]
    else:
        md_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.md') and f != 'README.md']
    
    results = []
    for f in sorted(md_files):
        r = sync_article(f)
        if r:
            results.append(r)
            # Update listing pages
            update_homepage(r)
            update_category_page(r)
            update_author_page(r)
            print()
    
    print(f"🎉 Synced {len(results)} articles!")
    print(f"   Pages updated: homepage + {len(set(r['category'] for r in results))} category + {len(set(r['author'] for r in results))} author")


if __name__ == "__main__":
    main()
