#!/usr/bin/env python3
"""
AI-Powered Multilingual Web Scraper
Uses OpenAI SDK to intelligently analyze and organize multilingual web content
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, parse_qs, urlencode
import os
import time
import re
import json
from datetime import datetime
from typing import Set, List, Tuple, Optional, Dict, Any
import logging
from dotenv import load_dotenv
from urllib.robotparser import RobotFileParser
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# AI Processing
try:
    import openai
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    print("Warning: OpenAI SDK not installed. AI features will be disabled.")
    print("Install with: pip install openai")

# PDF Generation
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from reportlab.pdfbase import pdfutils
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfbase import pdfmetrics
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False
    print("Warning: reportlab not installed. PDF generation will be disabled.")
    print("Install with: pip install reportlab")

# Load environment variables
load_dotenv()

class AIWebScraper:
    def __init__(self, base_url: str, output_dir: str = "output", delay: float = 1.0, 
                 max_retries: int = 3, max_file_size: int = 10*1024*1024,
                 openai_api_key: Optional[str] = None):
        """
        Initialize the AI-powered web scraper
        
        Args:
            base_url: The starting URL to scrape
            output_dir: Directory to save scraped content
            delay: Delay between requests in seconds
            max_retries: Maximum number of retries for failed requests
            max_file_size: Maximum file size to download (in bytes)
            openai_api_key: OpenAI API key for AI processing
        """
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.output_dir = output_dir
        self.delay = delay
        self.max_retries = max_retries
        self.max_file_size = max_file_size
        self.visited_urls: Set[str] = set()
        self.failed_urls: List[str] = []
        self.multilingual_content: Dict[str, List[Dict]] = {
            'english': [],
            'french': [],
            'portuguese': []
        }
        
        # Create output directories
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs("final_output", exist_ok=True)
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO, 
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(output_dir, 'scraping.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
        # Setup OpenAI client
        self.openai_client = None
        if HAS_OPENAI:
            api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                self.logger.info("✅ OpenAI AI Agent initialized successfully")
            else:
                self.logger.warning("⚠️ OpenAI API key not provided. AI features disabled.")
        
        # Setup session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"],
            backoff_factor=1
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        # Setup robots.txt parser
        self.robot_parser = RobotFileParser()
        self.robot_parser.set_url(f"{base_url.rstrip('/')}/robots.txt")
        try:
            self.robot_parser.read()
            self.logger.info("✅ Loaded robots.txt successfully")
        except Exception as e:
            self.logger.warning(f"⚠️ Could not load robots.txt: {e}")
            self.robot_parser = None
    
    def analyze_content_with_ai(self, content: str, url: str, title: str = "") -> Dict[str, Any]:
        """
        Use AI to analyze content and extract language and category information
        
        Args:
            content: Text content to analyze
            url: URL of the content
            title: Title of the page
            
        Returns:
            Dictionary with language, category, summary, and keywords
        """
        if not self.openai_client:
            return {
                'language': 'unknown',
                'category': 'general',
                'summary': content[:200] + "..." if len(content) > 200 else content,
                'keywords': [],
                'importance_score': 5
            }
        
        try:
            # Create analysis prompt
            analysis_prompt = f"""
            Analyze the following web page content and provide a JSON response with:
            1. Primary language (english, french, portuguese, or mixed)
            2. Content category (embassy_info, consular_services, about_mozambique, trade_investment, tourism, gallery, news, other)
            3. Brief summary (2-3 sentences)
            4. Key topics/keywords (max 5)
            5. Importance score (1-10, where 10 is most important)
            
            URL: {url}
            Title: {title}
            Content: {content[:3000]}
            
            Respond with valid JSON only:
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert content analyst specializing in multilingual embassy and government websites. Respond only with valid JSON."},
                    {"role": "user", "content": analysis_prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            ai_analysis = json.loads(response.choices[0].message.content)
            self.logger.info(f"🤖 AI Analysis: {url} -> {ai_analysis.get('language', 'unknown')} ({ai_analysis.get('category', 'general')})")
            
            return ai_analysis
            
        except Exception as e:
            self.logger.error(f"❌ AI analysis failed for {url}: {e}")
            return {
                'language': 'unknown',
                'category': 'general',
                'summary': content[:200] + "..." if len(content) > 200 else content,
                'keywords': [],
                'importance_score': 5
            }
    
    def translate_content_with_ai(self, content: str, target_language: str, source_language: str = "auto") -> str:
        """
        Use AI to translate content to target language
        
        Args:
            content: Content to translate
            target_language: Target language (english, french, portuguese)
            source_language: Source language (auto-detect if not specified)
            
        Returns:
            Translated content
        """
        if not self.openai_client:
            return content
        
        try:
            language_map = {
                'english': 'English',
                'french': 'French',
                'portuguese': 'Portuguese'
            }
            
            translate_prompt = f"""
            Translate the following text to {language_map[target_language]}. 
            Maintain the original formatting and structure.
            If the text is already in {language_map[target_language]}, return it unchanged.
            
            Text to translate:
            {content}
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": f"You are a professional translator. Translate content accurately to {language_map[target_language]}, preserving formatting and meaning."},
                    {"role": "user", "content": translate_prompt}
                ],
                temperature=0.1,
                max_tokens=2000
            )
            
            translated_content = response.choices[0].message.content
            self.logger.info(f"🌐 Translated content to {target_language}")
            
            return translated_content
            
        except Exception as e:
            self.logger.error(f"❌ Translation failed to {target_language}: {e}")
            return content
    
    def can_fetch(self, url: str) -> bool:
        """Check if URL can be fetched according to robots.txt"""
        if not self.robot_parser:
            return True
        
        try:
            return self.robot_parser.can_fetch(self.session.headers.get('User-Agent', '*'), url)
        except Exception as e:
            self.logger.warning(f"Error checking robots.txt for {url}: {e}")
            return True
    
    def normalize_url(self, url: str) -> str:
        """Normalize URL for consistent comparison"""
        parsed = urlparse(url)
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        if parsed.query:
            query_params = parse_qs(parsed.query, keep_blank_values=True)
            sorted_query = urlencode(sorted(query_params.items()), doseq=True)
            normalized += f"?{sorted_query}"
        
        if normalized.endswith('/') and normalized.count('/') > 3:
            normalized = normalized[:-1]
        
        return normalized
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        text = re.sub(r' +', ' ', text)
        text = re.sub(r'\t+', ' ', text)
        
        # Remove non-printable characters except newlines and tabs
        text = re.sub(r'[^\x20-\x7E\n\t\u00C0-\u017F\u1E00-\u1EFF]', '', text)
        
        # Fix common encoding issues
        replacements = {
            '\u2019': "'", '\u2018': "'", '\u201c': '"', '\u201d': '"',
            '\u2013': '-', '\u2014': '--', '\u00A0': ' '
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        return text.strip()
    
    def get_page_content(self, url: str) -> Tuple[Optional[str], Optional[BeautifulSoup], Optional[Dict]]:
        """
        Fetch and analyze a web page with AI
        
        Returns:
            Tuple of (text_content, BeautifulSoup_object, AI_analysis)
        """
        # Check robots.txt compliance
        if not self.can_fetch(url):
            self.logger.warning(f"🚫 Skipping {url} due to robots.txt restrictions")
            return None, None, None
        
        try:
            # Check content type and size
            head_response = self.session.head(url, timeout=10)
            content_type = head_response.headers.get('Content-Type', '').lower()
            
            if not any(ct in content_type for ct in ['text/html', 'text/plain', 'application/xhtml']):
                self.logger.warning(f"⏭️ Skipping {url} - not HTML content")
                return None, None, None
            
            content_length = head_response.headers.get('Content-Length')
            if content_length and int(content_length) > self.max_file_size:
                self.logger.warning(f"⏭️ Skipping {url} - file too large")
                return None, None, None
            
            # Fetch content
            response = self.session.get(url, timeout=10, stream=True)
            response.raise_for_status()
            
            # Check actual content size while downloading
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > self.max_file_size:
                    self.logger.warning(f"⏭️ Skipping {url} - content too large during download")
                    return None, None, None
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove unwanted elements
            for element in soup(["script", "style", "nav", "footer", "header", "aside"]):
                element.decompose()
            
            # Extract title
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            
            # Get text content
            text_content = soup.get_text()
            text_content = self.clean_text(text_content)
            
            # AI Analysis
            ai_analysis = self.analyze_content_with_ai(text_content, url, title)
            ai_analysis['title'] = title
            ai_analysis['url'] = url
            ai_analysis['scraped_at'] = datetime.now().isoformat()
            
            return text_content, soup, ai_analysis
            
        except requests.exceptions.RequestException as e:
            self.logger.error(f"❌ Request error fetching {url}: {str(e)}")
            self.failed_urls.append(url)
            return None, None, None
        except Exception as e:
            self.logger.error(f"❌ Unexpected error fetching {url}: {str(e)}")
            self.failed_urls.append(url)
            return None, None, None
    
    def extract_links(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """Extract internal links from a page"""
        links = []
        
        if not soup:
            return links
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            
            # Skip non-HTTP links
            if href.startswith(('mailto:', 'tel:', 'javascript:', '#')):
                continue
            
            # Convert relative URLs to absolute
            absolute_url = urljoin(current_url, href)
            parsed = urlparse(absolute_url)
            
            # Only include links from the same domain
            if parsed.netloc == self.domain:
                clean_url = self.normalize_url(absolute_url)
                links.append(clean_url)
        
        return list(set(links))
    
    def save_page_content(self, content: str, ai_analysis: Dict[str, Any]) -> str:
        """Save page content with AI analysis"""
        url = ai_analysis['url']
        
        # Create filename based on URL
        parsed = urlparse(url)
        path = parsed.path.strip('/')
        
        if not path:
            filename = "index"
        else:
            filename = re.sub(r'[<>:"/\\|?*]', '_', path)
            filename = filename.replace('/', '_')
        
        if parsed.query:
            query_part = re.sub(r'[<>:"/\\|?*]', '_', parsed.query)
            filename += f"__{query_part}"
        
        if len(filename) > 200:
            filename = filename[:200]
        
        filename += ".txt"
        filepath = os.path.join(self.output_dir, filename)
        
        # Handle duplicate filenames
        counter = 1
        original_filepath = filepath
        while os.path.exists(filepath):
            name, ext = os.path.splitext(original_filepath)
            filepath = f"{name}_{counter}{ext}"
            counter += 1
        
        # Save content with AI analysis
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"URL: {url}\n")
            f.write(f"Title: {ai_analysis.get('title', 'No title')}\n")
            f.write(f"Language: {ai_analysis.get('language', 'unknown')}\n")
            f.write(f"Category: {ai_analysis.get('category', 'general')}\n")
            f.write(f"Importance Score: {ai_analysis.get('importance_score', 5)}\n")
            f.write(f"Keywords: {', '.join(ai_analysis.get('keywords', []))}\n")
            f.write(f"Scraped on: {ai_analysis['scraped_at']}\n")
            f.write(f"AI Summary: {ai_analysis.get('summary', 'No summary available')}\n")
            f.write("=" * 80 + "\n\n")
            f.write(content)
        
        # Save metadata
        metadata_file = filepath.replace('.txt', '_metadata.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(ai_analysis, f, indent=2, ensure_ascii=False)
        
        # Add to multilingual content
        language = ai_analysis.get('language', 'unknown')
        if language in self.multilingual_content:
            self.multilingual_content[language].append({
                'filepath': filepath,
                'content': content,
                'analysis': ai_analysis
            })
        elif language == 'mixed':
            # For mixed language content, add to all languages
            for lang in self.multilingual_content:
                self.multilingual_content[lang].append({
                    'filepath': filepath,
                    'content': content,
                    'analysis': ai_analysis
                })
        
        self.logger.info(f"💾 Saved: {url} -> {filepath} ({language})")
        return filepath
    
    def scrape_website(self, max_pages: int = 100, batch_size: int = 10) -> bool:
        """
        Main scraping method with AI-powered analysis
        """
        urls_to_visit = [self.base_url]
        pages_scraped = 0
        batch_count = 0
        
        self.logger.info(f"🚀 Starting AI-powered scraping of {self.base_url}")
        self.logger.info(f"📁 Content will be saved to: {self.output_dir}")
        self.logger.info(f"📊 Max pages: {max_pages}, Batch size: {batch_size}")
        
        # Load existing progress if available
        progress_file = os.path.join(self.output_dir, 'scraping_progress.json')
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                    self.visited_urls = set(progress.get('visited_urls', []))
                    urls_to_visit = progress.get('urls_to_visit', [self.base_url])
                    pages_scraped = progress.get('pages_scraped', 0)
                    self.logger.info(f"🔄 Resumed from previous session: {pages_scraped} pages already scraped")
            except Exception as e:
                self.logger.warning(f"⚠️ Could not load progress file: {e}")
        
        while urls_to_visit and pages_scraped < max_pages:
            current_url = urls_to_visit.pop(0)
            
            if current_url in self.visited_urls:
                continue
            
            self.logger.info(f"🔍 Scraping ({pages_scraped + 1}/{max_pages}): {current_url}")
            
            # Adaptive delay based on server response
            start_time = time.time()
            
            # Get page content with AI analysis
            content, soup, ai_analysis = self.get_page_content(current_url)
            
            if content and soup and ai_analysis:
                # Save the content with AI analysis
                self.save_page_content(content, ai_analysis)
                
                # Extract new links
                new_links = self.extract_links(soup, current_url)
                
                # Add new links to queue
                for link in new_links:
                    if link not in self.visited_urls and link not in urls_to_visit:
                        urls_to_visit.append(link)
                
                pages_scraped += 1
            
            # Mark as visited
            self.visited_urls.add(current_url)
            
            # Calculate adaptive delay
            response_time = time.time() - start_time
            adaptive_delay = max(self.delay, response_time * 0.5)
            time.sleep(adaptive_delay)
            
            batch_count += 1
            
            # Save progress periodically
            if batch_count >= batch_size:
                self._save_progress(urls_to_visit, pages_scraped)
                batch_count = 0
                self.logger.info(f"💾 Progress saved at {pages_scraped} pages")
        
        # Final save
        self._save_progress(urls_to_visit, pages_scraped)
        self.save_summary()
        
        # Generate multilingual outputs
        if pages_scraped > 0:
            self.generate_multilingual_outputs()
        
        self.logger.info(f"\n✅ AI-powered scraping completed!")
        self.logger.info(f"📄 Pages scraped: {pages_scraped}")
        self.logger.info(f"❌ Failed URLs: {len(self.failed_urls)}")
        self.logger.info(f"🌐 Multilingual content organized by language")
        
        # Clean up progress file on successful completion
        if os.path.exists(progress_file):
            os.remove(progress_file)
        
        return True
    
    def _save_progress(self, urls_to_visit: List[str], pages_scraped: int) -> None:
        """Save current scraping progress for resume functionality"""
        progress = {
            'visited_urls': list(self.visited_urls),
            'urls_to_visit': urls_to_visit,
            'pages_scraped': pages_scraped,
            'last_updated': datetime.now().isoformat(),
            'multilingual_stats': {lang: len(content) for lang, content in self.multilingual_content.items()}
        }
        
        progress_file = os.path.join(self.output_dir, 'scraping_progress.json')
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, indent=2)
    
    def save_summary(self) -> str:
        """Save a comprehensive summary of the AI-powered scraping session"""
        summary = {
            'base_url': self.base_url,
            'total_pages_scraped': len(self.visited_urls),
            'failed_urls': self.failed_urls,
            'scraped_urls': list(self.visited_urls),
            'scraping_completed_at': datetime.now().isoformat(),
            'ai_analysis_enabled': self.openai_client is not None,
            'multilingual_breakdown': {
                lang: {
                    'page_count': len(content),
                    'categories': list(set([item['analysis'].get('category', 'unknown') for item in content]))
                }
                for lang, content in self.multilingual_content.items()
            }
        }
        
        summary_file = os.path.join(self.output_dir, 'ai_scraping_summary.json')
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"📊 AI scraping summary saved: {summary_file}")
        return summary_file
    
    def generate_multilingual_outputs(self) -> Dict[str, List[str]]:
        """
        Generate separate TXT and PDF files for each language
        """
        self.logger.info("🌐 Generating multilingual output files...")
        
        output_files = {'txt': [], 'pdf': []}
        
        for language, content_list in self.multilingual_content.items():
            if not content_list:
                self.logger.info(f"⏭️ No content found for {language}, skipping...")
                continue
            
            self.logger.info(f"📝 Generating {language} outputs ({len(content_list)} pages)...")
            
            # Generate TXT file
            txt_file = self._generate_language_txt(language, content_list)
            if txt_file:
                output_files['txt'].append(txt_file)
            
            # Generate PDF file
            if HAS_REPORTLAB:
                pdf_file = self._generate_language_pdf(language, content_list)
                if pdf_file:
                    output_files['pdf'].append(pdf_file)
        
        self.logger.info(f"✅ Multilingual outputs generated: {len(output_files['txt'])} TXT, {len(output_files['pdf'])} PDF files")
        return output_files
    
    def _generate_language_txt(self, language: str, content_list: List[Dict]) -> Optional[str]:
        """Generate consolidated TXT file for a specific language"""
        try:
            # Sort content by importance score and category
            sorted_content = sorted(content_list, 
                                  key=lambda x: (x['analysis'].get('importance_score', 5), 
                                               x['analysis'].get('category', 'zzz')), 
                                  reverse=True)
            
            consolidated_content = []
            
            # Add header
            lang_names = {
                'english': 'English',
                'french': 'Français',
                'portuguese': 'Português'
            }
            
            consolidated_content.extend([
                "=" * 80,
                f"EMBASSY OF THE REPUBLIC OF MOZAMBIQUE IN FRANCE",
                f"COMPLETE WEBSITE CONTENT - {lang_names.get(language, language.upper())}",
                "=" * 80,
                f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"Total pages: {len(content_list)}",
                f"Language: {lang_names.get(language, language)}",
                f"Source: {self.base_url}",
                f"AI-Powered Analysis: ✅ Enabled",
                "=" * 80,
                ""
            ])
            
            # Add table of contents
            consolidated_content.extend([
                "TABLE OF CONTENTS",
                "-" * 40
            ])
            
            for i, item in enumerate(sorted_content, 1):
                analysis = item['analysis']
                title = analysis.get('title', 'Untitled')
                category = analysis.get('category', 'general').replace('_', ' ').title()
                score = analysis.get('importance_score', 5)
                consolidated_content.append(f"{i:2d}. {title} ({category}) [Score: {score}]")
            
            consolidated_content.extend(["", "=" * 80, ""])
            
            # Add content for each page
            for i, item in enumerate(sorted_content, 1):
                analysis = item['analysis']
                content = item['content']
                
                # Translate content if necessary
                if self.openai_client and analysis.get('language') != language:
                    content = self.translate_content_with_ai(content, language, analysis.get('language', 'auto'))
                
                # Add page header
                consolidated_content.extend([
                    f"PAGE {i}: {analysis.get('title', 'Untitled').upper()}",
                    "=" * 60,
                    f"URL: {analysis['url']}",
                    f"Category: {analysis.get('category', 'general').replace('_', ' ').title()}",
                    f"Original Language: {analysis.get('language', 'unknown').title()}",
                    f"Importance Score: {analysis.get('importance_score', 5)}/10",
                    f"Keywords: {', '.join(analysis.get('keywords', []))}",
                    f"AI Summary: {analysis.get('summary', 'No summary available')}",
                    f"Scraped: {analysis['scraped_at']}",
                    "-" * 60,
                    "",
                    content,
                    "",
                    "=" * 80,
                    ""
                ])
            
            # Write consolidated text file
            filename = f"mozambique_embassy_complete_content_{language}.txt"
            output_file = os.path.join("final_output", filename)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(consolidated_content))
            
            self.logger.info(f"📄 {language.title()} TXT file saved: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"❌ Error generating {language} TXT file: {e}")
            return None
    
    def _generate_language_pdf(self, language: str, content_list: List[Dict]) -> Optional[str]:
        """Generate PDF file for a specific language"""
        if not HAS_REPORTLAB:
            return None
        
        try:
            # Sort content by importance score and category
            sorted_content = sorted(content_list, 
                                  key=lambda x: (x['analysis'].get('importance_score', 5), 
                                               x['analysis'].get('category', 'zzz')), 
                                  reverse=True)
            
            filename = f"mozambique_embassy_complete_content_{language}.pdf"
            output_file = os.path.join("final_output", filename)
            
            # Create PDF document
            doc = SimpleDocTemplate(output_file, pagesize=A4, 
                                  rightMargin=72, leftMargin=72, 
                                  topMargin=72, bottomMargin=18)
            
            # Get styles
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30,
                alignment=TA_CENTER,
                textColor='darkblue'
            )
            
            page_title_style = ParagraphStyle(
                'PageTitle',
                parent=styles['Heading2'],
                fontSize=14,
                spaceAfter=12,
                textColor='darkgreen'
            )
            
            normal_style = styles['Normal']
            normal_style.fontSize = 10
            normal_style.spaceAfter = 6
            
            # Build PDF content
            story = []
            
            lang_names = {
                'english': 'English',
                'french': 'Français',
                'portuguese': 'Português'
            }
            
            # Title page
            story.append(Paragraph("EMBASSY OF THE REPUBLIC OF MOZAMBIQUE IN FRANCE", title_style))
            story.append(Paragraph(f"Complete Website Content - {lang_names.get(language, language.title())}", title_style))
            story.append(Spacer(1, 20))
            
            # Summary information
            story.append(Paragraph(f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
            story.append(Paragraph(f"<b>Total Pages:</b> {len(content_list)}", normal_style))
            story.append(Paragraph(f"<b>Language:</b> {lang_names.get(language, language)}", normal_style))
            story.append(Paragraph(f"<b>Source:</b> {self.base_url}", normal_style))
            story.append(Paragraph(f"<b>AI-Powered Analysis:</b> ✅ Enabled", normal_style))
            story.append(Spacer(1, 20))
            
            # Table of contents
            story.append(Paragraph("TABLE OF CONTENTS", page_title_style))
            for i, item in enumerate(sorted_content, 1):
                analysis = item['analysis']
                title = analysis.get('title', 'Untitled')
                category = analysis.get('category', 'general').replace('_', ' ').title()
                score = analysis.get('importance_score', 5)
                story.append(Paragraph(f"{i}. {title} ({category}) [Score: {score}]", normal_style))
            
            story.append(PageBreak())
            
            # Add content for each page
            for i, item in enumerate(sorted_content, 1):
                analysis = item['analysis']
                content = item['content']
                
                # Translate content if necessary
                if self.openai_client and analysis.get('language') != language:
                    content = self.translate_content_with_ai(content, language, analysis.get('language', 'auto'))
                
                # Add page title
                story.append(Paragraph(f"PAGE {i}: {analysis.get('title', 'Untitled')}", page_title_style))
                
                # Add metadata
                story.append(Paragraph(f"<b>URL:</b> {analysis['url']}", normal_style))
                story.append(Paragraph(f"<b>Category:</b> {analysis.get('category', 'general').replace('_', ' ').title()}", normal_style))
                story.append(Paragraph(f"<b>Importance Score:</b> {analysis.get('importance_score', 5)}/10", normal_style))
                story.append(Paragraph(f"<b>Keywords:</b> {', '.join(analysis.get('keywords', []))}", normal_style))
                story.append(Paragraph(f"<b>AI Summary:</b> {analysis.get('summary', 'No summary available')}", normal_style))
                story.append(Spacer(1, 12))
                
                # Add content (clean up for PDF)
                clean_content = content.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                # Split content into paragraphs for better PDF formatting
                paragraphs = clean_content.split('\n\n')
                for paragraph in paragraphs:
                    if paragraph.strip():
                        story.append(Paragraph(paragraph.strip(), normal_style))
                        story.append(Spacer(1, 6))
                
                if i < len(sorted_content):  # Don't add page break after last page
                    story.append(PageBreak())
            
            # Build PDF
            doc.build(story)
            
            self.logger.info(f"📄 {language.title()} PDF file saved: {output_file}")
            return output_file
            
        except Exception as e:
            self.logger.error(f"❌ Error generating {language} PDF file: {e}")
            return None


def main():
    """Main function to run the AI-powered web scraper"""
    # Configuration
    BASE_URL = "https://ambassademozambiquefrance.fr/"
    OUTPUT_DIR = "output"
    MAX_PAGES = 30
    
    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️ Warning: OPENAI_API_KEY not found in environment variables")
        print("AI features will be limited. Set your OpenAI API key in .env file:")
        print("OPENAI_API_KEY=your-api-key-here")
        print()
    
    # Create AI-powered scraper instance
    scraper = AIWebScraper(
        base_url=BASE_URL,
        output_dir=OUTPUT_DIR,
        delay=1.5  # Respectful delay
    )
    
    # Start AI-powered scraping
    success = scraper.scrape_website(max_pages=MAX_PAGES)
    
    if success:
        print(f"\n🎉 AI-powered scraping completed successfully!")
        print(f"📁 Check the 'final_output' folder for multilingual TXT and PDF files")
        print(f"📊 Detailed logs available in: {OUTPUT_DIR}/scraping.log")
    else:
        print("❌ Scraping encountered errors. Check logs for details.")


if __name__ == "__main__":
    main()