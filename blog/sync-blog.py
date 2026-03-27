#!/usr/bin/env python3
"""
Nexscope Blog Sync Script
Converts markdown articles from ns-blog-preview → production HTML pages.

Usage:
    python3 sync-blog.py                    # Sync all new articles
    python3 sync-blog.py article-slug.md    # Sync specific article

Source: /tmp/ns-blog-preview/
Target: /tmp/template-repo/blog/
Template: product-research-7-methods.html
"""

import os
import re
import sys
import yaml
import markdown
from datetime import datetime

# === CONFIG ===
SOURCE_DIR = "/tmp/ns-blog-preview"
TARGET_DIR = "/tmp/template-repo/blog"
TEMPLATE_FILE = os.path.join(TARGET_DIR, "product-research-7-methods.html")

# Author mapping
AUTHORS = {
    "Henk Nie": {
        "initials": "HN",
        "avatar": "images/authors/henk-nie.jpg",
        "avatar_style": "object-fit:cover",
        "page": "final-author-henk-nie.html",
    },
    "Nexscope Team": {
        "initials": "NT",
        "avatar": "images/authors/nexscope-team.png",
        "avatar_style": "object-fit:contain",
        "page": "final-author.html",
    },
    "Zhiyi Wu": {
        "initials": "ZW",
        "avatar": "images/authors/zhiyi-wu.jpg",
        "avatar_style": "object-fit:cover",
        "page": "final-author-zhiyi-wu.html",
    },
}

# Category → tag color mapping
CATEGORY_COLORS = {
    "Product Research": {"bg": "#EFF6FF", "color": "#3B82F6"},
    "PPC & Ads": {"bg": "#F5F3FF", "color": "#7C3AED"},
    "Listing Optimization": {"bg": "#ECFDF5", "color": "#059669"},
    "Profit & FBA": {"bg": "#FFFBEB", "color": "#D97706"},
    "Sourcing & Supply": {"bg": "#FEF2F2", "color": "#DC2626"},
    "Market Intelligence": {"bg": "#ECFEFF", "color": "#0891B2"},
    "AI for Amazon Sellers": {"bg": "#EEF2FF", "color": "#4F46E5"},
    "AI for Ecommerce": {"bg": "#EEF2FF", "color": "#4F46E5"},
    "Tool Reviews": {"bg": "#FDF2F8", "color": "#DB2777"},
    "Seller Guides": {"bg": "#FFFBEB", "color": "#B45309"},
    "Nexscope News": {"bg": "#EFF6FF", "color": "#3B82F6"},
}


def parse_frontmatter(content):
    """Extract YAML frontmatter and body from markdown."""
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            meta = yaml.safe_load(parts[1])
            body = parts[2].strip()
            return meta, body
    return {}, content


def md_to_html(md_text):
    """Convert markdown to HTML with tables, fenced code, etc."""
    extensions = ['tables', 'fenced_code', 'toc', 'attr_list']
    html = markdown.markdown(md_text, extensions=extensions)
    return html


def extract_h2_toc(html):
    """Extract H2 headings for TOC (H2 only, not H3)."""
    h2s = re.findall(r'<h2[^>]*id="([^"]*)"[^>]*>(.*?)</h2>', html, re.DOTALL)
    if not h2s:
        # Try without id
        h2s_no_id = re.findall(r'<h2>(.*?)</h2>', html)
        toc_items = []
        for h in h2s_no_id:
            slug = re.sub(r'[^\w\s-]', '', h.lower()).strip().replace(' ', '-')
            toc_items.append((slug, h))
        return toc_items
    return h2s


def extract_faq(md_text):
    """Extract FAQ section from markdown for FAQPage schema."""
    faq_match = re.search(r'##\s*(?:FAQ|Frequently Asked Questions)(.*?)(?=\n## |\Z)', md_text, re.DOTALL)
    if not faq_match:
        return []
    
    faq_text = faq_match.group(1)
    # Find Q&A pairs: ### Question\n\nAnswer
    qa_pairs = re.findall(r'###\s*(.*?)\n+(.*?)(?=\n### |\Z)', faq_text, re.DOTALL)
    faqs = []
    for q, a in qa_pairs:
        q = q.strip().rstrip('?') + '?'
        a = a.strip()
        # Remove markdown formatting
        a = re.sub(r'\*\*(.*?)\*\*', r'\1', a)
        a = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', a)
        if a and q:
            faqs.append({"q": q, "a": a.split('\n')[0]})  # First paragraph only
    return faqs


def calc_read_time(html):
    """Calculate reading time based on word count (238 wpm Medium standard)."""
    text = re.sub(r'<[^>]+>', ' ', html)
    words = len(text.split())
    return max(1, round(words / 238))


def slug_from_filename(filename):
    """Generate HTML filename from markdown filename."""
    name = os.path.splitext(filename)[0]
    return name + ".html"


def generate_article_html(meta, body_html, read_time, faqs):
    """Generate complete article HTML using the template structure."""
    
    author_name = meta.get("author", "Nexscope Team")
    author = AUTHORS.get(author_name, AUTHORS["Nexscope Team"])
    category = meta.get("category", "")
    cat_colors = CATEGORY_COLORS.get(category, {"bg": "#EFF6FF", "color": "#3B82F6"})
    
    title = meta.get("title", "")
    description = meta.get("description", "")
    og_image = meta.get("og:image", "")
    date_str = meta.get("lastUpdated", meta.get("date", "2026-03-27"))
    keywords = meta.get("keywords", "")
    
    # Format date
    try:
        dt = datetime.strptime(str(date_str), "%Y-%m-%d")
        display_date = dt.strftime("Updated %b %d, %Y")
        iso_date = dt.strftime("%Y-%m-%dT00:00:00Z")
    except:
        display_date = f"Updated {date_str}"
        iso_date = f"{date_str}T00:00:00Z"
    
    pub_date = meta.get("date", date_str)
    try:
        pub_dt = datetime.strptime(str(pub_date), "%Y-%m-%d")
        iso_pub_date = pub_dt.strftime("%Y-%m-%dT00:00:00Z")
    except:
        iso_pub_date = f"{pub_date}T00:00:00Z"

    # FAQ Schema
    faq_schema = ""
    if faqs:
        faq_entities = []
        for faq in faqs:
            q_escaped = faq['q'].replace('"', '\\"')
            a_escaped = faq['a'].replace('"', '\\"')
            faq_entities.append(f'''    {{
      "@type": "Question",
      "name": "{q_escaped}",
      "acceptedAnswer": {{
        "@type": "Answer",
        "text": "{a_escaped}"
      }}
    }}''')
        faq_joined = ",\n".join(faq_entities)
        faq_schema = f'''
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "FAQPage",
      "mainEntity": [
{faq_joined}
      ]
    }}
    </script>'''

    # CTA text based on category
    cta_texts = {
        "Product Research": ("Find Winning Products Faster", "Nexscope uses AI to analyze market data and surface high-potential product opportunities — so you can skip the guesswork."),
        "Seller Guides": ("Start Selling Smarter", "Nexscope gives you AI-powered insights to launch and grow your ecommerce business with confidence."),
        "AI for Amazon Sellers": ("Automate Your Amazon Workflow", "Nexscope brings AI-powered automation to your daily seller tasks — from research to optimization."),
        "AI for Ecommerce": ("Automate Your Amazon Workflow", "Nexscope brings AI-powered automation to your daily seller tasks — from research to optimization."),
    }
    cta_title, cta_desc = cta_texts.get(category, ("Grow Your Ecommerce Business", "Nexscope uses AI-powered intelligence to help you make smarter selling decisions."))

    # Read the template CSS + structure
    with open(TEMPLATE_FILE) as f:
        template = f.read()
    
    # Extract CSS block
    css_match = re.search(r'(<style>.*?</style>)', template, re.DOTALL)
    css = css_match.group(1) if css_match else ""

    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <meta name="description" content="{description}">
    <meta name="keywords" content="{keywords}">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    <meta property="og:image" content="{og_image}">
    <meta property="og:type" content="article">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    {css}
    <script type="application/ld+json">
    {{
      "@context": "https://schema.org",
      "@type": "Article",
      "headline": "{title}",
      "description": "{description}",
      "image": "{og_image}",
      "author": {{
        "@type": "Person",
        "name": "{author_name}",
        "url": "https://chiyeee.github.io/zixun-openclaw-noerroer-design/blog/{author['page']}"
      }},
      "publisher": {{
        "@type": "Organization",
        "name": "Nexscope",
        "logo": {{
          "@type": "ImageObject",
          "url": "https://www.nexscope.ai/logo.png"
        }}
      }},
      "datePublished": "{iso_pub_date}",
      "dateModified": "{iso_date}",
      "mainEntityOfPage": {{
        "@type": "WebPage"
      }}
    }}
    </script>{faq_schema}
</head>
<body>
    <nav>
        <div class="nav-container">
            <a href="final-index.html" class="nav-logo" style="text-decoration:none">
                <div class="nav-logo-icon">N</div>
                <span class="nav-logo-text">Nexscope</span>
            </a>
            <div style="display:flex;gap:2rem;align-items:center;">
                <a href="final-index.html" class="nav-link">Blog</a>
                <a href="https://www.nexscope.ai" class="nav-link" style="background:#3B82F6;color:white;padding:8px 20px;border-radius:6px;">Get Started</a>
            </div>
        </div>
    </nav>

    <div class="breadcrumbs">
        <a href="final-index.html">Home</a> / <a href="final-index.html">Blog</a> / <span style="color: #3B82F6;">{category}</span>
    </div>

    <div class="content-wrapper">
        <main class="main-content">
            <img src="{og_image}" alt="{title}" style="width:100%;border-radius:12px;margin-bottom:1.5rem;">
            
            <div class="author-section">
                <div class="author-avatar" style="padding:0;overflow:hidden;{'background:white;' if author_name == 'Nexscope Team' else ''}">
                    <img src="{author['avatar']}" alt="{author_name}" style="width:100%;height:100%;{author['avatar_style']};border-radius:50%">
                </div>
                <div class="author-info">
                    <p>Written by <a href="{author['page']}" class="author-link">{author_name}</a></p>
                    <p style="color: #6B7280; font-size: 12px;">{display_date} &bull; {read_time} min read</p>
                </div>
            </div>
            
            <article>
                {body_html}
            </article>
            
            <div class="bottom-cta" style="background: linear-gradient(135deg, #3B82F6 0%, #7C3AED 100%); border-radius: 16px; padding: 3rem; text-align: center; margin: 3rem 0; color: white;">
                <h2 style="font-size: 2rem; font-weight: 800; margin-bottom: 0.75rem; color: white;">{cta_title}</h2>
                <p style="font-size: 1.05rem; opacity: 0.9; margin-bottom: 1.5rem; max-width: 500px; margin-left: auto; margin-right: auto;">{cta_desc}</p>
                <a href="https://www.nexscope.ai" style="display: inline-block; background: #111827; color: white; padding: 14px 36px; border-radius: 8px; font-weight: 700; text-decoration: none; font-size: 16px;">Get Started — It's Free</a>
                <p style="font-size: 12px; opacity: 0.7; margin-top: 0.75rem;">No coding required &bull; Instant access</p>
            </div>
        </main>

        <aside>
            <div class="toc-wrapper">
                <div class="toc">
                    <h3 class="toc-title">Table of Contents</h3>
                    <ul id="toc-list"></ul>
                </div>
                <div class="cta-card-sidebar" style="background: linear-gradient(135deg, rgba(59,130,246,0.12), rgba(139,92,246,0.08)); border: 1px solid rgba(59,130,246,0.15); border-radius: 12px; padding: 1.5rem; margin-top: 1.5rem; backdrop-filter: blur(8px);">
                    <h3 style="font-size: 1rem; font-weight: 700; color: #111827; margin-bottom: 0.5rem;">{cta_title}</h3>
                    <p style="font-size: 13px; color: #6B7280; margin-bottom: 1rem;">{cta_desc}</p>
                    <a href="https://www.nexscope.ai" style="display: block; text-align: center; background: linear-gradient(135deg, #3B82F6, #7C3AED); color: white; padding: 10px; border-radius: 8px; font-weight: 600; text-decoration: none; font-size: 14px;">Try Nexscope Free</a>
                </div>
            </div>
        </aside>
    </div>

    <footer style="background: #111827; padding: 3rem 2rem; text-align: center; color: rgba(255,255,255,0.5); font-size: 14px; margin-top: 3rem;">
        <p>&copy; 2026 Nexscope Inc. All rights reserved. &middot; <a href="https://www.nexscope.ai" style="color: rgba(255,255,255,0.7); text-decoration: none;">nexscope.ai</a></p>
    </footer>

    <script>
        // Auto-generate TOC from H2 tags
        document.addEventListener('DOMContentLoaded', function() {{
            const article = document.querySelector('article');
            const tocList = document.getElementById('toc-list');
            const headings = article.querySelectorAll('h2');
            
            headings.forEach(function(h, i) {{
                if (!h.id) h.id = 'section-' + i;
                const li = document.createElement('li');
                li.className = 'toc-item';
                const a = document.createElement('a');
                a.href = '#' + h.id;
                a.textContent = h.textContent;
                a.className = 'toc-link';
                li.appendChild(a);
                tocList.appendChild(li);
            }});
            
            // Scroll spy
            const links = document.querySelectorAll('.toc-link');
            window.addEventListener('scroll', function() {{
                let current = '';
                headings.forEach(function(h) {{
                    if (window.scrollY >= h.offsetTop - 120) current = h.id;
                }});
                links.forEach(function(link) {{
                    link.classList.remove('active');
                    if (link.getAttribute('href') === '#' + current) link.classList.add('active');
                }});
            }});
        }});
    </script>
</body>
</html>'''
    return html


def sync_article(md_filename):
    """Process a single markdown file into HTML."""
    md_path = os.path.join(SOURCE_DIR, md_filename)
    
    with open(md_path) as f:
        content = f.read()
    
    meta, body = parse_frontmatter(content)
    if not meta.get("title"):
        print(f"  ⚠️  No frontmatter found in {md_filename}, skipping")
        return None
    
    # Convert markdown body to HTML
    body_html = md_to_html(body)
    
    # Remove the first H1 (it's already in the page title area)
    body_html = re.sub(r'<h1>.*?</h1>', '', body_html, count=1)
    
    # Extract FAQs
    faqs = extract_faq(body)
    
    # Calculate read time
    read_time = calc_read_time(body_html)
    
    # Generate output filename from slug or filename
    slug = meta.get("slug", "")
    if slug:
        out_name = slug.strip("/").split("/")[-1] + ".html"
    else:
        out_name = slug_from_filename(md_filename)
    
    out_path = os.path.join(TARGET_DIR, out_name)
    
    # Generate HTML
    html = generate_article_html(meta, body_html, read_time, faqs)
    
    with open(out_path, 'w') as f:
        f.write(html)
    
    print(f"  ✅ {md_filename}")
    print(f"     → {out_name} ({read_time} min read)")
    print(f"     Category: {meta.get('category')} | Author: {meta.get('author')}")
    
    return {
        "filename": out_name,
        "title": meta.get("title"),
        "category": meta.get("category"),
        "author": meta.get("author"),
        "date": meta.get("lastUpdated", meta.get("date")),
        "image": meta.get("og:image"),
        "read_time": read_time,
    }


def main():
    print("🔄 Nexscope Blog Sync")
    print(f"   Source: {SOURCE_DIR}")
    print(f"   Target: {TARGET_DIR}\n")
    
    # Check template exists
    if not os.path.exists(TEMPLATE_FILE):
        print(f"❌ Template not found: {TEMPLATE_FILE}")
        return
    
    # Get list of files to process
    if len(sys.argv) > 1:
        md_files = [sys.argv[1]]
    else:
        md_files = [f for f in os.listdir(SOURCE_DIR) if f.endswith('.md') and f != 'README.md']
    
    results = []
    for md_file in sorted(md_files):
        result = sync_article(md_file)
        if result:
            results.append(result)
    
    print(f"\n🎉 Synced {len(results)} articles!")
    
    # Print summary for homepage/category update
    if results:
        print("\n📋 Update homepage cards with:")
        for r in results:
            print(f"   {r['filename']} | {r['category']} | {r['title'][:50]}... | {r['read_time']} min")


if __name__ == "__main__":
    main()
