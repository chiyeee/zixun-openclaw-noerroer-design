#!/usr/bin/env python3
"""
Nexscope Blog Sync Script v2
Directly cuts the template HTML and replaces content sections.
Guarantees 100% style parity with product-research-7-methods.html.

Usage:
    python3 sync-blog.py                    # Sync all new articles
    python3 sync-blog.py article-slug.md    # Sync specific article
"""

import os, re, sys, yaml, markdown
from datetime import datetime

SOURCE_DIR = "/tmp/ns-blog-preview"
TARGET_DIR = "/tmp/template-repo/blog"
TEMPLATE_FILE = os.path.join(TARGET_DIR, "product-research-7-methods.html")

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

CTA_MAP = {
    "Product Research": ("Find your winning niche in minutes", "Discover high-opportunity products with proven research methods", "Start Your Research Now →"),
    "Seller Guides": ("Start selling smarter today", "AI-powered insights to launch and grow your ecommerce business", "Get Started Free →"),
    "AI for Amazon Sellers": ("Automate your Amazon workflow", "AI-powered tools to save hours on research, listing, and optimization", "Try Nexscope Free →"),
    "AI for Ecommerce": ("Automate your Amazon workflow", "AI-powered tools to save hours on research, listing, and optimization", "Try Nexscope Free →"),
}


def parse_frontmatter(content):
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return yaml.safe_load(parts[1]), parts[2].strip()
    return {}, content


def md_to_html(md_text, cover_image=""):
    """Convert markdown to article-body HTML."""
    html = markdown.markdown(md_text, extensions=['tables', 'fenced_code', 'toc'])
    
    # Remove first H1 (already shown above article)
    html = re.sub(r'<h1>.*?</h1>\s*', '', html, count=1)
    
    # Remove cover image duplicates (already shown above article)
    if cover_image:
        # Remove any <img> or <p><img></p> that contains the cover image URL
        cover_escaped = re.escape(cover_image)
        html = re.sub(r'<p>\s*<img[^>]*src="' + cover_escaped + r'"[^>]*/?\s*>\s*</p>\s*', '', html)
        html = re.sub(r'<img[^>]*src="' + cover_escaped + r'"[^>]*/?\s*>\s*', '', html)
    
    # Add IDs to h2 tags for TOC linking
    def add_h2_id(match):
        text = re.sub(r'<[^>]+>', '', match.group(1))
        slug = re.sub(r'[^\w\s-]', '', text.lower()).strip()
        slug = re.sub(r'\s+', '-', slug)
        return f'<h2 id="{slug}">{match.group(1)}</h2>'
    
    html = re.sub(r'<h2>(.*?)</h2>', add_h2_id, html)
    
    return html


def calc_read_time(html):
    text = re.sub(r'<[^>]+>', ' ', html)
    words = len(text.split())
    return max(1, round(words / 238))


def extract_faqs(md_text):
    """Extract FAQ for JSON-LD schema."""
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
    
    # === SPLIT TEMPLATE INTO 3 PARTS ===
    # Part 1: Everything from start to </head> (includes all CSS)
    # Part 2: <body> content (we'll rebuild this)
    # Part 3: The JS scripts at the end
    
    # Get everything up to </style></head>
    head_end = template.find('</head>')
    head_section = template[:head_end]
    
    # Get the TOC + ScrollSpy JS from template
    js_match = re.search(r'(<script>\s*// Auto-generate TOC.*?</script>)', template, re.DOTALL)
    if not js_match:
        js_match = re.search(r'(<script>\s*document\.addEventListener.*?</script>)', template, re.DOTALL)
    toc_js = js_match.group(1) if js_match else ""
    
    # === BUILD NEW HEAD ===
    # Replace title
    new_head = re.sub(r'<title>.*?</title>', f'<title>{meta["title"]}</title>', head_section)
    # Replace meta description
    new_head = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{meta.get("description", "")}">', new_head)
    
    # === CONVERT BODY ===
    og_image = meta.get("og:image", "")
    body_html = md_to_html(body_md, cover_image=og_image)
    read_time = calc_read_time(body_html)
    faqs = extract_faqs(body_md)
    
    # Author info
    author_name = meta.get("author", "Nexscope Team")
    author = AUTHORS.get(author_name, AUTHORS["Nexscope Team"])
    
    # Date formatting
    date_str = str(meta.get("lastUpdated", meta.get("date", "2026-03-27")))
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        display_date = dt.strftime("Updated %b %d, %Y")
    except:
        display_date = f"Updated {date_str}"
    
    # Category
    category = meta.get("category", "")
    
    # CTA
    cta_title, cta_desc, cta_btn = CTA_MAP.get(category, ("Grow your ecommerce business", "AI-powered intelligence for smarter selling decisions", "Get Started Free →"))
    
    # === ASSEMBLE COMPLETE HTML ===
    article_schema = build_article_schema(meta, author_name, author['page'])
    faq_schema = build_faq_schema(faqs)
    
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
        <a href="final-index.html">Home</a> / <a href="final-index.html">Blog</a> / <a href="#">{category}</a> / <span style="color: #3B82F6;">{meta["title"][:50]}...</span>
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
            
            {body_html}
            
            <div class="bottom-cta">
                <h3>{cta_title}</h3>
                <p>{cta_desc}</p>
                <a href="https://www.nexscope.ai">Get Started Free →</a>
                <div class="bottom-cta-small">No coding required • Instant access</div>
            </div>
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
    
    print(f"  ✅ {md_filename} → {out_name} ({read_time} min)")
    return {"filename": out_name, "title": meta["title"], "category": category, "read_time": read_time}


def main():
    print("🔄 Nexscope Blog Sync v2\n")
    
    if len(sys.argv) > 1:
        md_files = [sys.argv[1]]
    else:
        md_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.md') and f != 'README.md']
    
    results = []
    for f in sorted(md_files):
        r = sync_article(f)
        if r:
            results.append(r)
    
    print(f"\n🎉 Synced {len(results)} articles!")


if __name__ == "__main__":
    main()
