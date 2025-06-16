# 🚀 Quick Start Guide - AI-Powered Multilingual Web Scraper

## ✅ Setup (2 minutes)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure OpenAI API key:**
   ```bash
   cp .env.example .env
   # Edit .env and add: OPENAI_API_KEY=your-actual-api-key
   ```

## 🎯 Run the Scraper

### Option 1: Simple Run
```bash
python run_scraper.py
```

### Option 2: Advanced Usage
```python
from ai_web_scraper import AIWebScraper

scraper = AIWebScraper(
    base_url="https://your-target-website.com",
    delay=1.5,  # Respectful crawling
    max_retries=3
)

scraper.scrape_website(max_pages=30)
```

## 📁 What You Get

After running, check the `final_output/` folder for:

✅ **Multilingual TXT files** - Organized content by language  
✅ **Professional PDF reports** - Beautifully formatted documents  
✅ **AI analysis summary** - Complete intelligence report  

### Example Outputs:
```
final_output/
├── mozambique_embassy_ai_analysis_english.txt    (98KB)
├── mozambique_embassy_ai_analysis_english.pdf    (32KB)
├── mozambique_embassy_ai_analysis_french.txt     (98KB)
├── mozambique_embassy_ai_analysis_french.pdf     (32KB)
├── mozambique_embassy_ai_analysis_portuguese.txt (98KB)
├── mozambique_embassy_ai_analysis_portuguese.pdf (32KB)
└── ai_processing_summary.json                    (Analysis report)
```

## 🤖 AI Features

- **Language Detection**: Automatic French/English/Portuguese detection
- **Content Categorization**: embassy_info, consular_services, tourism, etc.
- **Importance Scoring**: AI ranks content priority (1-10 scale)
- **Keyword Extraction**: Automatic topic identification
- **Smart Summarization**: AI-generated page summaries
- **Professional Output**: Clean, organized multilingual documents

## 💰 Cost

- **Typical cost**: ~$1-2 per website (depending on size)
- **Optimized prompts** minimize OpenAI API usage
- **Resume capability** prevents re-processing

## 🆘 Need Help?

1. **Check README.md** for comprehensive documentation
2. **Check logs** in `output/scraping.log` (if generated)
3. **Verify API key** is correctly set in `.env`

---

**Ready to transform multilingual web content with AI? Let's go! 🚀**