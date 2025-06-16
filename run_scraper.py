#!/usr/bin/env python3
"""
Simple script to run the AI-powered web scraper
"""

from ai_web_scraper import AIWebScraper
import os
from dotenv import load_dotenv

def main():
    """Run the AI web scraper with default configuration"""
    # Load environment variables
    load_dotenv()
    
    # Check for OpenAI API key
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ Error: OPENAI_API_KEY not found in environment variables")
        print("Please add your OpenAI API key to the .env file:")
        print("OPENAI_API_KEY=your-api-key-here")
        return
    
    print("🤖 Starting AI-Powered Web Scraper...")
    print("🎯 Target: Mozambique Embassy in France")
    print("=" * 50)
    
    # Configuration
    BASE_URL = "https://ambassademozambiquefrance.fr/"
    OUTPUT_DIR = "output"
    MAX_PAGES = 30  # Adjust as needed
    
    # Create AI scraper
    scraper = AIWebScraper(
        base_url=BASE_URL,
        output_dir=OUTPUT_DIR,
        delay=1.5  # Respectful crawling
    )
    
    # Start scraping with AI analysis
    success = scraper.scrape_website(max_pages=MAX_PAGES)
    
    if success:
        print("\n🎉 AI scraping completed successfully!")
        print("📁 Check the 'final_output' folder for multilingual AI-analyzed files")
        print("📊 Detailed logs available in: output/scraping.log")
    else:
        print("❌ Scraping encountered errors. Check logs for details.")

if __name__ == "__main__":
    main()