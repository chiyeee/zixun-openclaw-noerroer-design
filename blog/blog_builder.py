#!/usr/bin/env python3
"""
Nexscope Blog Builder - 静态博客生成系统
功能：
1. 读取 Markdown 文件
2. 解析 frontmatter 元数据
3. 转换 Markdown 为 HTML
4. 填充到 HTML 模板
5. 生成静态站点

用法：
    python blog_builder.py --source ../blog-content --output ./dist
    python blog_builder.py --watch  # 监听文件变化自动重建
"""

import os
import re
import json
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
import hashlib

# 尝试导入依赖，如果没有则提示安装
try:
    import yaml
    import markdown
    from markdown.extensions.toc import TocExtension
    from markdown.extensions.tables import TableExtension
    from markdown.extensions.fenced_code import FencedCodeExtension
except ImportError:
    print("请先安装依赖: pip install pyyaml markdown")
    exit(1)


class BlogPost:
    """博客文章类"""
    
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.slug = filepath.stem  # 文件名作为 URL slug
        self.raw_content = filepath.read_text(encoding='utf-8')
        self.frontmatter = {}
        self.content_md = ""
        self.content_html = ""
        self.toc_html = ""
        
        self._parse()
    
    def _parse(self):
        """解析 frontmatter 和内容"""
        # 匹配 YAML frontmatter (--- 开头和结尾)
        pattern = r'^---\s*\n(.*?)\n---\s*\n(.*)$'
        match = re.match(pattern, self.raw_content, re.DOTALL)
        
        if match:
            frontmatter_str = match.group(1)
            self.content_md = match.group(2)
            
            # 解析 YAML（处理表格格式的元数据）
            self.frontmatter = self._parse_frontmatter(frontmatter_str)
        else:
            # 没有 frontmatter，整个文件都是内容
            self.content_md = self.raw_content
        
        # 转换 Markdown 为 HTML
        self._render_markdown()
    
    def _parse_frontmatter(self, content: str) -> Dict:
        """解析 frontmatter，支持表格格式和标准 YAML"""
        result = {}
        
        lines = content.strip().split('\n')
        
        # 第一步：处理 Markdown 表格（带标题行）
        # | Blog Title | Target Keywords | Search Volume |
        # |------------|----------------|---------------|
        # | OpenClaw for Amazon Sellers... | openclaw, openclaw ai | 24,500/mo |
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # 检测表格头部行
            if line.startswith('|') and line.endswith('|') and '|' in line[1:-1]:
                cells = [c.strip() for c in line[1:-1].split('|')]
                
                # 检查是否是标题行（不是分隔线，且不是数据行）
                if cells and not cells[0].startswith('-'):
                    # 这可能是标题行，检查下一行是否是分隔线
                    if i + 1 < len(lines):
                        next_line = lines[i + 1].strip()
                        if next_line.startswith('|') and '-' in next_line:
                            # 找到表格！下一个非分隔行是数据行
                            headers = [c.lower().replace(' ', '_') for c in cells]
                            
                            # 跳过分隔线，找数据行
                            i += 2
                            while i < len(lines):
                                data_line = lines[i].strip()
                                if data_line.startswith('|') and data_line.endswith('|'):
                                    if '-' not in data_line or '|' not in data_line[1:-1].replace('-', ''):
                                        # 这是数据行
                                        values = [c.strip() for c in data_line[1:-1].split('|')]
                                        for j, header in enumerate(headers):
                                            if j < len(values) and header:
                                                result[header] = values[j]
                                        break
                                i += 1
                            i += 1
                            continue
            
            # 处理 **Key:** Value 格式
            bold_match = re.match(r'\*\*(.+?):\*\*\s*(.+)', line)
            if bold_match:
                key = bold_match.group(1).lower().replace(' ', '_')
                value = bold_match.group(2).strip()
                result[key] = value
                i += 1
                continue
            
            # 处理标准 YAML 格式 key: value
            yaml_match = re.match(r'^([a-zA-Z_][a-zA-Z0-9_\s]*?):\s*(.*)$', line)
            if yaml_match:
                key = yaml_match.group(1).lower().replace(' ', '_')
                value = yaml_match.group(2).strip()
                result[key] = value
                i += 1
                continue
            
            i += 1
        
        # 尝试直接 YAML 解析作为后备
        try:
            yaml_result = yaml.safe_load(content)
            if isinstance(yaml_result, dict):
                for k, v in yaml_result.items():
                    if k not in result:
                        result[k] = v
        except:
            pass
        
        return result
    
    def _render_markdown(self):
        """将 Markdown 转换为 HTML"""
        md = markdown.Markdown(extensions=[
            'tables',
            'fenced_code',
            'codehilite',
            TocExtension(baselevel=2, toc_class='toc-list'),
            'nl2br',
            'sane_lists'
        ])
        
        self.content_html = md.convert(self.content_md)
        self.toc_html = getattr(md, 'toc', '')
    
    @property
    def title(self) -> str:
        """获取文章标题"""
        # 优先从 frontmatter 获取
        for key in ['title', 'blog_title', 'headline']:
            if key in self.frontmatter:
                return self.frontmatter[key]
        
        # 从 H1 标题获取
        match = re.search(r'^#\s+(.+)$', self.content_md, re.MULTILINE)
        if match:
            return match.group(1)
        
        return self.slug.replace('-', ' ').title()
    
    @property
    def description(self) -> str:
        """获取文章描述"""
        for key in ['meta_description', 'description', 'excerpt']:
            if key in self.frontmatter:
                return self.frontmatter[key]
        return ""
    
    @property
    def category(self) -> str:
        """获取分类"""
        return self.frontmatter.get('category', 'Uncategorized')
    
    @property
    def author(self) -> str:
        """获取作者"""
        return self.frontmatter.get('author', 'Nexscope Team')
    
    @property
    def date(self) -> str:
        """获取日期"""
        for key in ['date', 'published', 'updated']:
            if key in self.frontmatter:
                return self.frontmatter[key]
        return datetime.now().strftime('%B %d, %Y')
    
    @property
    def url_slug(self) -> str:
        """获取 URL slug"""
        slug = self.frontmatter.get('url_slug', '')
        if slug:
            # 提取最后的路径部分
            return slug.rstrip('/').split('/')[-1]
        return self.slug
    
    @property
    def cover_image(self) -> str:
        """获取封面图片"""
        # 从内容中提取第一张图片
        match = re.search(r'!\[.*?\]\((.*?)\)', self.content_md)
        if match:
            return match.group(1)
        return ""
    
    @property
    def keywords(self) -> List[str]:
        """获取关键词"""
        kw = self.frontmatter.get('target_keywords', '')
        if kw:
            return [k.strip() for k in kw.split(',')]
        return []
    
    @property
    def reading_time(self) -> int:
        """估算阅读时间（分钟）"""
        word_count = len(self.content_md.split())
        return max(1, word_count // 200)  # 假设每分钟 200 词
    
    def to_dict(self) -> Dict:
        """转换为字典（用于 JSON）"""
        return {
            'slug': self.url_slug,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'author': self.author,
            'date': self.date,
            'cover_image': self.cover_image,
            'keywords': self.keywords,
            'reading_time': self.reading_time,
            'url': f'/blog/{self.url_slug}/'
        }


class BlogBuilder:
    """博客生成器"""
    
    def __init__(self, source_dir: str, output_dir: str, template_dir: str):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.template_dir = Path(template_dir)
        self.posts: List[BlogPost] = []
    
    def load_template(self, name: str) -> str:
        """加载 HTML 模板"""
        template_path = self.template_dir / f"{name}.html"
        if template_path.exists():
            return template_path.read_text(encoding='utf-8')
        raise FileNotFoundError(f"模板不存在: {template_path}")
    
    def scan_posts(self) -> List[BlogPost]:
        """扫描所有 Markdown 文件"""
        self.posts = []
        
        if not self.source_dir.exists():
            print(f"⚠️ 源目录不存在: {self.source_dir}")
            return []
        
        for md_file in self.source_dir.glob('**/*.md'):
            try:
                post = BlogPost(md_file)
                self.posts.append(post)
                print(f"📄 已解析: {md_file.name} → {post.title[:50]}...")
            except Exception as e:
                print(f"❌ 解析失败 {md_file.name}: {e}")
        
        # 按日期排序（新的在前）
        self.posts.sort(key=lambda p: p.date, reverse=True)
        return self.posts
    
    def render_article(self, post: BlogPost) -> str:
        """渲染单篇文章"""
        template = self.load_template('article-template')
        
        # 生成目录 HTML
        toc_items = self._generate_toc(post.content_html)
        
        # 替换模板变量
        html = template
        
        # 标题和 meta
        html = re.sub(r'<title>.*?</title>', f'<title>{post.title} | Nexscope Blog</title>', html)
        html = re.sub(r'<meta name="description" content=".*?">', 
                      f'<meta name="description" content="{post.description}">', html)
        
        # 文章标题
        html = re.sub(r'<h1 class="[^"]*">[^<]*</h1>', 
                      f'<h1 class="text-4xl md:text-6xl font-extrabold text-white mb-8 leading-[1.1] tracking-tight">{post.title}</h1>', html)
        
        # 分类（多处替换）
        html = re.sub(r'<span class="text-brand-400 font-medium">[^<]*</span>', 
                      f'<span class="text-brand-400 font-medium">{post.category}</span>', html)
        html = re.sub(r'>Strategy</span>', f'>{post.category}</span>', html)
        html = re.sub(r'<span class="px-2\.5 py-1 bg-brand-500/10[^>]*>[^<]*</span>',
                      f'<span class="px-2.5 py-1 bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-bold rounded-md uppercase">{post.category}</span>', html)
        
        # 作者
        html = re.sub(r'Written by\s*<a[^>]*>[^<]*</a>', 
                      f'Written by <a href="/blog/author/{post.author.lower().replace(" ", "-")}/" class="text-brand-400 hover:text-brand-500 hover:underline transition-colors">{post.author}</a>', html)
        
        # 日期
        html = re.sub(r'Updated [A-Za-z]+ \d+, \d+', f'Updated {post.date}', html)
        
        # 阅读时间
        html = re.sub(r'• 15 min read', f'• {post.reading_time} min read', html)
        
        # Schema JSON-LD
        schema = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": post.title,
            "description": post.description,
            "author": {
                "@type": "Person",
                "name": post.author,
                "url": f"https://nexscope.com/blog/author/{post.author.lower().replace(' ', '-')}/"
            },
            "datePublished": post.date,
            "dateModified": post.date,
            "publisher": {
                "@type": "Organization",
                "name": "Nexscope",
                "logo": {
                    "@type": "ImageObject",
                    "url": "https://nexscope.com/logo.png"
                }
            }
        }
        html = re.sub(r'<script type="application/ld\+json">.*?</script>', 
                      f'<script type="application/ld+json">\n{json.dumps(schema, indent=2)}\n</script>', 
                      html, flags=re.DOTALL)
        
        # 目录
        html = re.sub(r'<ul class="space-y-1 text-sm border-l border-white/10 mb-8">.*?</ul>', 
                      toc_items, html, flags=re.DOTALL)
        
        # 处理文章内容 - 添加正确的 CSS 类
        styled_content = self._style_content(post.content_html)
        
        # 完全替换文章内容区域
        # 策略：找到 <div class="prose max-w-none"> 到 <!-- Bottom CTA --> 之间的内容并替换
        
        prose_start = '<div class="prose max-w-none">'
        content_end = '<!-- Bottom CTA -->'
        
        start_pos = html.find(prose_start)
        end_pos = html.find(content_end)
        
        if start_pos > 0 and end_pos > start_pos:
            # 找到了内容区域，完全替换
            before = html[:start_pos]
            after = html[end_pos:]
            
            new_content = f'''<div class="prose prose-lg max-w-none text-slate-300">
                    {styled_content}
                </div>

                '''
            html = before + new_content + after
        else:
            # 后备方案：尝试其他标记
            article_end = '</article>'
            if article_end in html:
                html = html.replace(article_end, f'''
                <!-- Article Content -->
                <div class="prose prose-lg max-w-none text-slate-300">
                    {styled_content}
                </div>

            {article_end}''')
        
        return html
    
    def _style_content(self, html: str) -> str:
        """为 Markdown 转换后的 HTML 添加 Tailwind CSS 样式"""
        styled = html
        
        # H1 - 超大标题（支持带属性的标签）
        styled = re.sub(
            r'<h1([^>]*)>([^<]+)</h1>',
            r'<h1\1 class="text-4xl font-extrabold text-white mt-12 mb-6">\2</h1>',
            styled
        )
        
        # H2 - 主要章节标题（支持带属性的标签）
        styled = re.sub(
            r'<h2([^>]*)>([^<]+)</h2>',
            r'<h2\1 class="text-3xl font-extrabold text-white mt-12 mb-6 border-b border-white/10 pb-4">\2</h2>',
            styled
        )
        
        # H3 - 子章节标题（支持带属性的标签）
        styled = re.sub(
            r'<h3([^>]*)>([^<]+)</h3>',
            r'<h3\1 class="text-2xl font-bold text-white mt-8 mb-4">\2</h3>',
            styled
        )
        
        # H4 - 小标题（支持带属性的标签）
        styled = re.sub(
            r'<h4([^>]*)>([^<]+)</h4>',
            r'<h4\1 class="text-xl font-semibold text-slate-200 mt-6 mb-3">\2</h4>',
            styled
        )
        
        # 段落
        styled = re.sub(
            r'<p>',
            r'<p class="text-slate-300 leading-relaxed mb-6">',
            styled
        )
        
        # 无序列表
        styled = re.sub(
            r'<ul>',
            r'<ul class="list-disc list-inside space-y-2 mb-6 text-slate-300">',
            styled
        )
        
        # 有序列表
        styled = re.sub(
            r'<ol>',
            r'<ol class="list-decimal list-inside space-y-2 mb-6 text-slate-300">',
            styled
        )
        
        # 列表项
        styled = re.sub(
            r'<li>',
            r'<li class="text-slate-300">',
            styled
        )
        
        # 代码块
        styled = re.sub(
            r'<pre><code([^>]*)>',
            r'<pre class="bg-bg-card border border-white/10 rounded-xl p-6 overflow-x-auto mb-6"><code\1 class="text-sm text-slate-300">',
            styled
        )
        
        # 行内代码
        styled = re.sub(
            r'<code>([^<]+)</code>',
            r'<code class="bg-bg-card px-2 py-1 rounded text-brand-400 text-sm">\1</code>',
            styled
        )
        
        # 引用块
        styled = re.sub(
            r'<blockquote>',
            r'<blockquote class="border-l-4 border-brand-500 bg-brand-500/10 p-6 rounded-r-xl my-6 text-slate-300 italic">',
            styled
        )
        
        # 表格
        styled = re.sub(
            r'<table>',
            r'<div class="overflow-x-auto mb-6"><table class="min-w-full border border-white/10 rounded-xl overflow-hidden">',
            styled
        )
        styled = re.sub(
            r'</table>',
            r'</table></div>',
            styled
        )
        styled = re.sub(
            r'<thead>',
            r'<thead class="bg-bg-card">',
            styled
        )
        styled = re.sub(
            r'<th>',
            r'<th class="px-4 py-3 text-left text-sm font-bold text-white border-b border-white/10">',
            styled
        )
        styled = re.sub(
            r'<td>',
            r'<td class="px-4 py-3 text-sm text-slate-300 border-b border-white/5">',
            styled
        )
        
        # 图片（处理自闭合标签）
        styled = re.sub(
            r'<img([^>]*)/?>',
            r'<img\1 class="rounded-xl my-8 w-full">',
            styled
        )
        
        # 链接
        styled = re.sub(
            r'<a href="([^"]+)">',
            r'<a href="\1" class="text-brand-400 hover:text-brand-300 underline">',
            styled
        )
        
        # Strong/Bold
        styled = re.sub(
            r'<strong>',
            r'<strong class="text-white font-semibold">',
            styled
        )
        
        return styled
    
    def _generate_toc(self, html: str) -> str:
        """从 HTML 生成目录"""
        # 提取 h2, h3 标题
        headings = re.findall(r'<h([23])[^>]*(?:id="([^"]*)")?[^>]*>([^<]+)</h\1>', html)
        
        toc_items = []
        for level, id_, text in headings:
            slug = id_ or text.lower().replace(' ', '-').replace("'", '')
            indent = '' if level == '2' else 'ml-4'
            toc_items.append(
                f'<li><a href="#{slug}" class="block py-2 pl-4 border-l-2 border-transparent text-slate-500 hover:text-white {indent}">{text}</a></li>'
            )
        
        return f'<ul class="space-y-1 text-sm border-l border-white/10 mb-8">{"".join(toc_items)}</ul>'
    
    def render_index(self) -> str:
        """渲染博客首页"""
        template = self.load_template('index')
        
        # 生成文章列表 HTML
        cards_html = ""
        for post in self.posts[:12]:  # 首页显示 12 篇
            cards_html += f'''
            <a href="/blog/{post.url_slug}/" class="group bg-bg-card rounded-2xl overflow-hidden border border-white/5 hover:border-brand-500/30 transition-all duration-300">
                <div class="aspect-video bg-bg-hover relative overflow-hidden">
                    <img src="{post.cover_image or '/images/placeholder.png'}" alt="{post.title}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500">
                </div>
                <div class="p-6">
                    <span class="text-xs font-bold text-brand-400 uppercase tracking-wider">{post.category}</span>
                    <h3 class="mt-2 text-lg font-bold text-white group-hover:text-brand-400 transition-colors line-clamp-2">{post.title}</h3>
                    <p class="mt-2 text-sm text-slate-500 line-clamp-2">{post.description}</p>
                    <div class="mt-4 flex items-center text-xs text-slate-600">
                        <span>{post.author}</span>
                        <span class="mx-2">•</span>
                        <span>{post.reading_time} min read</span>
                    </div>
                </div>
            </a>
'''
        
        # 替换文章列表区域
        html = re.sub(r'<!-- ARTICLE_CARDS_START -->.*?<!-- ARTICLE_CARDS_END -->', 
                      f'<!-- ARTICLE_CARDS_START -->\n{cards_html}\n<!-- ARTICLE_CARDS_END -->', 
                      template, flags=re.DOTALL)
        
        return html
    
    def build(self):
        """构建整个博客站点"""
        print("🚀 开始构建博客...")
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 扫描文章
        self.scan_posts()
        print(f"📚 找到 {len(self.posts)} 篇文章")
        
        # 渲染每篇文章
        for post in self.posts:
            output_path = self.output_dir / post.url_slug / 'index.html'
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            try:
                html = self.render_article(post)
                output_path.write_text(html, encoding='utf-8')
                print(f"✅ 生成: {output_path}")
            except Exception as e:
                print(f"❌ 生成失败 {post.slug}: {e}")
        
        # 渲染首页
        try:
            index_html = self.render_index()
            (self.output_dir / 'index.html').write_text(index_html, encoding='utf-8')
            print(f"✅ 生成: index.html")
        except Exception as e:
            print(f"⚠️ 首页生成失败: {e}")
        
        # 生成文章列表 JSON（供前端使用）
        posts_json = [p.to_dict() for p in self.posts]
        (self.output_dir / 'posts.json').write_text(
            json.dumps(posts_json, indent=2, ensure_ascii=False), 
            encoding='utf-8'
        )
        print(f"✅ 生成: posts.json")
        
        print(f"\n🎉 构建完成！输出目录: {self.output_dir}")


def main():
    parser = argparse.ArgumentParser(description='Nexscope Blog Builder')
    parser.add_argument('--source', '-s', default='../blog-content', 
                        help='Markdown 源文件目录')
    parser.add_argument('--output', '-o', default='./dist', 
                        help='输出目录')
    parser.add_argument('--templates', '-t', default='.', 
                        help='模板目录')
    parser.add_argument('--watch', '-w', action='store_true', 
                        help='监听文件变化')
    
    args = parser.parse_args()
    
    builder = BlogBuilder(
        source_dir=args.source,
        output_dir=args.output,
        template_dir=args.templates
    )
    
    builder.build()


if __name__ == '__main__':
    main()
