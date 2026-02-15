import requests
import json
import time
import os
from datetime import datetime
import logging
import feedparser
from typing import List, Dict, Optional
from pytrends.request import TrendReq
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import base64
from dotenv import load_dotenv
import re
import string
from deep_translator import GoogleTranslator

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('automation.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class GeminiAI:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://generativelanguage.googleapis.com/v1"
        self.model = "models/gemini-2.5-flash"
    
    def generate_news_content(self, trend: Dict) -> Optional[str]:
        """Generate comprehensive news content using chaining method for 1000+ words"""
        try:
            # Get sources information
            sources_str = ', '.join(trend.get('sources', [])) if trend.get('sources') else 'Multiple sources'
            category = trend.get('category', 'national')
            
            # Map English category to Hindi category name
            hindi_category_mapping = {
                'world': 'अंतर्राष्ट्रीय',
                'national': 'राष्ट्रीय समाचार',
                'entertainment': 'मनोरंजन',
                'sports': 'खेल',
                'technology': 'तकनीक',
                'business': 'व्यापार',
                'education': 'शिक्षा',
                'career': 'करियर',
                'fact_check': 'फैक्ट चेक',
                'crime': 'अपराध',
                'religion': 'धर्म',
                'health': 'स्वास्थ्य',
                'interesting-news': 'रोचक खबरें',
                'वायरल': 'वायरल'
            }
            hindi_category = hindi_category_mapping.get(category, 'राष्ट्रीय समाचार')
            
            logger.info(f"Starting chained content generation for: {trend['name']}")
            
            # Step 1: Generate initial outline and headline
            outline_result = self._generate_content_outline(trend, sources_str, hindi_category)
            if not outline_result:
                logger.error("Failed to generate content outline")
                return None
            
            # Step 2: Generate detailed sections
            detailed_content = self._generate_detailed_sections(trend, outline_result, sources_str)
            if not detailed_content:
                logger.error("Failed to generate detailed sections")
                return None
            
            # Step 3: Generate conclusion and tags
            final_content = self._generate_final_content(trend, detailed_content, outline_result, hindi_category)
            if not final_content:
                logger.error("Failed to generate final content")
                return None
            
            # Step 4: Generate image prompt
            image_prompt = self._generate_image_prompt(trend, outline_result.get('headline', ''))
            
            # Combine all parts
            combined_content = f"""
HEADLINE: {outline_result.get('headline', '')}
CONTENT: {final_content}
CATEGORIES: {hindi_category}
TAGS: {outline_result.get('tags', '')}
IMAGE_PROMPT: {image_prompt}
            """.strip()
            
            logger.info(f"Successfully generated comprehensive Hindi content (1000+ words) for: {trend['name']}")
            
            # Console log the generated content
            print(f"\n{'='*60}")
            print(f"GENERATED COMPREHENSIVE HINDI CONTENT FOR: {trend['name']}")
            print(f"{'='*60}")
            print(combined_content)
            print(f"{'='*60}\n")
            
            return combined_content
                
        except Exception as e:
            logger.error(f"Error generating content with chaining method: {str(e)}")
            return None
    
    def _generate_content_outline(self, trend: Dict, sources_str: str, hindi_category: str) -> Optional[Dict]:
        """Generate initial outline and headline"""
        try:
            prompt = f"""Create a detailed Hindi news article outline for this topic:
Topic: {trend['name']}
Sources: {sources_str}
Category: {hindi_category}

CRITICAL REQUIREMENTS:
1. DO NOT include any of these in the content:
   - Category labels or category mentions
   - The headline/title within the article text
   - Fake names or fictional characters
   - Phrases like (काल्पनिक नाम) or (काल्पनिक)
   - Reporter names or bylines

2. Article Structure:
   - Generate 5-6 main sections
   - Each section: 140-200 words
   - Conclusion: 80-100 words
   - Total article: 800-900 words (strict limit)

3. Writing Style:
   - Start directly with the news/information
   - Use clear, factual Hindi language
   - Focus on real facts, quotes, and details
   - Attribute quotes to official designations/organizations (not fictional names)

4. HEADLINE REQUIREMENTS:
   - MUST create a specific, compelling headline that directly relates to the topic
   - Use the actual news content from the topic, not generic phrases
   - Make it informative and engaging
   - Do NOT use generic phrases like "Trending Topic News" or "Breaking News"
   - The headline should clearly indicate what the story is about

Format the response as:
HEADLINE:
[Write a clear, compelling, SPECIFIC headline in Hindi that directly relates to the topic]

SECTIONS:
1. [Section title - Story Introduction and Key Facts]
2. [Section title - Background and Context]
3. [Section title - Latest Developments]
4. [Section title - Impact and Analysis]
5. [Section title - Future Implications]

IMAGE_PROMPT:
[A detailed image prompt in English that captures the key visual elements of this story]"""

            url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    content = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # Parse the outline
                    parsed = self._parse_outline(content)
                    logger.info(f"Generated outline with {len(parsed.get('sections', []))} sections")
                    return parsed
                else:
                    logger.error("No outline generated in response")
                    return None
            else:
                logger.error(f"Gemini API error in outline generation: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error generating outline: {str(e)}")
            return None
    
    def _generate_detailed_sections(self, trend: Dict, outline: Dict, sources_str: str) -> Optional[str]:
        """Step 2: Generate detailed content for each section"""
        try:
            url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
            
            sections = outline.get('sections', [])
            if not sections:
                logger.error("No sections found in outline")
                return None
            
            detailed_content = ""
            
            for i, section in enumerate(sections, 1):
                logger.info(f"Generating detailed content for section {i}: {section}")
                
                # Special prompt for first section to ensure proper introduction
                if i == 1:
                    prompt = f"""
                    Write the opening section of a Hindi news article about: "{trend['name']}"
                    
                    Section: {section}
                    Sources: {sources_str}
                    
                    CRITICAL LANGUAGE REQUIREMENTS:
                    - Write ONLY in SIMPLE HINDI language that common people can understand
                    - DO NOT use any foreign words like "perkembangan", "development", etc.
                    - Use ONLY Hindi words and simple English terms that are commonly understood in India
                    - If you must use English terms, use only basic ones like "computer", "mobile", "internet"
                    - Write in proper Hindi grammar with correct Devanagari script
                    - Use simple, everyday Hindi vocabulary
                    - Do NOT include any author name, byline, (काल्पनिक नाम), or any similar text in the article.
                    
                    CRITICAL REQUIREMENTS FOR INTRODUCTION:
                    - Write 140-200 words in Hindi with proper spacing
                    - START WITH A PROPER INTRODUCTION that introduces the story
                    - Remember the total article must not exceed 900 words
                    - Begin with context like "आज एक महत्वपूर्ण खबर..." or "हाल ही में..." 
                    - Don't jump directly into facts - set the scene first
                    - Explain what happened in simple, clear language
                    - Use SIMPLE, EASY-TO-UNDERSTAND language that common people can read
                    - Use journalistic storytelling approach
                    - Include relevant facts, quotes, and context in simple terms
                    - Make it engaging and informative but not complex
                    - Use proper Hindi grammar and vocabulary but avoid difficult words
                    - Use proper spaces between words, avoid underscores
                    - Write in clear, readable paragraphs with smooth flow
                    - Be comprehensive but accessible to general readers
                    - Use conversational tone while maintaining journalistic credibility
                    - Make readers understand why this news matters
                    
                    Write only the expanded section content, no headers or formatting.
                    """
                else:
                    prompt = f"""
                    Expand this section into a detailed 140-200 word Hindi news article section:
                    
                    Topic: {trend['name']}
                    Section: {section}
                    Sources: {sources_str}
                    
                    CRITICAL LANGUAGE REQUIREMENTS:
                    - Write ONLY in SIMPLE HINDI language that common people can understand
                    - DO NOT use any foreign words like "perkembangan", "development", etc.
                    - Use ONLY Hindi words and simple English terms that are commonly understood in India
                    - If you must use English terms, use only basic ones like "computer", "mobile", "internet"
                    - Write in proper Hindi grammar with correct Devanagari script
                    - Use simple, everyday Hindi vocabulary
                    - Do NOT include any author name, byline, (काल्पनिक नाम), or any similar text in the article.
                    
                    Content Requirements:
                    - Write 150-200 words in Hindi with proper spacing
                    - Use SIMPLE, EASY-TO-UNDERSTAND language that common people can read
                    - Use journalistic style with clear storytelling approach
                    - Include relevant facts, quotes, and context in simple terms
                    - Make it engaging and informative but not complex
                    - Use proper Hindi grammar and vocabulary but avoid difficult words
                    - Connect logically to the overall topic
                    - Use proper spaces between words, avoid underscores
                    - Write in clear, readable paragraphs with smooth flow
                    - Be comprehensive but accessible to general readers
                    - Include multiple perspectives in simple language
                    - Add relevant statistics or data if applicable, but explain them clearly
                    - Provide thorough analysis but in easy-to-understand terms
                    - Include expert opinions and quotes but make them relatable
                    - Add historical context if relevant, but keep it simple
                    - Use conversational tone while maintaining journalistic credibility
                    
                    Write only the expanded section content, no headers or formatting.
                    """
                
                payload = {
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }]
                }
                
                response = requests.post(url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    if 'candidates' in result and len(result['candidates']) > 0:
                        section_content = result['candidates'][0]['content']['parts'][0]['text']
                        detailed_content += f"\n\n{section_content}\n\n"
                        logger.info(f"Generated {len(section_content.split())} words for section {i}")
                    else:
                        logger.warning(f"No content generated for section {i}")
                        detailed_content += f"\n\n{section}\n\n"
                else:
                    logger.warning(f"API error for section {i}, using fallback")
                    detailed_content += f"\n\n{section}\n\n"
                
                # Add delay between API calls
                import time
                time.sleep(1)
            
            return detailed_content.strip()
                
        except Exception as e:
            logger.error(f"Error generating detailed sections: {str(e)}")
            return None
    
    def _generate_final_content(self, trend: Dict, detailed_content: str, outline: Dict, hindi_category: str) -> Optional[str]:
        """Step 3: Generate conclusion and finalize content"""
        try:
            url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
            
            prompt = f"""
            Create a comprehensive conclusion and finalize this Hindi news article:
            
            Topic: {trend['name']}
            Category: {hindi_category}
            
            Current content:
            {detailed_content}
            
            CRITICAL LANGUAGE REQUIREMENTS:
            - Write ONLY in SIMPLE HINDI language that common people can understand
            - DO NOT use any foreign words like "perkembangan", "development", etc.
            - Use ONLY Hindi words and simple English terms that are commonly understood in India
            - If you must use English terms, use only basic ones like "computer", "mobile", "internet"
            - Write in proper Hindi grammar with correct Devanagari script
            - Use simple, everyday Hindi vocabulary
            - Do NOT include any author name, byline, (काल्पनिक नाम), or any similar text in the article.
            
            Content Requirements:
            - Write a concise 80-100 word conclusion in Hindi with proper spacing
            - Use SIMPLE, ACCESSIBLE language that common people can understand
            - Ensure the article starts with a proper introduction that sets the scene
            - Don't jump directly into facts - introduce the story first
            - Summarize key points clearly and comprehensively in easy language
            - Provide detailed future outlook and implications in simple terms
            - Use proper Hindi grammar and spacing but avoid complex vocabulary
            - Ensure total article is between 800 and 900 words
            - Use journalistic style with storytelling approach
            - Avoid underscores, use proper spaces
            - Include expert opinions and analysis but make them relatable
            - Add relevant context and background information in simple terms
            - Make it comprehensive but accessible to general readers
            - Use conversational tone while maintaining journalistic credibility
            - IMPORTANT: Include ALL the detailed content from above in the final output
            - Do not truncate or shorten the content
            - Preserve all the detailed sections and add the conclusion
            - Ensure smooth flow between sections
            
            Format the final output as:
            HEADLINE: [Clear, compelling Hindi headline that explains what happened]
            CONTENT: [Complete article content with proper paragraphs - include ALL sections + conclusion, starting with proper introduction. DO NOT include CATEGORIES, TAGS, or IMAGE_PROMPT in the content section]
            CATEGORIES: [Category name]
            TAGS: [Comma separated tags]
            IMAGE_PROMPT: [English image prompt]
            """
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    final_content = result['candidates'][0]['content']['parts'][0]['text']
                    
                    # Verify word count
                    word_count = len(final_content.split())
                    logger.info(f"Final content generated with {word_count} words")
                    
                    if word_count < 800 or word_count > 900:
                        logger.warning(f"Content is {word_count} words, outside 800-900 word target")
                    
                    return final_content
                else:
                    logger.error("No final content generated")
                    return detailed_content
            else:
                logger.error(f"Gemini API error in final content generation: {response.status_code}")
                return detailed_content
                
        except Exception as e:
            logger.error(f"Error generating final content: {str(e)}")
            return detailed_content
    
    def _generate_image_prompt(self, trend: Dict, headline: str) -> str:
        """Step 4: Generate image prompt"""
        try:
            url = f"{self.base_url}/{self.model}:generateContent?key={self.api_key}"
            
            prompt = f"""
            Generate a detailed image prompt in English for this Hindi news topic:
            
            Topic: {trend['name']}
            Headline: {headline}
            
            Requirements:
            - Create a detailed, descriptive image prompt in English
            - Focus on visual elements that represent the news story
            - Include cultural context if relevant
            - Make it suitable for AI image generation
            - Avoid text in the image
            - Be specific about composition, lighting, and mood
            
            Return only the image prompt, no additional text.
            """
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    image_prompt = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    logger.info(f"Generated image prompt: {image_prompt[:100]}...")
                    return image_prompt
                else:
                    logger.warning("No image prompt generated, using fallback")
                    return f"News image related to: {trend['name']}"
            else:
                logger.warning(f"API error for image prompt, using fallback")
                return f"News image related to: {trend['name']}"
                
        except Exception as e:
            logger.error(f"Error generating image prompt: {str(e)}")
            return f"News image related to: {trend['name']}"
    
    def _parse_outline(self, content: str) -> Dict:
        """Parse the generated outline"""
        try:
            lines = content.split('\n')
            headline = ""
            sections = []
            tags = ""
            
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('HEADLINE:'):
                    headline = line.replace('HEADLINE:', '').strip()
                elif line.startswith('SECTIONS:'):
                    current_section = 'sections'
                elif line.startswith('TAGS:'):
                    current_section = 'tags'
                    tags = line.replace('TAGS:', '').strip()
                elif current_section == 'sections' and line[0].isdigit():
                    # Extract section title
                    section_title = line.split('.', 1)[1].strip() if '.' in line else line
                    sections.append(section_title)
            
            return {
                'headline': headline,  # No fallback - must have proper headline
                'sections': sections,
                'tags': tags
            }
            
        except Exception as e:
            logger.error(f"Error parsing outline: {str(e)}")
            return {
                'headline': "",  # No fallback - will be handled by caller
                'sections': ["Background", "Current Developments", "Analysis", "Reaction", "Future"],
                'tags': "समाचार, ताजा खबर"
            }

    def parse_generated_content(self, content: str) -> Dict:
        """Parse the generated content to extract headline, content, categories, tags, and image prompt"""
        try:
            lines = content.split('\n')
            headline = ""
            article_content = ""
            categories = []
            tags = []
            image_prompt = ""
            
            current_section = None
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('HEADLINE:'):
                    current_section = 'headline'
                    headline = line.replace('HEADLINE:', '').strip()
                elif line.startswith('CONTENT:'):
                    current_section = 'content'
                elif line.startswith('CATEGORIES:'):
                    current_section = 'categories'
                    cats = line.replace('CATEGORIES:', '').strip()
                    if cats:
                        categories = [cat.strip() for cat in cats.split(',') if cat.strip()]
                elif line.startswith('TAGS:'):
                    current_section = 'tags'
                    tag_list = line.replace('TAGS:', '').strip()
                    if tag_list:
                        tags = [tag.strip() for tag in tag_list.split(',') if tag.strip()]
                elif line.startswith('IMAGE_PROMPT:'):
                    current_section = 'image_prompt'
                    image_prompt = line.replace('IMAGE_PROMPT:', '').strip()
                elif current_section == 'content':
                    # Clean the content line - replace underscores with spaces
                    cleaned_line = line.replace('_', ' ')
                    if cleaned_line:
                        article_content += cleaned_line + '\n\n'
                elif current_section == 'image_prompt':
                    image_prompt += ' ' + line
            
            # If parsing failed, return empty headline - will be handled by caller
            if not headline:
                headline = ""  # No fallback - caller must provide proper title
            if not article_content:
                # If no structured content found, clean the entire content
                article_content = content.replace('_', ' ')
            
            # Clean up the content - remove any remaining underscores and improve formatting
            article_content = article_content.replace('_', ' ')
            article_content = article_content.replace('  ', ' ')  # Remove double spaces
            
            # Remove any metadata sections that might have been included in content
            metadata_patterns = [
                r'CATEGORIES:.*?(?=\n\n|\n[A-Z]|$)',
                r'TAGS:.*?(?=\n\n|\n[A-Z]|$)',
                r'IMAGE_PROMPT:.*?(?=\n\n|\n[A-Z]|$)',
                r'CATEGORIES:.*',
                r'TAGS:.*',
                r'IMAGE_PROMPT:.*'
            ]
            
            for pattern in metadata_patterns:
                article_content = re.sub(pattern, '', article_content, flags=re.IGNORECASE | re.DOTALL)
            
            # Clean up any extra whitespace
            article_content = re.sub(r'\n\s*\n\s*\n', '\n\n', article_content)
            article_content = article_content.strip()
            
            return {
                'headline': headline,
                'content': article_content,
                'categories': categories,
                'tags': tags,
                'image_prompt': image_prompt.strip()
            }
            
        except Exception as e:
            logger.error(f"Error parsing generated content: {str(e)}")
            return {
                'headline': "",  # No fallback - caller must provide proper title
                'content': content.replace('_', ' '),
                'categories': [],
                'tags': [],
                'image_prompt': ""
            }

    def generate_news_content_with_search_grounding(self, trend: Dict) -> Optional[str]:
        """Generate news content for viral topics using Gemini with search grounding."""
        try:
            sources_str = ', '.join(trend.get('sources', [])) if trend.get('sources') else 'Multiple sources'
            category = 'वायरल'
            prompt = f"{trend['name']}\nSources: {sources_str}\nCategory: वायरल\nWrite a detailed viral news article in Hindi."
            grounding_tool = types.Tool(google_search=types.GoogleSearch())
            config = types.GenerateContentConfig(tools=[grounding_tool])
            response = genai.Client(api_key=self.api_key).models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
            if hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'candidates') and response.candidates:
                return response.candidates[0].text
            else:
                logger.error("No content generated by Gemini with search grounding.")
                return None
        except Exception as e:
            logger.error(f"Error generating viral news content with search grounding: {str(e)}")
            return None

    def generate_news_content_chained_with_search_grounding(self, trend: Dict) -> Optional[str]:
        """Generate comprehensive news content using chaining method (outline, sections, final, image prompt) with search grounding enabled for viral news."""
        try:
            sources_str = ', '.join(trend.get('sources', [])) if trend.get('sources') else 'Multiple sources'
            # For viral news, always use 'वायरल' as the Hindi category
            hindi_category = 'वायरल'
            grounding_tool = types.Tool(google_search=types.GoogleSearch())
            config = types.GenerateContentConfig(tools=[grounding_tool])
            # Step 1: Generate initial outline and headline
            outline_prompt = f"""
            Create a comprehensive outline for a detailed Hindi viral news article about: "{trend['name']}"
            This topic is trending across multiple news sources: {sources_str}
            Category: {hindi_category}
            CRITICAL LANGUAGE REQUIREMENTS:
            - Write ONLY in SIMPLE HINDI language that common people can understand
            - DO NOT use any foreign words like "perkembangan", "development", etc.
            - Use ONLY Hindi words and simple English terms that are commonly understood in India
            - If you must use English terms, use only basic ones like "computer", "mobile", "internet"
            - Write in proper Hindi grammar with correct Devanagari script
            - Use simple, everyday Hindi vocabulary
            - Do NOT include any author name, byline, (काल्पनिक नाम), or any similar text in the article.

            Content Requirements:
            - Create a compelling, clear Hindi headline that immediately tells what happened
            - Generate 5-6 main sections for a comprehensive article
            - Each section should be 140-200 words when expanded
            - Conclusion section should be 80-100 words
            - Use simple, accessible language that common people can understand
            - Follow journalistic style with clear storytelling
            - Include proper introduction, background, current developments, expert opinions, and future implications
            - Strictly ensure total article is between 800 and 900 words - do not exceed this limit
            - Generate 3-5 relevant Hindi tags
            - Make it comprehensive but easy to read

            HEADLINE REQUIREMENTS:
            - MUST create a specific, compelling headline that directly relates to the viral topic
            - Use the actual news content from the topic, not generic phrases
            - Make it informative and engaging
            - Do NOT use generic phrases like "Trending Topic News" or "Breaking News"
            - The headline should clearly indicate what the viral story is about

            Format the response as:
            HEADLINE: [Clear, compelling, SPECIFIC Hindi headline that explains what happened]
            SECTIONS:
            1. [Section title - Story Introduction and What Happened]
            2. [Section title - Background Context and Why It Matters]
            3. [Section title - Current Developments and Latest Updates]
            4. [Section title - Expert Analysis and Impact]
            5. [Section title - Future Implications and Conclusion]
            TAGS: [comma-separated Hindi tags]
            """
            outline_response = genai.Client(api_key=self.api_key).models.generate_content(
                model=self.model,
                contents=outline_prompt,
                config=config,
            )
            outline_content = outline_response.text if hasattr(outline_response, 'text') else outline_response.candidates[0].text
            outline_result = self._parse_outline(outline_content)
            if not outline_result:
                logger.error("Failed to generate content outline (viral)")
                return None
            # Step 2: Generate detailed sections
            detailed_prompt = f"""
            Expand the following outline into detailed sections for a viral Hindi news article. Use simple, accessible Hindi.\n\nOutline:\n{outline_content}\n\nSources: {sources_str}\nCategory: {hindi_category}
            """
            detailed_response = genai.Client(api_key=self.api_key).models.generate_content(
                model=self.model,
                contents=detailed_prompt,
                config=config,
            )
            detailed_content = detailed_response.text if hasattr(detailed_response, 'text') else detailed_response.candidates[0].text
            if not detailed_content:
                logger.error("Failed to generate detailed sections (viral)")
                return None
            # Step 3: Generate conclusion and tags
            final_prompt = f"""
            Write a final, well-structured viral Hindi news article using the following detailed content and outline. Add a conclusion and ensure all sections flow naturally.\n\nDetailed Content:\n{detailed_content}\n\nOutline:\n{outline_content}\n\nCategory: {hindi_category}
            """
            final_response = genai.Client(api_key=self.api_key).models.generate_content(
                model=self.model,
                contents=final_prompt,
                config=config,
            )
            final_content = final_response.text if hasattr(final_response, 'text') else final_response.candidates[0].text
            if not final_content:
                logger.error("Failed to generate final content (viral)")
                return None
            # Step 4: Generate image prompt
            image_prompt = self._generate_image_prompt(trend, outline_result.get('headline', ''))
            # Combine all parts
            combined_content = f"""
HEADLINE: {outline_result.get('headline', trend['name'])}
CONTENT: {final_content}
CATEGORIES: {hindi_category}
TAGS: {outline_result.get('tags', '')}
IMAGE_PROMPT: {image_prompt}
            """.strip()
            logger.info(f"Successfully generated comprehensive viral Hindi content (800-900 words) for: {trend['name']}")
            print(f"\n{'='*60}")
            print(f"Generated viral content for: {trend['name']}")
            print(f"{'='*60}\n")
            return combined_content
        except Exception as e:
            logger.error(f"Error in chained viral content generation with search grounding: {str(e)}")
            return None

class WordPressAPI:
    def __init__(self, site_url: str, username: str, password: str):
        self.site_url = site_url.rstrip('/')
        self.username = username
        self.password = password
        self.api_url = f"{self.site_url}/wp-json/wp/v2"
        
        import base64
        credentials = f"{username}:{password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }
    
    def create_category(self, name: str) -> Optional[int]:
        """Create a category and return its ID"""
        try:
            url = f"{self.api_url}/categories"
            payload = {"name": name}
            
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            
            if response.status_code in [201, 200]:
                category_data = response.json()
                category_id = category_data['id']
                logger.info(f"Created category '{name}' with ID: {category_id}")
                return category_id
            elif response.status_code == 400:
                # Category might already exist, try to find it
                return self.get_category_id(name)
            else:
                logger.error(f"Failed to create category '{name}': {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating category '{name}': {str(e)}")
            return None
    
    def get_category_id(self, name: str) -> Optional[int]:
        """Get category ID by name"""
        try:
            url = f"{self.api_url}/categories?search={name}"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                categories = response.json()
                for category in categories:
                    if category['name'].lower() == name.lower():
                        return category['id']
            return None
            
        except Exception as e:
            logger.error(f"Error getting category ID for '{name}': {str(e)}")
            return None
    
    def create_tag(self, name: str) -> Optional[int]:
        """Create a tag and return its ID"""
        try:
            url = f"{self.api_url}/tags"
            payload = {"name": name}
            
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            
            if response.status_code in [201, 200]:
                tag_data = response.json()
                tag_id = tag_data['id']
                logger.info(f"Created tag '{name}' with ID: {tag_id}")
                return tag_id
            elif response.status_code == 400:
                # Tag might already exist, try to find it
                return self.get_tag_id(name)
            else:
                logger.error(f"Failed to create tag '{name}': {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error creating tag '{name}': {str(e)}")
            return None
    
    def get_tag_id(self, name: str) -> Optional[int]:
        """Get tag ID by name"""
        try:
            url = f"{self.api_url}/tags?search={name}"
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                tags = response.json()
                for tag in tags:
                    if tag['name'].lower() == name.lower():
                        return tag['id']
            return None
            
        except Exception as e:
            logger.error(f"Error getting tag ID for '{name}': {str(e)}")
            return None
    
    def _create_ascii_slug(self, text: str) -> str:
        """
        Create a short, relevant, English ASCII slug from a Hindi or mixed-language title.
        Uses deep-translator to get English, then cleans and shortens.
        """
        try:
            english_text = GoogleTranslator(source='auto', target='en').translate(text)
        except Exception as e:
            # Fallback: use original text if translation fails
            english_text = text
        # Lowercase and remove punctuation
        english_text = english_text.lower()
        english_text = re.sub(f'[{re.escape(string.punctuation)}]', '', english_text)
        # Remove numbers
        english_text = re.sub(r'\d+', '', english_text)
        # Tokenize and remove stopwords
        stopwords = set([
            'the', 'a', 'an', 'and', 'or', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by', 'from',
            'is', 'are', 'was', 'were', 'be', 'been', 'has', 'have', 'had', 'as', 'that', 'this', 'these', 'those',
            'it', 'its', 'but', 'if', 'so', 'not', 'no', 'yes', 'do', 'does', 'did', 'can', 'could', 'should', 'would',
            'will', 'just', 'about', 'into', 'over', 'after', 'before', 'more', 'less', 'up', 'down', 'out', 'off', 'new', 'news', 'breaking', 'update', 'latest', 'today', 'now', 'live', 'report', 'story', 'top', 'big', 'major', 'minor', 'first', 'second', 'third', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten'
        ])
        words = [w for w in english_text.split() if w not in stopwords and w.isascii() and len(w) > 2]
        # Limit to 4-6 words
        slug_words = words[:6]
        if not slug_words:
            # Fallback: use first 3 ascii words or 'news'
            slug_words = [w for w in english_text.split() if w.isascii()][:3] or ['news']
        slug = '-'.join(slug_words)
        # Final cleanup: only keep ascii, lowercase, hyphens
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        return slug.strip('-')
    
    def _is_hindi_text(self, text: str) -> bool:
        """Check if text contains Hindi characters."""
        hindi_chars = re.findall(r'[\u0900-\u097F]', text)
        return len(hindi_chars) > 0  # If any Hindi characters are present
    
    def _create_slug_from_hindi(self, hindi_text: str) -> str:
        """Create English slug from Hindi text by extracting key information."""
        # Common Hindi to English translations for news keywords
        hindi_to_english = {
            # Countries and places
            'चीन': 'china', 'भारत': 'india', 'अमेरिका': 'america', 'रूस': 'russia',
            'पाकिस्तान': 'pakistan', 'ताइवान': 'taiwan', 'जापान': 'japan',
            'कनाडा': 'canada', 'ऑस्ट्रेलिया': 'australia', 'ब्रिटेन': 'britain',
            'फ्रांस': 'france', 'जर्मनी': 'germany', 'इटली': 'italy',
            
            # People and leaders
            'मोदी': 'modi', 'ट्रम्प': 'trump', 'पुतिन': 'putin', 'शी': 'xi',
            'बाइडन': 'biden', 'किम': 'kim', 'अमित': 'amit', 'राहुल': 'rahul',
            
            # Key events and actions
            'युद्ध': 'war', 'शांति': 'peace', 'व्यापार': 'trade', 'अर्थव्यवस्था': 'economy',
            'चुनाव': 'election', 'सरकार': 'government', 'संसद': 'parliament',
            'सेना': 'army', 'सैन्य': 'military', 'अभ्यास': 'drill', 'तैनात': 'deploy',
            'जहाज़': 'warship', 'हमला': 'attack', 'बम': 'bomb', 'आतंक': 'terror',
            'दुर्घटना': 'accident', 'मौत': 'death', 'चोट': 'injury',
            
            # Numbers and percentages
            'प्रतिशत': 'percent', 'फीसदी': 'percent', 'लाख': 'lakh', 'करोड़': 'crore',
            'मिलियन': 'million', 'बिलियन': 'billion',
            
            # Common news words
            'समाचार': 'news', 'खबर': 'news', 'रिपोर्ट': 'report', 'अध्ययन': 'study',
            'अनुसंधान': 'research', 'खोज': 'discovery', 'आविष्कार': 'invention',
            'प्रौद्योगिकी': 'technology', 'तकनीक': 'technology', 'विज्ञान': 'science',
            'शिक्षा': 'education', 'स्वास्थ्य': 'health', 'खेल': 'sports',
            'मनोरंजन': 'entertainment', 'फिल्म': 'film', 'संगीत': 'music',
            'क्रिकेट': 'cricket', 'फुटबॉल': 'football', 'टेनिस': 'tennis',
            
            # Actions and reactions
            'कहा': 'said', 'बोला': 'said', 'जवाब': 'response', 'प्रतिक्रिया': 'reaction',
            'बौखलाया': 'reacts', 'गुस्सा': 'angry', 'खुश': 'happy', 'दुखी': 'sad',
            'चिंतित': 'worried', 'आश्चर्य': 'surprise', 'डर': 'fear',
            
            # Time and dates
            'आज': 'today', 'कल': 'tomorrow', 'पिछले': 'previous', 'अगले': 'next',
            'साल': 'year', 'महीना': 'month', 'सप्ताह': 'week', 'दिन': 'day',
            
            # Common connectors (to be filtered out)
            'और': '', 'या': '', 'लेकिन': '', 'मगर': '', 'फिर': '', 'तब': '',
            'जब': '', 'क्योंकि': '', 'इसलिए': '', 'कि': '', 'का': '', 'की': '',
            'के': '', 'को': '', 'से': '', 'में': '', 'पर': '', 'तक': '', 'द्वारा': '',
            'के लिए': '', 'के बारे में': '', 'के खिलाफ': '', 'के साथ': ''
        }
        
        # Extract key words from Hindi text
        words = hindi_text.split()
        key_words = []
        
        for word in words:
            # Clean the word - remove special characters but keep Hindi and English
            clean_word = re.sub(r'[^\u0900-\u097F\u0020-\u007F]', '', word)
            
            # Check if it's a number
            if re.match(r'^\d+$', clean_word):
                key_words.append(clean_word)
                continue
            
            # Check if it's a percentage
            if re.match(r'^\d+%$', clean_word):
                key_words.append(clean_word)
                continue
            
            # Check if it's a known Hindi word
            if clean_word in hindi_to_english:
                english_word = hindi_to_english[clean_word]
                if english_word:  # Only add if not empty (filtered out connector)
                    key_words.append(english_word)
                continue
            
            # Check for partial matches (for compound words)
            for hindi_word, english_word in hindi_to_english.items():
                if hindi_word in clean_word and english_word:
                    key_words.append(english_word)
                    break
            
            # If no match found, try to extract any English words from the text
            english_words = re.findall(r'[a-zA-Z]+', clean_word)
            if english_words:
                key_words.extend(english_words)
        
        # Limit to 6-10 words
        if len(key_words) > 10:
            key_words = key_words[:10]
        elif len(key_words) < 6:
            # If we don't have enough words, add some generic ones based on context
            if any(word in ['china', 'india', 'america', 'russia'] for word in key_words):
                key_words.extend(['news', 'update'])
            elif any(word in ['war', 'attack', 'military'] for word in key_words):
                key_words.extend(['conflict', 'security'])
            elif any(word in ['election', 'government', 'politics'] for word in key_words):
                key_words.extend(['politics', 'news'])
            else:
                key_words.extend(['breaking', 'news'])
        
        # Create slug
        slug = '-'.join(key_words)
        slug = re.sub(r'[^a-z0-9-]', '', slug.lower())
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        
        logger.info(f"Generated slug from Hindi: '{hindi_text}' -> '{slug}' (key_words: {key_words})")
        return slug
    
    def _create_slug_from_english(self, english_text: str) -> str:
        """Create clean slug from English text."""
        import re
        
        # Common stop words to remove
        stop_words = {
            'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with',
            'by', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'between', 'among', 'within', 'without', 'against',
            'toward', 'towards', 'upon', 'over', 'under', 'behind', 'beneath',
            'beside', 'besides', 'beyond', 'inside', 'outside', 'underneath',
            'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
            'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
            'can', 'must', 'shall', 'this', 'that', 'these', 'those', 'i', 'you', 'he',
            'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your',
            'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'hers', 'ours', 'theirs'
        }
        
        # Convert to lowercase and split into words
        words = re.findall(r'\b[a-zA-Z0-9]+\b', english_text.lower())
        
        # Filter out stop words and short words (less than 3 characters)
        key_words = [word for word in words if word not in stop_words and len(word) >= 3]
        
        # Limit to 6-10 words
        if len(key_words) > 10:
            key_words = key_words[:10]
        elif len(key_words) < 6:
            # Add generic words if needed
            key_words.extend(['breaking', 'news'])
        
        # Create slug
        slug = '-'.join(key_words)
        slug = re.sub(r'[^a-z0-9-]', '', slug)
        slug = re.sub(r'-+', '-', slug)
        slug = slug.strip('-')
        
        logger.info(f"Generated slug from English: '{english_text}' -> '{slug}'")
        return slug

    def create_post(self, title: str, content: str, status: str = "draft", categories: List[str] = [], tags: List[str] = [], featured_media: Optional[int] = None, slug: str = None, author_id: Optional[int] = None) -> Optional[int]:
        try:
            url = f"{self.api_url}/posts"
            # Create categories and get their IDs
            category_ids = []
            for category_name in categories:
                category_id = self.create_category(category_name)
                if category_id:
                    category_ids.append(category_id)
            # Create tags and get their IDs
            tag_ids = []
            for tag_name in tags:
                tag_id = self.create_tag(tag_name)
                if tag_id:
                    tag_ids.append(tag_id)
            payload = {
                "title": title,
                "content": content,
                "status": status,
                "format": "standard",
                "categories": category_ids,
                "tags": tag_ids,
                "featured_media": featured_media
            }
            
            # Add author ID if provided
            if author_id:
                payload["author"] = author_id
            if slug:
                payload["slug"] = slug
            response = requests.post(url, json=payload, headers=self.headers, timeout=30)
            if response.status_code in [201, 200]:
                post_data = response.json()
                post_id = post_data['id']
                logger.info(f"Successfully created WordPress post with ID: {post_id}")
                logger.info(f"Categories: {categories}")
                logger.info(f"Tags: {tags}")
                return post_id
            else:
                logger.error(f"Failed to create WordPress post: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error creating WordPress post: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        try:
            url = f"{self.api_url}/posts"
            response = requests.get(url, headers=self.headers, timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"WordPress connection test failed: {str(e)}")
            return False
    
    def upload_image(self, image_data: str, title: str, caption: str = "", ascii_slug: str = None, alt_text: str = "") -> Optional[int]:
        """Upload image to WordPress and return media ID"""
        try:
            if not image_data:
                logger.warning("No image data provided for upload")
                return None
            # Convert Base64 image to bytes
            image_bytes = base64.b64decode(image_data)
            # Compress and resize the image
            compressed_image_bytes = self._compress_image(image_bytes)
            # Create filename from ASCII slug if provided, else from title
            if ascii_slug:
                filename = ascii_slug + "-featured.jpg"
            else:
                filename = self._create_slug(title) + "-featured.jpg"
            # Prepare the upload
            url = f"{self.api_url}/media"
            # Create multipart form data properly
            files = {
                'file': (filename, compressed_image_bytes, 'image/jpeg')
            }
            # Remove Content-Type header for multipart upload
            upload_headers = self.headers.copy()
            if 'Content-Type' in upload_headers:
                del upload_headers['Content-Type']
            # Upload the image
            response = requests.post(url, files=files, headers=upload_headers, timeout=30)
            if response.status_code in [201, 200]:
                media_data = response.json()
                media_id = media_data['id']
                image_url = media_data['source_url']
                logger.info(f"Successfully uploaded image with ID: {media_id}")
                logger.info(f"Image URL: {image_url}")
                
                # Update the image with alt text if provided
                if alt_text:
                    self._update_image_alt_text(media_id, alt_text)
                
                return media_id
            else:
                logger.error(f"Failed to upload image: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            logger.error(f"Error uploading image: {str(e)}")
            return None
    
    def _update_image_alt_text(self, media_id: int, alt_text: str) -> bool:
        """Update the alt text for an uploaded image"""
        try:
            url = f"{self.api_url}/media/{media_id}"
            data = {
                'alt_text': alt_text
            }
            response = requests.post(url, json=data, headers=self.headers, timeout=30)
            if response.status_code in [200, 201]:
                logger.info(f"Successfully updated alt text for image {media_id}: {alt_text}")
                return True
            else:
                logger.warning(f"Failed to update alt text for image {media_id}: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Error updating alt text for image {media_id}: {str(e)}")
            return False
    
    def _compress_image(self, image_bytes: bytes) -> bytes:
        """Compress and resize image to reduce file size"""
        try:
            # Open image from bytes
            image = Image.open(BytesIO(image_bytes))
            
            # Convert to RGB if necessary (remove alpha channel)
            if image.mode in ('RGBA', 'LA', 'P'):
                # Create a white background
                background = Image.new('RGB', image.size, (255, 255, 255))
                if image.mode == 'P':
                    image = image.convert('RGBA')
                background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
                image = background
            
            # Resize image to reasonable dimensions (max 1920x1080)
            max_width = 1920
            max_height = 1080
            
            # Calculate new dimensions maintaining aspect ratio
            width, height = image.size
            if width > max_width or height > max_height:
                ratio = min(max_width / width, max_height / height)
                new_width = int(width * ratio)
                new_height = int(height * ratio)
                image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
            
            # Compress image with high quality but reasonable file size
            output_buffer = BytesIO()
            image.save(output_buffer, format='JPEG', quality=85, optimize=True)
            compressed_bytes = output_buffer.getvalue()
            
            # Log compression results
            original_size = len(image_bytes)
            compressed_size = len(compressed_bytes)
            compression_ratio = (1 - compressed_size / original_size) * 100
            
            logger.info(f"Image compressed: {original_size:,} bytes → {compressed_size:,} bytes ({compression_ratio:.1f}% reduction)")
            
            return compressed_bytes
            
        except Exception as e:
            logger.error(f"Error compressing image: {str(e)}")
            # Return original bytes if compression fails
            return image_bytes
    
    def _create_slug(self, title: str) -> str:
        """Create a URL-friendly slug from title"""
        import re
        # Remove special characters and convert to lowercase
        slug = re.sub(r'[^\w\s-]', '', title.lower())
        # Replace spaces with hyphens
        slug = re.sub(r'[-\s]+', '-', slug)
        # Remove leading/trailing hyphens
        slug = slug.strip('-')
        return slug

class RSSTrendsAPI:
    def __init__(self):
        # RSS feeds for Hindi news sources
        self.rss_feeds = {
            'bhaskar': [
                "https://www.bhaskar.com/rss-v1--category-1061.xml",
                "https://www.bhaskar.com/rss-v1--category-1125.xml", 
                "https://www.bhaskar.com/rss-v1--category-3998.xml",
                "https://www.bhaskar.com/rss-v1--category-11945.xml",
                "https://www.bhaskar.com/rss-v1--category-5707.xml",
                "https://www.bhaskar.com/rss-v1--category-1053.xml",
                "https://www.bhaskar.com/rss-v1--category-1051.xml"  # Business news
            ],
            'ndtv': [
                "https://feeds.feedburner.com/ndtvnews-world-news",
                "https://feeds.feedburner.com/ndtvnews-india-news",
                "https://feeds.feedburner.com/ndtvnews-entertainment",
                "https://feeds.feedburner.com/ndtvprofit-latest", # Business/profit news
                "https://feeds.feedburner.com/ndtvmovies-latest"  # Movies news
            ],
            'indiatv': [
                "https://www.indiatv.in/rssnews/topstory-world.xml",
                "https://www.indiatv.in/rssnews/topstory-india.xml",
                "https://www.indiatv.in/rssnews/topstory-entertainment.xml",
                "https://www.indiatv.in/rssnews/topstory-education.xml",
                "https://www.indiatv.in/rssnews/topstory-tech.xml",
                "https://www.indiatv.in/rssnews/topstory-education/sarkari-naukri.xml",
                "https://www.indiatv.in/rssnews/topstory-paisa.xml",  # Business/money news
                "https://www.indiatv.in/rssnews/topstory-fact-check.xml",  # Fact check
                "https://www.indiatv.in/rssnews/topstory-crime.xml",  # Crime news
                "https://www.indiatv.in/rssnews/topstory-religion.xml",  # Religion news
                "https://www.indiatv.in/rssnews/topstory-health.xml"  # Health news
            ],
            'news18': [
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/nation/nation.xml",
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/entertainment/entertainment.xml",
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/career/career-career.xml",
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/sports/football.xml",
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/sports/tennis.xml",
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/tech/tech.xml",
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/sports/cricket.xml",
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/tech/apps.xml",
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/business/innovation.xml",
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/business/online-business.xml",  # Online business
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/business/business.xml",  # General business
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/business/money-making-tips.xml",  # Money making tips
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/tech/launch-review.xml",  # Tech launch reviews
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/entertainment/bollywood.xml",  # Bollywood news
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/entertainment/hollywood.xml",  # Hollywood news
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/shows/shows.xml"  # TV shows
            ],
            'abplive': [
                "https://www.abplive.com/education/feed",
                "https://www.abplive.com/technology/feed",
                "https://www.abplive.com/education/jobs/feed",
                "https://www.abplive.com/sports/feed",
                "https://www.abplive.com/sports/ipl/feed",
                "https://www.abplive.com/news/world/feed",
                "https://www.abplive.com/technology/gadgets/feed",
                "https://www.abplive.com/business/feed",  # Business news
                "https://www.abplive.com/fact-check/feed",  # Fact check
                "https://www.abplive.com/entertainment/bollywood/feed",  # Bollywood news
                "https://www.abplive.com/entertainment/television/feed",  # TV news
                "https://www.abplive.com/entertainment/tamil-cinema/feed",  # Tamil cinema
                "https://www.abplive.com/entertainment/bhojpuri-cinema/feed"  # Bhojpuri cinema
            ],
            'amarujala': [
                "https://www.amarujala.com/rss/podcast/tech-talk.xml",
                "https://www.amarujala.com/rss/podcast/karobar-ka-bazar.xml"  # Business market news
            ],
            'gadgets360': [
                "https://feeds.feedburner.com/gadgets360-latest"
            ],
            'oneindia': [
                "https://hindi.oneindia.com/rss/feeds/hindi-politics-fb.xml",
                "https://hindi.oneindia.com/rss/feeds/artificial-intelligence-fb.xml",
                "https://hindi.oneindia.com/rss/feeds/hindi-sports-fb.xml",
                "https://hindi.oneindia.com/rss/feeds/hindi-entertainment-fb.xml"
            ],
            'livehindustan': [
                "https://api.livehindustan.com/feeds/rss/gadgets/smartphones-tabs/rssfeed.xml",
                "https://api.livehindustan.com/feeds/rss/gadgets/laptops-pc/rssfeed.xml",
                "https://api.livehindustan.com/feeds/rss/gadgets/apps/rssfeed.xml",
                "https://api.livehindustan.com/feeds/rss/career/education/rssfeed.xml",
                "https://api.livehindustan.com/feeds/rss/career/jobs/rssfeed.xml",
                "https://api.livehindustan.com/feeds/rss/career/exams/rssfeed.xml",
                "https://api.livehindustan.com/feeds/rss/career/admission/rssfeed.xml",
                "https://api.livehindustan.com/feeds/rss/budget/business/rssfeed.xml"  # Business budget news
            ],
            'navbharattimes': [
                "https://navbharattimes.indiatimes.com/rssfeedsdefault.cms"  # General news
            ],
            'zeenews': [
                "https://zeenews.india.com/rss/business.xml",  # Business news
                "https://zeenews.india.com/rss/india.xml",  # India news
                "https://zeenews.india.com/rss/world.xml"  # World news
            ],
            'navjivanindia': [
                "https://www.navjivanindia.com/stories.rss",  # General news
                "https://www.navjivanindia.com/stories.rss?section=news",  # News section
                "https://www.navjivanindia.com/stories.rss?section=india",  # India news
                "https://www.navjivanindia.com/stories.rss?section=politics",  # Politics
                "https://www.navjivanindia.com/stories.rss?section=crime",  # Crime
                "https://www.navjivanindia.com/stories.rss?section=entertainment",  # Entertainment
                "https://www.navjivanindia.com/stories.rss?section=cinema",  # Cinema
                "https://www.navjivanindia.com/stories.rss?section=international",  # International
                "https://www.navjivanindia.com/stories.rss?section=economy",  # Economy
                "https://www.navjivanindia.com/stories.rss?section=sports",  # Sports
                "https://www.navjivanindia.com/stories.rss?section=education"  # Education
            ],
            'viral': [
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/ajab-gajab.xml",
                "https://www.bhaskar.com/rss-v1--category-10891.xml",
                "https://www.navjivanindia.com/stories.rss?section=social-viral"
            ],
            'uttarpradesh': [
                "https://www.amarujala.com/rss/uttar-pradesh.xml",
                "https://www.bhaskar.com/rss-v1--category-2052.xml",
                "https://hindi.news18.com/commonfeeds/v1/hin/rss/uttar-pradesh/uttar-pradesh.xml",
                "https://timesofindia.indiatimes.com/rssfeeds/-2128819658.cms"
            ],
        }
        
        # Category mapping for different news sources
        self.category_mapping = {
            'world': ['विश्व', 'वर्ल्ड', 'अंतरराष्ट्रीय', 'अंतर्राष्ट्रीय', 'इंटरनेशनल', 'world', 'international', 'अमेरिका', 'america', 'टैरिफ', 'tariff', 'ट्रम्प', 'trump', 'चीन', 'china', 'पाकिस्तान', 'pakistan', 'यूक्रेन', 'ukraine', 'रूस', 'russia'],
            'national': ['राष्ट्रीय', 'देश', 'नेशनल', 'national', 'india', 'भारत', 'राजनीति', 'politics', 'गुजरात', 'gujarat', 'पुल', 'bridge', 'मोदी', 'modi', 'सरकार', 'government', 'मंत्री', 'minister', 'चुनाव', 'election', 'संसद', 'parliament', 'लोकसभा', 'loksabha', 'राज्यसभा', 'rajyasabha'],
            'entertainment': ['मनोरंजन', 'एंटरटेनमेंट', 'entertainment', 'बॉलीवुड', 'bollywood', 'फिल्म', 'film', 'अभिनेता', 'actor', 'अभिनेत्री', 'actress', 'श्रीदेवी', 'sridevi', 'यश', 'yash', 'शहाना', 'shahana', 'अक्षय', 'akshay', 'शाहरुख', 'shahrukh', 'सलमान', 'salman', 'आमिर', 'aamir', 'सिनेमा', 'cinema', 'टीवी', 'tv', 'सीरियल', 'serial'],
            'sports': ['खेल', 'स्पोर्ट्स', 'sports', 'क्रिकेट', 'cricket', 'फुटबॉल', 'football', 'टेनिस', 'tennis', 'आईपीएल', 'ipl', 'गेम', 'game', 'मैच', 'match', 'टूर्नामेंट', 'tournament', 'ओलंपिक', 'olympic', 'विश्वकप', 'worldcup', 'बैडमिंटन', 'badminton', 'हॉकी', 'hockey'],
            'business': ['व्यापार', 'बिजनेस', 'business', 'company', 'कंपनी', 'शेयर', 'share', 'बाजार', 'market', 'अर्थव्यवस्था', 'economy', 'निवेश', 'investment'],
            'technology': ['तकनीक', 'टेक्नोलॉजी', 'technology', 'टेक', 'tech', 'कंप्यूटर', 'computer', 'स्मार्टफोन', 'smartphone', 'मोबाइल', 'mobile', 'लैपटॉप', 'laptop', 'इंटरनेट', 'internet', 'सॉफ्टवेयर', 'software', 'ऐप', 'app', 'आर्टिफिशियल इंटेलिजेंस', 'artificial intelligence', 'एआई', 'ai', 'मशीन लर्निंग', 'machine learning', 'डेटा', 'data', 'बिग डेटा', 'big data', 'क्लाउड', 'cloud', 'साइबर', 'cyber', 'साइबर सुरक्षा', 'cybersecurity', 'हैकिंग', 'hacking', 'साइबर अपराध', 'cybercrime', 'डिजिटल', 'digital', 'डिजिटल इंडिया', 'digital india', 'ई-गवर्नेंस', 'e-governance', 'ई-कॉमर्स', 'e-commerce', 'ऑनलाइन', 'online', 'वेब', 'web', 'वेबसाइट', 'website', 'सोशल मीडिया', 'social media', 'फेसबुक', 'facebook', 'ट्विटर', 'twitter', 'इंस्टाग्राम', 'instagram', 'यूट्यूब', 'youtube', 'व्हाट्सऐप', 'whatsapp', 'टेलीग्राम', 'telegram', 'सिग्नल', 'signal', 'ब्लॉकचेन', 'blockchain', 'क्रिप्टो', 'crypto', 'बिटकॉइन', 'bitcoin', 'एथेरियम', 'ethereum', 'निफ्टी', 'nft', 'मेटावर्स', 'metaverse', 'वर्चुअल रियलिटी', 'virtual reality', 'वीआर', 'vr', 'ऑगमेंटेड रियलिटी', 'augmented reality', 'एआर', 'ar', '5जी', '5g', '6जी', '6g', 'वाई-फाई', 'wifi', 'ब्लूटूथ', 'bluetooth', 'गैलेक्सी', 'galaxy', 'आईफोन', 'iphone', 'एंड्रॉइड', 'android', 'आईओएस', 'ios', 'माइक्रोसॉफ्ट', 'microsoft', 'गूगल', 'google', 'एप्पल', 'apple', 'अमेज़न', 'amazon', 'फ्लिपकार्ट', 'flipkart', 'पेटीएम', 'paytm', 'फोनपे', 'phonepay', 'गूगल पे', 'google pay', 'यूपीआई', 'upi', 'डिजिटल पेमेंट', 'digital payment', 'ऑनलाइन पेमेंट', 'online payment', 'स्टार्टअप', 'startup', 'यूनिकॉर्न', 'unicorn', 'फिनटेक', 'fintech', 'एडटेक', 'edtech', 'हेल्थटेक', 'healthtech', 'एग्रीटेक', 'agritech', 'क्लीनटेक', 'cleantech', 'प्रोडक्ट', 'product', 'सर्विस', 'service', 'प्लेटफॉर्म', 'platform', 'एपीआई', 'api', 'सीएसएस', 'css', 'एचटीएमएल', 'html', 'जावास्क्रिप्ट', 'javascript', 'पायथन', 'python', 'जावा', 'java', 'सी++', 'c++', 'सी#', 'c#', 'पीएचपी', 'php', 'रूबी', 'ruby', 'गो', 'go', 'रस्ट', 'rust', 'स्विफ्ट', 'swift', 'कोटलिन', 'kotlin', 'डेवलपर', 'developer', 'प्रोग्रामर', 'programmer', 'कोडर', 'coder', 'हैकर', 'hacker', 'साइबर एक्सपर्ट', 'cyber expert', 'आईटी', 'it', 'आईटी सेक्टर', 'it sector', 'टेक कंपनी', 'tech company', 'सिलिकन वैली', 'silicon valley', 'बेंगलुरु', 'bangalore', 'हैदराबाद', 'hyderabad', 'पुणे', 'pune', 'गुड़गांव', 'gurgaon', 'नोएडा', 'noida', 'टेक हब', 'tech hub', 'आईटी पार्क', 'it park', 'सॉफ्टवेयर पार्क', 'software park', 'टेक्नोलॉजी पार्क', 'technology park', 'इनोवेशन', 'innovation', 'इनोवेटिव', 'innovative', 'डिस्रप्टिव', 'disruptive', 'डिस्रप्टिव टेक्नोलॉजी', 'disruptive technology', 'इमर्जिंग टेक्नोलॉजी', 'emerging technology', 'फ्यूचर टेक्नोलॉजी', 'future technology', 'नेक्स्ट जेनरेशन', 'next generation', 'जनरेशन', 'generation', 'जीपीयू', 'gpu', 'सीपीयू', 'cpu', 'रैम', 'ram', 'स्टोरेज', 'storage', 'हार्ड डिस्क', 'hard disk', 'एसएसडी', 'ssd', 'प्रोसेसर', 'processor', 'चिप', 'chip', 'सेमीकंडक्टर', 'semiconductor', 'माइक्रोचिप', 'microchip', 'इंटेल', 'intel', 'एएमडी', 'amd', 'क्वालकॉम', 'qualcomm', 'मीडियाटेक', 'mediatek', 'एनवीडिया', 'nvidia', 'टेस्ला', 'tesla', 'स्पेसएक्स', 'spacex', 'नेटफ्लिक्स', 'netflix', 'स्पॉटिफाई', 'spotify', 'जूम', 'zoom', 'स्लैक', 'slack', 'डिस्कॉर्ड', 'discord', 'टेलीग्राम', 'telegram', 'सिग्नल', 'signal', 'व्हाट्सऐप', 'whatsapp', 'इंस्टाग्राम', 'instagram', 'फेसबुक', 'facebook', 'ट्विटर', 'twitter', 'लिंक्डइन', 'linkedin', 'यूट्यूब', 'youtube', 'टिकटॉक', 'tiktok', 'स्नैपचैट', 'snapchat', 'पिंटरेस्ट', 'pinterest', 'रेडिट', 'reddit', 'क्वोरा', 'quora', 'स्टैक ओवरफ्लो', 'stack overflow', 'गिटहब', 'github', 'गिटलैब', 'gitlab', 'बिटबकेट', 'bitbucket', 'जीरा', 'jira', 'कन्फ्लुएंस', 'confluence', 'ट्रेलो', 'trello', 'एसएलएकी', 'slack', 'माइक्रोसॉफ्ट टीम्स', 'microsoft teams', 'जूम', 'zoom', 'गूगल मीट', 'google meet', 'स्काइप', 'skype', 'वेबेक्स', 'webex', 'गूगल क्लासरूम', 'google classroom', 'ज़ूम क्लासरूम', 'zoom classroom', 'ऑनलाइन एजुकेशन', 'online education', 'ई-लर्निंग', 'e-learning', 'डिजिटल एजुकेशन', 'digital education', 'हाइब्रिड एजुकेशन', 'hybrid education', 'रिमोट वर्क', 'remote work', 'वर्क फ्रॉम होम', 'work from home', 'हाइब्रिड वर्क', 'hybrid work', 'डिजिटल वर्क', 'digital work', 'ऑनलाइन वर्क', 'online work', 'टेक जॉब', 'tech job', 'आईटी जॉब', 'it job', 'सॉफ्टवेयर जॉब', 'software job', 'डेवलपर जॉब', 'developer job', 'प्रोग्रामर जॉब', 'programmer job', 'टेक सैलरी', 'tech salary', 'आईटी सैलरी', 'it salary', 'सॉफ्टवेयर सैलरी', 'software salary', 'टेक इंटरव्यू', 'tech interview', 'आईटी इंटरव्यू', 'it interview', 'सॉफ्टवेयर इंटरव्यू', 'software interview', 'टेक कैरियर', 'tech career', 'आईटी कैरियर', 'it career', 'सॉफ्टवेयर कैरियर', 'software career', 'टेक स्किल', 'tech skill', 'आईटी स्किल', 'it skill', 'सॉफ्टवेयर स्किल', 'software skill', 'प्रोग्रामिंग स्किल', 'programming skill', 'कोडिंग स्किल', 'coding skill', 'टेक ट्रेनिंग', 'tech training', 'आईटी ट्रेनिंग', 'it training', 'सॉफ्टवेयर ट्रेनिंग', 'software training', 'प्रोग्रामिंग ट्रेनिंग', 'programming training', 'कोडिंग ट्रेनिंग', 'coding training', 'टेक कोर्स', 'tech course', 'आईटी कोर्स', 'it course', 'सॉफ्टवेयर कोर्स', 'software course', 'प्रोग्रामिंग कोर्स', 'programming course', 'कोडिंग कोर्स', 'coding course', 'टेक सर्टिफिकेशन', 'tech certification', 'आईटी सर्टिफिकेशन', 'it certification', 'सॉफ्टवेयर सर्टिफिकेशन', 'software certification', 'प्रोग्रामिंग सर्टिफिकेशन', 'programming certification', 'कोडिंग सर्टिफिकेशन', 'coding certification'],
            'education': ['शिक्षा', 'education', 'स्कूल', 'school', 'कॉलेज', 'college', 'यूनिवर्सिटी', 'university', 'परीक्षा', 'exam', 'छात्र', 'student', 'शिक्षक', 'teacher'],
            'career': ['करियर', 'career', 'नौकरी', 'job', 'रोजगार', 'employment', 'सरकारी नौकरी', 'sarkari naukri'],
            'fact_check': ['फैक्ट चेक', 'fact check', 'फैक्ट', 'fact', 'जांच', 'verify', 'सत्यापन', 'verification'],
            'crime': ['अपराध', 'crime', 'हत्या', 'murder', 'चोरी', 'theft', 'डकैती', 'robbery', 'बलात्कार', 'rape', 'हमला', 'attack', 'गिरफ्तार', 'arrest', 'पुलिस', 'police', 'थाना', 'police station', 'मुकदमा', 'case', 'अदालत', 'court', 'जेल', 'jail', 'कैद', 'prison', 'सजा', 'punishment', 'फांसी', 'hanging', 'मौत', 'death', 'शव', 'dead body', 'खून', 'blood', 'हिंसा', 'violence', 'आतंक', 'terror', 'आतंकवाद', 'terrorism', 'बम', 'bomb', 'फायरिंग', 'firing', 'गोली', 'bullet', 'चाकू', 'knife', 'छुरा', 'dagger', 'मारपीट', 'assault', 'धमकी', 'threat', 'खतरा', 'danger', 'अपहरण', 'kidnapping', 'अगवा', 'abduction', 'फिरौती', 'ransom', 'लूट', 'loot', 'धोखा', 'fraud', 'घोटाला', 'scam', 'भ्रष्टाचार', 'corruption', 'रिश्वत', 'bribe', 'कालाबाजारी', 'black marketing', 'नकली', 'fake', 'जालसाजी', 'forgery', 'झूठ', 'lie', 'झूठा', 'false', 'गलत', 'wrong', 'अवैध', 'illegal', 'गैरकानूनी', 'unlawful'],
            'religion': ['धर्म', 'religion', 'पूजा', 'worship', 'मंदिर', 'temple', 'मस्जिद', 'mosque', 'गुरुद्वारा', 'gurudwara', 'चर्च', 'church', 'ईश्वर', 'god', 'भगवान', 'bhagwan', 'अल्लाह', 'allah', 'जीसस', 'jesus', 'कृष्ण', 'krishna', 'राम', 'ram', 'शिव', 'shiva', 'दुर्गा', 'durga', 'लक्ष्मी', 'lakshmi', 'सरस्वती', 'saraswati', 'गणेश', 'ganesh', 'हनुमान', 'hanuman', 'बुद्ध', 'buddha', 'महावीर', 'mahavir', 'गुरु', 'guru', 'संत', 'saint', 'साधु', 'sadhu', 'पंडित', 'pandit', 'मौलवी', 'maulvi', 'पादरी', 'priest', 'पुरोहित', 'purohit', 'पूजारी', 'pujari', 'आरती', 'aarti', 'भजन', 'bhajan', 'कीर्तन', 'kirtan', 'प्रार्थना', 'prayer', 'नमाज', 'namaz', 'व्रत', 'fast', 'उपवास', 'upvas', 'पूजा', 'puja', 'हवन', 'havan', 'यज्ञ', 'yagya', 'मंत्र', 'mantra', 'श्लोक', 'shlok', 'वेद', 'veda', 'पुराण', 'purana', 'गीता', 'geeta', 'कुरान', 'quran', 'बाइबिल', 'bible', 'गुरुग्रंथ', 'gurugranth', 'रामायण', 'ramayan', 'महाभारत', 'mahabharat', 'रामचरितमानस', 'ramcharitmanas', 'हिंदू', 'hindu', 'मुस्लिम', 'muslim', 'सिख', 'sikh', 'ईसाई', 'christian', 'जैन', 'jain', 'बौद्ध', 'buddhist', 'पारसी', 'parsi', 'यहूदी', 'jewish', 'धार्मिक', 'religious', 'आध्यात्मिक', 'spiritual', 'मोक्ष', 'moksha', 'निर्वाण', 'nirvana', 'स्वर्ग', 'heaven', 'नरक', 'hell', 'पुनर्जन्म', 'rebirth', 'कर्म', 'karma', 'धर्म', 'dharma', 'अधर्म', 'adharma', 'पाप', 'sin', 'पुण्य', 'virtue', 'शुभ', 'auspicious', 'अशुभ', 'inauspicious', 'मंगल', 'mangal', 'अमंगल', 'amangal', 'शुभ मुहूर्त', 'auspicious time', 'अशुभ मुहूर्त', 'inauspicious time', 'पंचांग', 'panchang', 'ज्योतिष', 'astrology', 'हस्तरेखा', 'palmistry', 'कुंडली', 'kundali', 'राशि', 'zodiac', 'नक्षत्र', 'nakshatra', 'ग्रह', 'planet', 'सूर्य', 'sun', 'चंद्र', 'moon', 'मंगल', 'mars', 'बुध', 'mercury', 'गुरु', 'jupiter', 'शुक्र', 'venus', 'शनि', 'saturn', 'राहु', 'rahu', 'केतु', 'ketu'],
            'health': ['स्वास्थ्य', 'health', 'मेडिकल', 'medical', 'डॉक्टर', 'doctor', 'हॉस्पिटल', 'hospital', 'दवा', 'medicine', 'इलाज', 'treatment', 'बीमारी', 'disease', 'रोग', 'illness', 'संक्रमण', 'infection', 'वायरस', 'virus', 'बैक्टीरिया', 'bacteria', 'जीवाणु', 'germ', 'फ्लू', 'flu', 'बुखार', 'fever', 'खांसी', 'cough', 'जुकाम', 'cold', 'सिरदर्द', 'headache', 'दर्द', 'pain', 'चोट', 'injury', 'घाव', 'wound', 'फ्रैक्चर', 'fracture', 'सर्जरी', 'surgery', 'ऑपरेशन', 'operation', 'टीका', 'vaccine', 'इंजेक्शन', 'injection', 'टेस्ट', 'test', 'एक्सरे', 'xray', 'सीटी स्कैन', 'ct scan', 'एमआरआई', 'mri', 'ब्लड टेस्ट', 'blood test', 'डायबिटीज', 'diabetes', 'हृदय', 'heart', 'दिल', 'heart', 'कैंसर', 'cancer', 'टीबी', 'tb', 'एड्स', 'aids', 'कोविड', 'covid', 'कोरोना', 'corona', 'महामारी', 'pandemic', 'एपिडेमिक', 'epidemic', 'स्वास्थ्य मंत्रालय', 'health ministry', 'आयुष', 'ayush', 'आयुर्वेद', 'ayurveda', 'योग', 'yoga', 'प्राणायाम', 'pranayam', 'ध्यान', 'meditation', 'एक्यूपंक्चर', 'acupuncture', 'होम्योपैथी', 'homeopathy', 'एलोपैथी', 'allopathy', 'फिजियोथेरेपी', 'physiotherapy', 'मनोचिकित्सा', 'psychiatry', 'मनोविज्ञान', 'psychology', 'तनाव', 'stress', 'अवसाद', 'depression', 'चिंता', 'anxiety', 'मानसिक स्वास्थ्य', 'mental health', 'शारीरिक स्वास्थ्य', 'physical health', 'पोषण', 'nutrition', 'आहार', 'diet', 'विटामिन', 'vitamin', 'प्रोटीन', 'protein', 'कार्बोहाइड्रेट', 'carbohydrate', 'वसा', 'fat', 'फाइबर', 'fiber', 'खनिज', 'mineral', 'कैल्शियम', 'calcium', 'आयरन', 'iron', 'विटामिन डी', 'vitamin d', 'विटामिन सी', 'vitamin c', 'विटामिन बी', 'vitamin b', 'फोलिक एसिड', 'folic acid', 'ओमेगा 3', 'omega 3', 'एंटीऑक्सिडेंट', 'antioxidant', 'इम्यूनिटी', 'immunity', 'प्रतिरक्षा', 'immune system', 'मेटाबॉलिज्म', 'metabolism', 'पाचन', 'digestion', 'पेट', 'stomach', 'आंत', 'intestine', 'लिवर', 'liver', 'किडनी', 'kidney', 'फेफड़े', 'lungs', 'दिमाग', 'brain', 'मस्तिष्क', 'brain', 'तंत्रिका', 'nerve', 'मांसपेशी', 'muscle', 'हड्डी', 'bone', 'त्वचा', 'skin', 'बाल', 'hair', 'आंख', 'eye', 'कान', 'ear', 'नाक', 'nose', 'मुंह', 'mouth', 'दांत', 'teeth', 'जीभ', 'tongue', 'गला', 'throat', 'गर्दन', 'neck', 'कंधा', 'shoulder', 'हाथ', 'hand', 'पैर', 'leg', 'पैर', 'foot', 'घुटना', 'knee', 'कमर', 'waist', 'पीठ', 'back', 'छाती', 'chest', 'पेट', 'belly', 'नाभि', 'navel', 'जननांग', 'genital', 'मासिक धर्म', 'menstruation', 'गर्भावस्था', 'pregnancy', 'प्रसव', 'delivery', 'बच्चा', 'baby', 'शिशु', 'infant', 'बाल चिकित्सा', 'pediatrics', 'वृद्धावस्था', 'old age', 'बुढ़ापा', 'aging', 'जीवन प्रत्याशा', 'life expectancy', 'मृत्यु दर', 'mortality rate', 'जन्म दर', 'birth rate', 'जनसंख्या', 'population', 'जनगणना', 'census'],
            'interesting-news': ['रोचक', 'अनोखा', 'मजेदार', 'रहस्य', 'इतिहास', 'trivia', 'curious', 'weird', 'मिस्ट्री', 'mystery', 'interesting', 'fact', 'अनसुलझा', 'unsolved', 'अविश्वसनीय', 'unbelievable', 'gk', 'सामान्य ज्ञान', 'general knowledge', 'science fact', 'science trivia', 'history fact', 'history trivia', 'top 10', 'top ten', 'listicle', 'amazing', 'funny', 'strange', 'odd', 'peculiar', 'bizarre', 'unusual', 'unique', 'notable', 'noteworthy', 'record', 'world record', 'गिनीज', 'guinness', 'most', 'least', 'first', 'last', 'biggest', 'smallest', 'longest', 'shortest', 'fastest', 'slowest', 'rare', 'uncommon', 'unexplained', 'explained', 'legend', 'myth', 'mythology', 'mythical', 'superstition', 'taboo', 'belief', 'faith', 'धारणा', 'विश्वास', 'मान्यता', 'किवदंती', 'लोककथा', 'folklore', 'story', 'कहानी', 'कथा', 'adventure', 'adventurous', 'exploration', 'discovery', 'invention', 'breakthrough', 'innovation', 'oddity', 'quirky', 'eccentric', 'eccentricity', 'phenomenon', 'phenomena', 'paranormal', 'supernatural', 'ghost', 'spirit', 'haunted', 'haunting', 'alien', 'ufo', 'extraterrestrial', 'space mystery', 'ocean mystery', 'bermuda', 'triangle', 'bermuda triangle', 'samudra', 'समुद्र', 'समुद्र का रहस्य', 'समुद्र में', 'जहाज', 'ship', 'wreck', 'shipwreck', 'डूबा', 'डूबे', 'sink', 'sank', 'sunk', 'lost', 'missing', 'disappear', 'disappeared', 'disappearance', 'lost at sea', 'sea mystery', 'sea legend', 'sea myth', 'sea story', 'sea adventure', 'sea exploration', 'sea discovery', 'sea fact', 'sea trivia', 'sea record', 'sea phenomenon', 'sea phenomena', 'sea oddity', 'sea quirky', 'sea eccentric', 'sea eccentricity', 'sea paranormal', 'sea supernatural', 'sea ghost', 'sea spirit', 'sea haunted', 'sea haunting', 'sea alien', 'sea ufo', 'sea extraterrestrial', 'sea space mystery', 'sea ocean mystery', 'sea bermuda', 'sea triangle', 'sea bermuda triangle'],
            'वायरल': ['वायरल', 'viral', 'अजब', 'गजब', 'सोशल', 'social', 'trending', 'trend'],
            'उत्तर प्रदेश': ['उत्तर प्रदेश', 'uttar pradesh', 'up', 'यूपी', 'up news'],
        }
    
    def get_trending_topics(self, country: str = 'IN') -> List[Dict]:
        """
        Get trending topics that appear in at least 3 different news sources
        """
        trends = self._get_multi_source_trending_topics()
        if trends:
            return trends
        
        logger.warning("No trending topics found from multiple RSS sources")
        return []
    
    def _get_multi_source_trending_topics(self) -> List[Dict]:
        """Get trending topics that appear in at least 3 different sources"""
        try:
            all_entries = []
            source_entries = {}
            
            # Fetch entries from all sources
            for source_name, feed_urls in self.rss_feeds.items():
                source_entries[source_name] = []
                
                for feed_url in feed_urls:
                    try:
                        logger.info(f"Fetching RSS feed from {source_name}: {feed_url}")
                        
                        # Parse RSS feed
                        feed = feedparser.parse(feed_url)
                        
                        if feed.entries:
                            logger.info(f"Found {len(feed.entries)} entries from {source_name}")
                            
                            for entry in feed.entries:
                                if hasattr(entry, 'title') and entry.title:
                                    # Clean and process the title
                                    title = entry.title.strip()
                                    if len(title) > 10:  # Filter out very short titles
                                        entry_data = {
                                            'title': title,
                                            'link': getattr(entry, 'link', ''),
                                            'published': getattr(entry, 'published', ''),
                                            'source': source_name,
                                            'feed_url': feed_url
                                        }
                                        source_entries[source_name].append(entry_data)
                                        all_entries.append(entry_data)
                        else:
                            logger.warning(f"No entries found in RSS feed: {feed_url}")
                            
                    except Exception as e:
                        logger.error(f"Error fetching RSS feed {feed_url}: {str(e)}")
                        continue
            
            if all_entries:
                # Find topics that appear in at least 3 different sources
                multi_source_topics = self._find_multi_source_topics(all_entries, source_entries)
                
                if multi_source_topics:
                    # Convert to trending topics format
                    trends = []
                    for i, topic in enumerate(multi_source_topics[:20]):  # Get top 20 (increased from 10)
                        # Use the category that was already determined in _find_multi_source_topics
                        category = topic.get('category', 'national')
                        
                        trends.append({
                            'name': topic['title'],
                            'query': topic['title'],
                            'tweet_volume': 1000 - (i * 50),
                            'url': topic['link'] if topic['link'] else f"https://www.google.com/search?q={topic['title'].replace(' ', '+')}",
                            'rank': i + 1,
                            'sources': topic['sources'],
                            'category': category,
                            'published': topic['published'],
                            'match_count': topic.get('match_count', len(topic['sources']))
                        })
                    
                    if trends:
                        logger.info(f"Successfully found {len(trends)} multi-source trending topics")
                        print(f"Found {len(trends)} trending topics appearing in multiple sources:")
                        for trend in trends[:5]:  # Show top 5
                            sources_str = ', '.join(trend['sources'])
                            match_count = trend.get('match_count', len(trend['sources']))
                            print(f"  {trend['rank']}. {trend['name']} (Sources: {sources_str}, Category: {trend['category']}, Matches: {match_count})")
                        return trends
            
            logger.warning("No multi-source trending topics found")
            return []
            
        except Exception as e:
            logger.error(f"Error getting multi-source trending topics: {str(e)}")
            return []
    
    def _find_multi_source_topics(self, all_entries: List[Dict], source_entries: Dict) -> List[Dict]:
        """Find topics that appear in different sources based on category-specific thresholds"""
        topic_sources = {}
        
        # Category-specific match count requirements
        category_match_counts = {
            "national": 3,
            "politics": 3,
            "world": 3,
            "business": 2,  # Lowered from 3 to 2 for business topics
            "education": 2,
            "career": 2,
            "technology": 2,
            "sports": 2,
            "entertainment": 2,
            "crime": 2,  # New category - requires 2 sources
            "religion": 2,  # New category - requires 2 sources
            "health": 2,  # New category - requires 2 sources
            "fact_check": 2,  # Fact check - requires 2 sources
            "interesting-news": 2,  # Interesting news - requires 2 sources
        }
        
        # Group topics by normalized title and track their sources
        for entry in all_entries:
            normalized_title = self._normalize_title(entry['title'])
            
            if normalized_title not in topic_sources:
                topic_sources[normalized_title] = {
                    'title': entry['title'],
                    'sources': set(),
                    'links': [],
                    'published': entry['published']
                }
            
            topic_sources[normalized_title]['sources'].add(entry['source'])
            if entry['link']:
                topic_sources[normalized_title]['links'].append(entry['link'])
        
        # Filter topics based on category-specific thresholds
        multi_source_topics = []
        for normalized_title, topic_data in topic_sources.items():
            # Determine category for this topic
            category = self._determine_category(topic_data['title'], list(topic_data['sources']))
            
            # Get required match count for this category
            required_matches = category_match_counts.get(category, 3)  # Default to 3
            
            # Check if topic meets the threshold for its category
            if len(topic_data['sources']) >= required_matches:
                multi_source_topics.append({
                    'title': topic_data['title'],
                    'sources': list(topic_data['sources']),
                    'link': topic_data['links'][0] if topic_data['links'] else '',
                    'published': topic_data['published'],
                    'category': category,
                    'match_count': len(topic_data['sources'])
                })
        
        # Sort by number of sources (descending) and then by published date
        multi_source_topics.sort(key=lambda x: (x['match_count'], x['published']), reverse=True)
        
        # Log category breakdown
        category_counts = {}
        for topic in multi_source_topics:
            cat = topic['category']
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        logger.info(f"Found {len(multi_source_topics)} topics with category-specific thresholds:")
        for cat, count in category_counts.items():
            threshold = category_match_counts.get(cat, 3)
            logger.info(f"  {cat}: {count} topics (≥{threshold} sources)")
        
        return multi_source_topics
    
    def _normalize_title(self, title: str) -> str:
        """Normalize title for comparison by removing common words and special characters"""
        import re
        
        # Convert to lowercase
        normalized = title.lower()
        
        # Remove special characters and extra spaces
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove common Hindi and English words that don't add meaning
        common_words = [
            'news', 'latest', 'breaking', 'update', 'report', 'story',
            'समाचार', 'ताजा', 'ताज़ा', 'खबर', 'अपडेट', 'रिपोर्ट'
        ]
        
        words = normalized.split()
        filtered_words = [word for word in words if word not in common_words and len(word) > 2]
        
        return ' '.join(filtered_words)
    
    def _determine_category(self, title: str, sources: List[str]) -> str:
        """Determine the most appropriate category for a topic"""
        title_lower = title.lower()
        
        # Check each category mapping
        for category, keywords in self.category_mapping.items():
            for keyword in keywords:
                if keyword.lower() in title_lower:
                    return category
        
        # Fallback: If 'interesting-news' keywords are present, use 'interesting-news'
        interesting_keywords = self.category_mapping.get('interesting-news', [])
        for keyword in interesting_keywords:
            if keyword.lower() in title_lower:
                return 'interesting-news'
        
        # Check for new categories (crime, religion, health) before defaulting
        crime_keywords = self.category_mapping.get('crime', [])
        for keyword in crime_keywords:
            if keyword.lower() in title_lower:
                return 'crime'
        
        religion_keywords = self.category_mapping.get('religion', [])
        for keyword in religion_keywords:
            if keyword.lower() in title_lower:
                return 'religion'
        
        health_keywords = self.category_mapping.get('health', [])
        for keyword in health_keywords:
            if keyword.lower() in title_lower:
                return 'health'
        
        # Default category based on source analysis
        if 'world' in title_lower or any('world' in source.lower() for source in sources):
            return 'world'
        elif 'entertainment' in title_lower or any('entertainment' in source.lower() for source in sources):
            return 'entertainment'
        elif 'technology' in title_lower or any('tech' in source.lower() for source in sources):
            return 'technology'
        elif 'education' in title_lower or any('education' in source.lower() for source in sources):
            return 'education'
        elif 'career' in title_lower or any('career' in source.lower() for source in sources):
            return 'career'
        else:
            return 'national'  # Default to national news
    
    def _get_source_name(self, url: str) -> str:
        """Extract source name from URL"""
        if 'bhaskar' in url:
            return 'Dainik Bhaskar'
        elif 'ndtv' in url:
            return 'NDTV'
        elif 'indiatv' in url:
            return 'India TV'
        elif 'news18' in url:
            return 'News18 Hindi'
        elif 'abplive' in url:
            return 'ABP Live'
        elif 'amarujala' in url:
            return 'Amar Ujala'
        elif 'gadgets360' in url:
            return 'Gadgets 360'
        elif 'oneindia' in url:
            return 'OneIndia Hindi'
        elif 'livehindustan' in url:
            return 'Live Hindustan'
        elif 'zeenews' in url:
            return 'Zee News'
        elif 'navjivanindia' in url:
            return 'Navjivan India'
        else:
            return 'RSS Feed'

    def get_viral_topics(self) -> list:
        """Fetch all entries from viral feeds, treat each as a valid viral news topic. Limit to 5."""
        viral_feeds = self.rss_feeds.get('viral', [])
        topics = []
        for feed_url in viral_feeds:
            try:
                logger.info(f"Fetching viral RSS feed: {feed_url}")
                feed = feedparser.parse(feed_url)
                if feed.entries:
                    for entry in feed.entries:
                        if hasattr(entry, 'title') and entry.title:
                            title = entry.title.strip()
                            if len(title) > 10:
                                topics.append({
                                    'name': title,
                                    'query': title,
                                    'tweet_volume': 0,
                                    'url': getattr(entry, 'link', ''),
                                    'rank': 0,
                                    'sources': ['viral'],
                                    'category': 'वायरल',
                                    'published': getattr(entry, 'published', ''),
                                    'match_count': 1
                                })
                else:
                    logger.warning(f"No entries found in viral RSS feed: {feed_url}")
            except Exception as e:
                logger.error(f"Error fetching viral RSS feed {feed_url}: {str(e)}")
                continue
        logger.info(f"Fetched {len(topics)} viral topics.")
        return topics[:5]

    def get_uttarpradesh_topics(self) -> list:
        """Fetch all entries from Uttar Pradesh feeds, treat each as a valid UP news topic. Limit to 5."""
        up_feeds = self.rss_feeds.get('uttarpradesh', [])
        topics = []
        for feed_url in up_feeds:
            try:
                logger.info(f"Fetching Uttar Pradesh RSS feed: {feed_url}")
                feed = feedparser.parse(feed_url)
                if feed.entries:
                    for entry in feed.entries:
                        if hasattr(entry, 'title') and entry.title:
                            title = entry.title.strip()
                            if len(title) > 10:
                                topics.append({
                                    'name': title,
                                    'query': title,
                                    'category': 'उत्तर प्रदेश',
                                    'sources': ['uttarpradesh'],
                                    'author_id': 10,
                                    'author_name': 'Harshit',
                                    'link': getattr(entry, 'link', ''),
                                    'summary': getattr(entry, 'summary', ''),
                                    'published': getattr(entry, 'published', ''),
                                })
            except Exception as e:
                logger.error(f"Error fetching Uttar Pradesh feed {feed_url}: {str(e)}")
        logger.info(f"Fetched {len(topics)} Uttar Pradesh topics.")
        return topics[:5]

class DynamicImageSelector:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
        
        # Keyword mappings for predefined images
        self.keyword_mappings = {
            'politics': [
                'मोदी', 'राहुल', 'बीजेपी', 'कांग्रेस', 'राजनीति', 'चुनाव', 'वोट', 'सरकार', 'मंत्री', 'पार्टी',
                'modi', 'rahul', 'bjp', 'congress', 'politics', 'election', 'vote', 'government', 'minister', 'party'
            ],
            'technology': [
                'स्मार्टफोन', 'लैपटॉप', 'कंप्यूटर', 'इंटरनेट', 'सॉफ्टवेयर', 'ऐप', 'आर्टिफिशियल इंटेलिजेंस', 'एआई',
                'smartphone', 'laptop', 'computer', 'internet', 'software', 'app', 'artificial intelligence', 'ai'
            ],
            'sports': [
                'क्रिकेट', 'फुटबॉल', 'खेल', 'मैच', 'टीम', 'खिलाड़ी', 'स्टेडियम', 'टूर्नामेंट',
                'cricket', 'football', 'sports', 'match', 'team', 'player', 'stadium', 'tournament'
            ],
            'entertainment': [
                'बॉलीवुड', 'फिल्म', 'अभिनेता', 'अभिनेत्री', 'मूवी', 'सिनेमा', 'मनोरंजन',
                'bollywood', 'film', 'actor', 'actress', 'movie', 'cinema', 'entertainment'
            ],
            'business': [
                'व्यापार', 'बिजनेस', 'कंपनी', 'शेयर', 'बाजार', 'अर्थव्यवस्था', 'निवेश',
                'business', 'company', 'share', 'market', 'economy', 'investment'
            ],
            'education': [
                'शिक्षा', 'स्कूल', 'कॉलेज', 'यूनिवर्सिटी', 'परीक्षा', 'छात्र', 'शिक्षक',
                'education', 'school', 'college', 'university', 'exam', 'student', 'teacher'
            ],
            'legal': [
                'कोर्ट', 'कानून', 'वकील', 'जज', 'मुकदमा', 'फैसला', 'अदालत',
                'court', 'law', 'lawyer', 'judge', 'case', 'verdict', 'judiciary'
            ]
        }
    
    def analyze_content_for_keywords(self, content: str, title: str) -> tuple[str, float]:
        """Analyze content and return best matching category and confidence score"""
        combined_text = f"{title} {content}".lower()
        
        best_category = 'general'
        best_score = 0.0
        
        for category, keywords in self.keyword_mappings.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in combined_text:
                    score += 1
            
            # Calculate confidence score (0-1)
            confidence = score / len(keywords) if keywords else 0
            
            if confidence > best_score:
                best_score = confidence
                best_category = category
        
        logger.info(f"Content analysis: Category={best_category}, Confidence={best_score:.2f}")
        return best_category, best_score
    
    def get_predefined_image(self, category: str) -> Optional[str]:
        """Get predefined image for the given category"""
        try:
            # Define available images for each category
            category_images = {
                'politics': ['modi_1.jpg', 'rahul_gandhi_1.jpg', 'parliament_1.jpg'],
                'technology': ['smartphone.jpg', 'ai_technology.jpg'],
                'sports': ['cricket.jpg', 'stadium.jpg'],
                'entertainment': ['bollywood.jpg', 'film_camera.jpg'],
                'business': ['business.jpg', 'office_building.jpg'],
                'education': ['education.jpg', 'school_building.jpg'],
                'legal': ['courtroom_1.jpg', 'legal_documents.jpg'],
                'general': ['news.jpg', 'newspaper.jpg']
            }
            
            available_images = category_images.get(category, category_images['general'])
            
            # Try to find an available image
            for image_name in available_images:
                image_path = f"predefined_images/{category}/{image_name}"
                if os.path.exists(image_path):
                    logger.info(f"Using predefined image: {image_path}")
                    return self._load_image_as_base64(image_path)
            
            # Fallback to general category
            for image_name in category_images['general']:
                image_path = f"predefined_images/general/{image_name}"
                if os.path.exists(image_path):
                    logger.info(f"Using fallback predefined image: {image_path}")
                    return self._load_image_as_base64(image_path)
            
            logger.warning(f"No predefined image found for category: {category}")
            return None
            
        except Exception as e:
            logger.error(f"Error loading predefined image: {str(e)}")
            return None
    
    def _load_image_as_base64(self, image_path: str) -> str:
        """Load image file and convert to base64"""
        try:
            with open(image_path, 'rb') as image_file:
                image_data = image_file.read()
                return base64.b64encode(image_data).decode('utf-8')
        except Exception as e:
            logger.error(f"Error converting image to base64: {str(e)}")
            return ""
    
    def generate_ai_image(self, prompt: str, aspect_ratio: str = "16:9") -> Optional[str]:
        """Generate image using Google's Imagen model with fallback"""
        try:
            # Add instruction to avoid text in image
            enhanced_prompt = f"**Image should not contain any text**, {prompt}"
            
            logger.info(f"Generating AI image with prompt: {prompt}")
            
            # Try imagen-4.0-generate-preview-06-06 first
            try:
                logger.info("Attempting image generation with imagen-4.0-generate-preview-06-06")
                response = self.client.models.generate_images(
                    model='imagen-4.0-generate-preview-06-06',
                    prompt=enhanced_prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio=aspect_ratio,
                    )
                )
                
                # Check if response and generated_images exist
                if response and hasattr(response, 'generated_images') and response.generated_images:
                    generated_image = response.generated_images[0]
                    if generated_image and hasattr(generated_image, 'image') and hasattr(generated_image.image, 'image_bytes'):
                        logger.info("Successfully generated image with imagen-4.0-generate-preview-06-06")
                        return base64.b64encode(generated_image.image.image_bytes).decode('utf-8')
                
                logger.warning("Failed to generate image with imagen-4.0-generate-preview-06-06, trying imagen-3.0-generate-002")
                
            except Exception as e:
                logger.warning(f"Error with imagen-4.0-generate-preview-06-06: {str(e)}, trying imagen-3.0-generate-002")
            
            # Fallback to imagen-3.0-generate-002
            try:
                logger.info("Attempting image generation with imagen-3.0-generate-002")
                response = self.client.models.generate_images(
                    model='imagen-3.0-generate-002',
                    prompt=enhanced_prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio=aspect_ratio,
                    )
                )
                
                # Check if response and generated_images exist
                if response and hasattr(response, 'generated_images') and response.generated_images:
                    generated_image = response.generated_images[0]
                    if generated_image and hasattr(generated_image, 'image') and hasattr(generated_image.image, 'image_bytes'):
                        logger.info("Successfully generated image with imagen-3.0-generate-002")
                        return base64.b64encode(generated_image.image.image_bytes).decode('utf-8')
                
                logger.error("Failed to generate image with both models")
                return None
                
            except Exception as e:
                logger.error(f"Error with imagen-3.0-generate-002: {str(e)}")
                return None
                
        except Exception as e:
            logger.error(f"Error in generate_ai_image: {str(e)}")
            return None
    
    def select_image(self, content: str, title: str, ai_prompt: str = "") -> tuple[Optional[str], str]:
        """Select or generate an image based on content analysis"""
        try:
            # First try to generate AI image if prompt is provided
            if ai_prompt:
                logger.info("Attempting to generate AI image with provided prompt")
                image_data = self.generate_ai_image(ai_prompt)
                if image_data:
                    return image_data, 'ai_generated'
            
            # Analyze content for category
            category, confidence = self.analyze_content_for_keywords(content, title)
            
            # If high confidence, try predefined image
            if confidence > 0.3:
                logger.info(f"High confidence ({confidence:.2f}) for category: {category}")
                image_data = self.get_predefined_image(category)
                if image_data:
                    return image_data, 'predefined'
            
            # If no predefined image or low confidence, try AI generation
            if not ai_prompt:
                # Generate a generic image prompt from title
                ai_prompt = f"News image related to: {title}"
            
            logger.info("Attempting AI image generation")
            image_data = self.generate_ai_image(ai_prompt)
            if image_data:
                return image_data, 'ai_generated'
            
            # Final fallback: try to get any predefined image
            logger.warning("AI generation failed, trying fallback predefined image")
            image_data = self.get_predefined_image('general')
            if image_data:
                return image_data, 'predefined'
            
            logger.error("All image selection methods failed")
            return None, 'none'
            
        except Exception as e:
            logger.error(f"Error in select_image: {str(e)}")
            return None, 'none'

class ImageGenerator:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = genai.Client(api_key=api_key)
    
    def generate_image(self, prompt: str, aspect_ratio: str = "16:9") -> Optional[str]:
        """Generate image using Google's Imagen model with fallback"""
        try:
            # Add instruction to avoid text in image
            enhanced_prompt = f"**Image should not contain any text**, {prompt}"
            
            logger.info(f"Generating image with prompt: {prompt}")
            
            # Try imagen-4.0-generate-preview-06-06 first
            try:
                logger.info("Attempting image generation with imagen-4.0-generate-preview-06-06")
                response = self.client.models.generate_images(
                    model='imagen-4.0-generate-preview-06-06',
                    prompt=enhanced_prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio=aspect_ratio,
                    )
                )
                
                # Check if response and generated_images exist
                if response and hasattr(response, 'generated_images') and response.generated_images:
                    generated_image = response.generated_images[0]
                    if generated_image and hasattr(generated_image, 'image') and hasattr(generated_image.image, 'image_bytes'):
                        image = Image.open(BytesIO(generated_image.image.image_bytes))
                        
                        # Convert image to base64
                        buffered = BytesIO()
                        image.save(buffered, format="PNG")
                        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                        
                        logger.info("Successfully generated image with imagen-4.0-generate-preview-06-06")
                        return img_str
                
                logger.warning("imagen-4.0-generate-preview-06-06 failed, trying imagen-3.0-generate-002")
                
            except Exception as e:
                logger.warning(f"imagen-4.0-generate-preview-06-06 failed: {str(e)}, trying imagen-3.0-generate-002")
            
            # Fallback to imagen-3.0-generate-002
            response = self.client.models.generate_images(
                model='imagen-3.0-generate-002',
                prompt=enhanced_prompt,
                config=types.GenerateImagesConfig(
                    number_of_images=1,
                    aspect_ratio=aspect_ratio,
                )
            )
            
            # Check if response and generated_images exist
            if not response or not hasattr(response, 'generated_images') or not response.generated_images:
                logger.error("No images generated in response from imagen-3.0-generate-002")
                return None
            
            # Process the generated image
            generated_image = response.generated_images[0]
            if not generated_image or not hasattr(generated_image, 'image') or not generated_image.image:
                logger.error("Invalid generated image data from imagen-3.0-generate-002")
                return None
            
            image = Image.open(BytesIO(generated_image.image.image_bytes))
            
            # Convert image to base64
            buffered = BytesIO()
            image.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
            
            logger.info("Successfully generated image with imagen-3.0-generate-002 (fallback)")
            return img_str
            
        except Exception as e:
            logger.error(f"Error generating image: {str(e)}")
            return None

class ContentAutomation:
    def __init__(self, config: Dict):
        self.config = config
        self.trends_api = RSSTrendsAPI()  # Use RSS API instead of Google Trends
        self.gemini_ai = GeminiAI(config['gemini']['api_key'])
        self.wordpress_api = WordPressAPI(
            config['wordpress']['site_url'],
            config['wordpress']['username'],
            config['wordpress']['password']
        )
        
        # Category-User Mapping Configuration
        self.category_user_mapping = {
            'sports': {
                'user_id': 2,
                'user_name': 'Saumitra',
                'categories': ['sports']
            },
            'national': {
                'user_id': 1,
                'user_name': 'Disharth',
                'categories': ['national']
            },
            'world': {
                'user_id': 3,
                'user_name': 'Aditi',
                'categories': ['world']
            },
            'technology': {
                'user_id': 4,
                'user_name': 'Sumit',
                'categories': ['technology', 'career']
            },
            'career': {
                'user_id': 4,
                'user_name': 'Sumit',
                'categories': ['technology', 'career']
            },
            'business': {
                'user_id': 5,
                'user_name': 'Aditya',
                'categories': ['business']
            },
            'education': {
                'user_id': 8,
                'user_name': 'Latika',
                'categories': ['education']
            },
            'crime': {
                'user_id': 6,
                'user_name': 'Piyush',
                'categories': ['crime']
            },
            'interesting-news': {
                'user_id': 7,
                'user_name': 'Ramkrishna',
                'categories': ['interesting-news', 'fact_check']
            },
            'fact_check': {
                'user_id': 7,
                'user_name': 'Ramkrishna',
                'categories': ['interesting-news', 'fact_check']
            },
            'health': {
                'user_id': 9,
                'user_name': 'Shrey',
                'categories': ['health', 'religion', 'entertainment']
            },
            'religion': {
                'user_id': 9,
                'user_name': 'Shrey',
                'categories': ['health', 'religion', 'entertainment']
            },
            'entertainment': {
                'user_id': 9,
                'user_name': 'Shrey',
                'categories': ['health', 'religion', 'entertainment']
            },
            'वायरल': {
                'user_id': 11,
                'user_name': 'Shanvi',
                'categories': ['वायरल']
            },
            'उत्तर प्रदेश': {
                'user_id': 10,
                'user_name': 'Harshit',
                'categories': ['उत्तर प्रदेश']
            }
        }
        
        # Default user for uncategorized content
        self.default_user = {
            'user_id': 1,
            'user_name': 'Disharth',
            'categories': ['national']
        }
        
        self.processed_trends = set()
        self.load_processed_trends()
        self.image_selector = DynamicImageSelector(config['image_generator']['api_key'])
    
    def load_processed_trends(self):
        try:
            if os.path.exists('processed_trends.json'):
                with open('processed_trends.json', 'r') as f:
                    self.processed_trends = set(json.load(f))
        except Exception as e:
            logger.error(f"Error loading processed trends: {str(e)}")
    
    def save_processed_trends(self):
        try:
            with open('processed_trends.json', 'w') as f:
                json.dump(list(self.processed_trends), f)
        except Exception as e:
            logger.error(f"Error saving processed trends: {str(e)}")
    
    def extract_title_from_content(self, content: str) -> str:
        lines = content.split('\n')
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and len(line) < 100:
                return line
        return ""  # No fallback - caller must provide proper title
    
    def clean_content(self, content: str) -> str:
        """Clean up the content"""
        # Remove category labels (English and Hindi, any position)
        content = re.sub(r'^\s*(Category|श्रेणी)\s*:?\s*[^\n]*$', '', content, flags=re.IGNORECASE | re.MULTILINE)
        content = re.sub(r'(Category|श्रेणी)\s*:?\s*[^\n]*', '', content, flags=re.IGNORECASE)
        
        # Remove tag lines/blocks (TAGS:, Tags:, टैग:)
        content = re.sub(r'^\s*(TAGS|Tags|टैग)\s*:?\s*[^\n]*$', '', content, flags=re.IGNORECASE | re.MULTILINE)
        content = re.sub(r'(TAGS|Tags|टैग)\s*:?\s*[^\n]*', '', content, flags=re.IGNORECASE)
        
        # Remove fake names
        content = re.sub(r'[^()]*\(काल्पनिक\)[^()]*', '', content)
        content = re.sub(r'[^()]*\(काल्पनिक नाम\)[^()]*', '', content)
        
        # Remove the title if it appears at the start of content
        if hasattr(self, '_last_cleaned_title') and self._last_cleaned_title:
            content = re.sub(f'^{re.escape(self._last_cleaned_title)}\\s*', '', content)
            content = re.sub(f'^VIDEO:\\s*{re.escape(self._last_cleaned_title)}\\s*', '', content)
        
        # Clean up formatting
        content = content.replace('#', '')
        content = content.replace('**', '')
        content = content.replace('*', '')
        content = content.replace('_', ' ')  # Replace underscores with spaces
        
        # Remove foreign words that shouldn't be in Hindi content
        foreign_words_to_remove = [
            'perkembangan', 'development', 'implementation', 'utilization',
            'optimization', 'standardization', 'modernization', 'digitalization',
            'globalization', 'industrialization', 'urbanization', 'commercialization'
        ]
        
        for word in foreign_words_to_remove:
            content = content.replace(word, '')
            content = content.replace(word.capitalize(), '')
        
        # Split into paragraphs and format
        paragraphs = content.split('\n\n')
        formatted_content = ""
        
        for para in paragraphs:
            para = para.strip()
            if para and len(para) > 10:  # Only include substantial paragraphs
                # Clean up any remaining formatting issues
                para = para.replace('  ', ' ')  # Remove double spaces
                para = para.replace('_', ' ')   # Ensure no underscores remain
                # Remove any remaining foreign words
                for word in foreign_words_to_remove:
                    para = para.replace(word, '')
                    para = para.replace(word.capitalize(), '')
                formatted_content += f"<p>{para}</p>\n\n"
        
        # If no content was formatted, use the original content
        if not formatted_content.strip():
            cleaned_content = content.replace('_', ' ')
            for word in foreign_words_to_remove:
                cleaned_content = cleaned_content.replace(word, '')
                cleaned_content = cleaned_content.replace(word.capitalize(), '')
            formatted_content = f"<p>{cleaned_content}</p>"
        
        # Clean up any double newlines created by our removals
        formatted_content = re.sub(r'\n\s*\n\s*\n', '\n\n', formatted_content)
        
        return formatted_content.strip()
    
    def clean_title(self, title: str) -> str:
        """Clean up the title"""
        # Remove formatting symbols
        title = title.replace('**', '')
        title = title.replace('*', '')
        title = title.replace('#', '')
        title = title.replace('_', ' ')
        
        # Remove foreign words that shouldn't be in Hindi titles
        foreign_words_to_remove = [
            'perkembangan', 'development', 'implementation', 'utilization',
            'optimization', 'standardization', 'modernization', 'digitalization',
            'globalization', 'industrialization', 'urbanization', 'commercialization'
        ]
        
        for word in foreign_words_to_remove:
            title = title.replace(word, '')
            title = title.replace(word.capitalize(), '')
        
        # Remove extra spaces
        title = ' '.join(title.split())
        
        # Store the cleaned title for use in content cleaning
        self._last_cleaned_title = title.strip()
        
        return title.strip()
    
    def get_user_for_category(self, category: str) -> Dict:
        """Get the appropriate user for a given category"""
        # Get user mapping for the category
        user_mapping = self.category_user_mapping.get(category, self.default_user)
        
        logger.info(f"Assigned category '{category}' to user: {user_mapping['user_name']} (ID: {user_mapping['user_id']})")
        return user_mapping
    
    def run_automation(self, max_posts: int = 3):
        """Run automation for all content types (legacy method)"""
        logger.info("Starting content automation process...")
        if not self.wordpress_api.test_connection():
            logger.error("WordPress connection failed. Please check your credentials.")
            return
        # Get trending topics from multiple RSS sources
        trends = self.trends_api.get_trending_topics()
        viral_trends = self.trends_api.get_viral_topics()
        up_trends = self.trends_api.get_uttarpradesh_topics()
        all_trends = viral_trends + up_trends + trends
        if not all_trends:
            logger.error("No trending topics found from multiple sources or viral feeds")
            return
        # Print pure viral-only topics to terminal
        pure_viral = [t for t in viral_trends if t['category'] == 'वायरल' and t['sources'] == ['viral']]
        pure_up = [t for t in up_trends if t['category'] == 'उत्तर प्रदेश' and t['sources'] == ['uttarpradesh']]
        if pure_viral or pure_up:
            print("\n=== Viral-only topics to be posted (category 'वायरल' or 'उत्तर प्रदेश') ===")
            for t in pure_viral[:10]:
                print(f"- {t['name']}")
            if len(pure_viral) > 10:
                print(f"...and {len(pure_viral) - 10} more.")
            for t in pure_up[:10]:
                print(f"- {t['name']}")
            if len(pure_up) > 10:
                print(f"...and {len(pure_up) - 10} more.")
            print("===============================================\n")
        # Reorder all_trends so pure viral-only topics are posted first
        other_trends = [t for t in all_trends if t not in pure_viral and t not in pure_up]
        all_trends = pure_viral + pure_up + other_trends
        logger.info(f"Found {len(all_trends)} trending topics (multi-source + viral + UP)")
        posts_created = 0
        posts_without_images = []
        for trend in all_trends:
            if posts_created >= max_posts:
                break
            if trend['name'] in self.processed_trends:
                logger.info(f"Skipping already processed trend: {trend['name']}")
                continue
            sources_str = ', '.join(trend.get('sources', [])) if trend.get('sources') else 'Unknown'
            category = trend.get('category', 'national')
            logger.info(f"Processing trend: {trend['name']} (Sources: {sources_str}, Category: {category})")
            # Use chained content generation with search grounding for viral news
            if category == 'वायरल':
                content = self.gemini_ai.generate_news_content_chained_with_search_grounding(trend)
            elif category == 'उत्तर प्रदेश':
                content = self.gemini_ai.generate_news_content_chained_with_search_grounding(trend)
                author_id = 10
            else:
                content = self.gemini_ai.generate_news_content(trend)
            if not content:
                logger.warning(f"Failed to generate content for: {trend['name']}")
                continue
            parsed_content = self.gemini_ai.parse_generated_content(content)
            
            # Check if a proper headline was generated, if not use original RSS title
            if not parsed_content['headline'] or parsed_content['headline'].strip() == "":
                logger.warning(f"No proper headline generated for: {trend['name']}, using original RSS title")
                parsed_content['headline'] = trend['name']  # Use original RSS feed title
            
            # Skip if still no proper title
            if not parsed_content['headline'] or parsed_content['headline'].strip() == "":
                logger.error(f"No title available for: {trend['name']}, skipping post")
                continue
                
            cleaned_content = self.clean_content(parsed_content['content'])
            categories = parsed_content['categories'][:1] if parsed_content['categories'] else []
            if category == 'वायरल':
                categories = ['वायरल']
            elif category == 'उत्तर प्रदेश':
                categories = ['उत्तर प्रदेश']
            featured_image_id = None
            ascii_slug = self.wordpress_api._create_ascii_slug(trend['name'])
            image_generated = False
            cleaned_title = self.clean_title(parsed_content['headline'])
            image_data, image_source = self.image_selector.select_image(
                content=cleaned_content,
                title=cleaned_title,
                ai_prompt=parsed_content.get('image_prompt', '')
            )
            if image_data:
                logger.info(f"Selected image source: {image_source}")
                # Generate English alt text for the image
                english_alt_text = self._convert_hindi_to_english_alt_text(cleaned_title)
                featured_image_id = self.wordpress_api.upload_image(
                    image_data=image_data,
                    title=cleaned_title,
                    caption=cleaned_title,
                    ascii_slug=ascii_slug,
                    alt_text=english_alt_text  # Use English alt text
                )
                if featured_image_id:
                    logger.info(f"Successfully uploaded featured image with ID: {featured_image_id} (Source: {image_source})")
                    image_generated = True
                    # Add image source attribution at the end of content
                    attribution = f"\n\n<p style='text-align: left; font-style: italic; color: #666;'>Image Source: {('AI' if image_source == 'ai_generated' else 'Google')}</p>"
                    cleaned_content = cleaned_content + attribution
                else:
                    logger.warning("Failed to upload featured image")
            else:
                logger.warning("No image could be selected or generated")
            cleaned_title = self.clean_title(parsed_content['headline'])
            ascii_slug = self.wordpress_api._create_ascii_slug(trend['name'])
            user_mapping = self.get_user_for_category(category)
            author_id = user_mapping['user_id']
            post_id = self.wordpress_api.create_post(
                title=cleaned_title,
                content=cleaned_content,
                categories=categories,
                tags=parsed_content['tags'],
                featured_media=featured_image_id,
                slug=ascii_slug,
                status="publish",
                author_id=author_id
            )
            if post_id:
                self.processed_trends.add(trend['name'])
                posts_created += 1
                logger.info(f"Successfully created post {post_id} for trend: {trend['name']}")
                if not image_generated and parsed_content['image_prompt']:
                    posts_without_images.append({
                        'post_id': post_id,
                        'trend_name': trend['name'],
                        'image_prompt': parsed_content['image_prompt'],
                        'headline': parsed_content['headline'],
                        'ascii_slug': ascii_slug
                    })
                    logger.info(f"Added post {post_id} to image retry list")
                time.sleep(3)
            else:
                logger.error(f"Failed to create post for trend: {trend['name']}")
        self.save_processed_trends()
        logger.info(f"Automation completed. Created {posts_created} posts.")
        if posts_without_images:
            logger.info(f"Starting image retry for {len(posts_without_images)} posts...")
            self._retry_image_generation(posts_without_images)

    def run_viral_up_automation(self, max_posts: int = 5):
        """Run automation specifically for viral and Uttar Pradesh news (every 3 hours)"""
        logger.info("Starting VIRAL & UP content automation process...")
        if not self.wordpress_api.test_connection():
            logger.error("WordPress connection failed. Please check your credentials.")
            return
        
        # Get only viral and UP topics
        viral_trends = self.trends_api.get_viral_topics()
        up_trends = self.trends_api.get_uttarpradesh_topics()
        all_trends = viral_trends + up_trends
        
        if not all_trends:
            logger.error("No viral or UP topics found")
            return
        
        logger.info(f"Found {len(all_trends)} viral and UP topics")
        
        posts_created = 0
        posts_without_images = []
        
        for trend in all_trends:
            if posts_created >= max_posts:
                break
            if trend['name'] in self.processed_trends:
                logger.info(f"Skipping already processed trend: {trend['name']}")
                continue
            
            sources_str = ', '.join(trend.get('sources', [])) if trend.get('sources') else 'Unknown'
            category = trend.get('category', 'national')
            logger.info(f"Processing VIRAL/UP trend: {trend['name']} (Sources: {sources_str}, Category: {category})")
            
            # Use chained content generation with search grounding for viral/UP news
            content = self.gemini_ai.generate_news_content_chained_with_search_grounding(trend)
            
            if not content:
                logger.warning(f"Failed to generate content for: {trend['name']}")
                continue
            
            parsed_content = self.gemini_ai.parse_generated_content(content)
            
            # Check if a proper headline was generated, if not use original RSS title
            if not parsed_content['headline'] or parsed_content['headline'].strip() == "":
                logger.warning(f"No proper headline generated for: {trend['name']}, using original RSS title")
                parsed_content['headline'] = trend['name']
            
            # Skip if still no proper title
            if not parsed_content['headline'] or parsed_content['headline'].strip() == "":
                logger.error(f"No title available for: {trend['name']}, skipping post")
                continue
                
            cleaned_content = self.clean_content(parsed_content['content'])
            
            # Set categories based on trend type
            if category == 'वायरल':
                categories = ['वायरल']
            elif category == 'उत्तर प्रदेश':
                categories = ['उत्तर प्रदेश']
            else:
                categories = parsed_content['categories'][:1] if parsed_content['categories'] else []
            
            featured_image_id = None
            ascii_slug = self.wordpress_api._create_ascii_slug(trend['name'])
            image_generated = False
            cleaned_title = self.clean_title(parsed_content['headline'])
            
            image_data, image_source = self.image_selector.select_image(
                content=cleaned_content,
                title=cleaned_title,
                ai_prompt=parsed_content.get('image_prompt', '')
            )
            
            if image_data:
                logger.info(f"Selected image source: {image_source}")
                english_alt_text = self._convert_hindi_to_english_alt_text(cleaned_title)
                featured_image_id = self.wordpress_api.upload_image(
                    image_data=image_data,
                    title=cleaned_title,
                    caption=cleaned_title,
                    ascii_slug=ascii_slug,
                    alt_text=english_alt_text
                )
                if featured_image_id:
                    logger.info(f"Successfully uploaded featured image with ID: {featured_image_id} (Source: {image_source})")
                    image_generated = True
                    attribution = f"\n\n<p style='text-align: left; font-style: italic; color: #666;'>Image Source: {('AI' if image_source == 'ai_generated' else 'Google')}</p>"
                    cleaned_content = cleaned_content + attribution
                else:
                    logger.warning("Failed to upload featured image")
            else:
                logger.warning("No image could be selected or generated")
            
            cleaned_title = self.clean_title(parsed_content['headline'])
            ascii_slug = self.wordpress_api._create_ascii_slug(trend['name'])
            user_mapping = self.get_user_for_category(category)
            author_id = user_mapping['user_id']
            
            post_id = self.wordpress_api.create_post(
                title=cleaned_title,
                content=cleaned_content,
                categories=categories,
                tags=parsed_content['tags'],
                featured_media=featured_image_id,
                slug=ascii_slug,
                status="publish",
                author_id=author_id
            )
            
            if post_id:
                self.processed_trends.add(trend['name'])
                posts_created += 1
                logger.info(f"Successfully created VIRAL/UP post {post_id} for trend: {trend['name']}")
                if not image_generated and parsed_content['image_prompt']:
                    posts_without_images.append({
                        'post_id': post_id,
                        'trend_name': trend['name'],
                        'image_prompt': parsed_content['image_prompt'],
                        'headline': parsed_content['headline'],
                        'ascii_slug': ascii_slug
                    })
                    logger.info(f"Added post {post_id} to image retry list")
                time.sleep(3)
            else:
                logger.error(f"Failed to create post for trend: {trend['name']}")
        
        self.save_processed_trends()
        logger.info(f"VIRAL & UP automation completed. Created {posts_created} posts.")
        if posts_without_images:
            logger.info(f"Starting image retry for {len(posts_without_images)} posts...")
            self._retry_image_generation(posts_without_images)

    def run_multi_source_automation(self, max_posts: int = 3):
        """Run automation specifically for multi-source news (every 45 minutes)"""
        logger.info("Starting MULTI-SOURCE content automation process...")
        if not self.wordpress_api.test_connection():
            logger.error("WordPress connection failed. Please check your credentials.")
            return
        
        # Get only multi-source trending topics (exclude viral and UP)
        trends = self.trends_api.get_trending_topics()
        
        if not trends:
            logger.error("No multi-source trending topics found")
            return
        
        logger.info(f"Found {len(trends)} multi-source trending topics")
        
        posts_created = 0
        posts_without_images = []
        
        for trend in trends:
            if posts_created >= max_posts:
                break
            if trend['name'] in self.processed_trends:
                logger.info(f"Skipping already processed trend: {trend['name']}")
                continue
            
            sources_str = ', '.join(trend.get('sources', [])) if trend.get('sources') else 'Unknown'
            category = trend.get('category', 'national')
            logger.info(f"Processing MULTI-SOURCE trend: {trend['name']} (Sources: {sources_str}, Category: {category})")
            
            # Use regular content generation for multi-source news
            content = self.gemini_ai.generate_news_content(trend)
            
            if not content:
                logger.warning(f"Failed to generate content for: {trend['name']}")
                continue
            
            parsed_content = self.gemini_ai.parse_generated_content(content)
            
            # Check if a proper headline was generated, if not use original RSS title
            if not parsed_content['headline'] or parsed_content['headline'].strip() == "":
                logger.warning(f"No proper headline generated for: {trend['name']}, using original RSS title")
                parsed_content['headline'] = trend['name']
            
            # Skip if still no proper title
            if not parsed_content['headline'] or parsed_content['headline'].strip() == "":
                logger.error(f"No title available for: {trend['name']}, skipping post")
                continue
                
            cleaned_content = self.clean_content(parsed_content['content'])
            categories = parsed_content['categories'][:1] if parsed_content['categories'] else []
            
            featured_image_id = None
            ascii_slug = self.wordpress_api._create_ascii_slug(trend['name'])
            image_generated = False
            cleaned_title = self.clean_title(parsed_content['headline'])
            
            image_data, image_source = self.image_selector.select_image(
                content=cleaned_content,
                title=cleaned_title,
                ai_prompt=parsed_content.get('image_prompt', '')
            )
            
            if image_data:
                logger.info(f"Selected image source: {image_source}")
                english_alt_text = self._convert_hindi_to_english_alt_text(cleaned_title)
                featured_image_id = self.wordpress_api.upload_image(
                    image_data=image_data,
                    title=cleaned_title,
                    caption=cleaned_title,
                    ascii_slug=ascii_slug,
                    alt_text=english_alt_text
                )
                if featured_image_id:
                    logger.info(f"Successfully uploaded featured image with ID: {featured_image_id} (Source: {image_source})")
                    image_generated = True
                    attribution = f"\n\n<p style='text-align: left; font-style: italic; color: #666;'>Image Source: {('AI' if image_source == 'ai_generated' else 'Google')}</p>"
                    cleaned_content = cleaned_content + attribution
                else:
                    logger.warning("Failed to upload featured image")
            else:
                logger.warning("No image could be selected or generated")
            
            cleaned_title = self.clean_title(parsed_content['headline'])
            ascii_slug = self.wordpress_api._create_ascii_slug(trend['name'])
            user_mapping = self.get_user_for_category(category)
            author_id = user_mapping['user_id']
            
            post_id = self.wordpress_api.create_post(
                title=cleaned_title,
                content=cleaned_content,
                categories=categories,
                tags=parsed_content['tags'],
                featured_media=featured_image_id,
                slug=ascii_slug,
                status="publish",
                author_id=author_id
            )
            
            if post_id:
                self.processed_trends.add(trend['name'])
                posts_created += 1
                logger.info(f"Successfully created MULTI-SOURCE post {post_id} for trend: {trend['name']}")
                if not image_generated and parsed_content['image_prompt']:
                    posts_without_images.append({
                        'post_id': post_id,
                        'trend_name': trend['name'],
                        'image_prompt': parsed_content['image_prompt'],
                        'headline': parsed_content['headline'],
                        'ascii_slug': ascii_slug
                    })
                    logger.info(f"Added post {post_id} to image retry list")
                time.sleep(3)
            else:
                logger.error(f"Failed to create post for trend: {trend['name']}")
        
        self.save_processed_trends()
        logger.info(f"MULTI-SOURCE automation completed. Created {posts_created} posts.")
        if posts_without_images:
            logger.info(f"Starting image retry for {len(posts_without_images)} posts...")
            self._retry_image_generation(posts_without_images)
    
    def _retry_image_generation(self, posts_without_images: List[Dict]):
        """Retry image generation for posts that don't have images"""
        logger.info(f"Attempting to generate images for {len(posts_without_images)} posts...")
        
        for post_data in posts_without_images:
            try:
                post_id = post_data['post_id']
                trend_name = post_data['trend_name']
                image_prompt = post_data['image_prompt']
                headline = post_data['headline']
                ascii_slug = post_data['ascii_slug']
                
                logger.info(f"Retrying image generation for post {post_id}: {trend_name}")
                
                # Clean the title for retry
                cleaned_headline = self.clean_title(headline)
                
                # Use dynamic image selector for retry
                image_data, image_source = self.image_selector.select_image(
                    content="",  # We don't have content in retry, just use prompt
                    title=cleaned_headline,
                    ai_prompt=image_prompt
                )
                
                if image_data:
                    # Upload image to WordPress
                    # Generate English alt text for the image
                    english_alt_text = self._convert_hindi_to_english_alt_text(cleaned_headline)
                    featured_image_id = self.wordpress_api.upload_image(
                        image_data=image_data,
                        title=cleaned_headline,
                        caption=cleaned_headline,
                        ascii_slug=ascii_slug,
                        alt_text=english_alt_text  # Use English alt text
                    )
                    
                    if featured_image_id:
                        logger.info(f"Successfully uploaded featured image with ID: {featured_image_id} (Source: {image_source})")
                        
                        # Get current post content
                        post_content = self.wordpress_api.get_post_content(post_id)
                        if post_content:
                            # Add image source attribution at the end of content
                            attribution = f"\n\n<p style='text-align: left; font-style: italic; color: #666;'>Image Source: {('AI' if image_source == 'ai_generated' else 'Google')}</p>"
                            new_content = post_content + attribution
                            
                            # Update post with new image and content
                            if self._update_post_featured_image(post_id, featured_image_id, new_content):
                                logger.info(f"Successfully updated post {post_id} with new image and attribution")
                            else:
                                logger.error(f"Failed to update post {post_id} with new image")
                        else:
                            logger.error(f"Failed to get content for post {post_id}")
                    else:
                        logger.error(f"Failed to upload image for post {post_id}")
                else:
                    logger.warning(f"Failed to generate image for post {post_id} after retries")
                
                # Add delay between retries
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"Error during image retry for post {post_data.get('post_id', 'unknown')}: {str(e)}")
                continue
        
        logger.info("Image retry process completed")
    
    def retry_images_for_existing_posts(self, max_posts: int = 10):
        """Retry image generation for existing posts that don't have featured images"""
        logger.info("Starting image retry for existing posts...")
        
        try:
            # Get recent posts without featured images
            posts_without_images = self._get_posts_without_images(max_posts)
            
            if not posts_without_images:
                logger.info("No posts found without featured images")
                return
            
            logger.info(f"Found {len(posts_without_images)} posts without featured images")
            
            # Retry image generation for these posts
            self._retry_image_generation_for_existing_posts(posts_without_images)
            
        except Exception as e:
            logger.error(f"Error in retry_images_for_existing_posts: {str(e)}")
    
    def _get_posts_without_images(self, max_posts: int) -> List[Dict]:
        """Get recent posts that don't have featured images"""
        try:
            url = f"{self.wordpress_api.api_url}/posts"
            params = {
                'per_page': max_posts,
                'orderby': 'date',
                'order': 'desc'
            }
            
            response = requests.get(url, headers=self.wordpress_api.headers, params=params, timeout=30)
            
            if response.status_code == 200:
                posts = response.json()
                posts_without_images = []
                
                for post in posts:
                    if not post.get('featured_media') or post['featured_media'] == 0:
                        # Try to extract image prompt from post content or title
                        image_prompt = self._extract_image_prompt_from_post(post)
                        if image_prompt:
                            posts_without_images.append({
                                'post_id': post['id'],
                                'title': post['title']['rendered'],
                                'image_prompt': image_prompt,
                                'ascii_slug': self.wordpress_api._create_ascii_slug(post['title']['rendered'])
                            })
                
                return posts_without_images
            else:
                logger.error(f"Failed to get posts: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting posts without images: {str(e)}")
            return []
    
    def _extract_image_prompt_from_post(self, post: Dict) -> Optional[str]:
        """Extract image prompt from post content or generate one from title"""
        try:
            # Try to find image prompt in post content
            content = post.get('content', {}).get('rendered', '')
            
            # Look for common patterns that might contain image prompts
            if 'IMAGE_PROMPT:' in content:
                lines = content.split('\n')
                for line in lines:
                    if 'IMAGE_PROMPT:' in line:
                        prompt = line.replace('IMAGE_PROMPT:', '').strip()
                        if prompt:
                            return prompt
            
            # If no prompt found, generate one from the title
            title = post.get('title', {}).get('rendered', '')
            if title:
                # Generate a more specific image prompt from the title
                # Remove HTML tags if present
                clean_title = title.replace('<p>', '').replace('</p>', '').replace('<strong>', '').replace('</strong>', '')
                
                # Create a more descriptive prompt
                if 'बिहार' in clean_title or 'Bihar' in clean_title:
                    return "A dramatic news image showing political protest or demonstration in Bihar, India, with people holding banners and flags, representing political tension and voting rights issues"
                elif 'पंजाब' in clean_title or 'Punjab' in clean_title:
                    return "A somber news image depicting the cultural landscape of Punjab, India, with traditional elements like turbans and agricultural fields, representing the region's heritage and current challenges"
                elif 'ब्राजील' in clean_title or 'Brazil' in clean_title:
                    return "A vibrant collage image showing the contrast between Brazil's colorful carnival culture with samba dancers and the serious issue of corruption, with Brazilian flags and cultural elements"
                else:
                    return f"Professional news photography style image representing: {clean_title[:100]}"
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting image prompt: {str(e)}")
            return None
    
    def _retry_image_generation_for_existing_posts(self, posts_without_images: List[Dict]):
        """Retry image generation for existing posts"""
        logger.info(f"Attempting to generate images for {len(posts_without_images)} existing posts...")
        
        for post_data in posts_without_images:
            try:
                post_id = post_data['post_id']
                title = post_data['title']
                image_prompt = post_data['image_prompt']
                ascii_slug = post_data['ascii_slug']
                
                logger.info(f"Retrying image generation for existing post {post_id}: {title}")
                
                # Use dynamic image selector for retry
                image_data, image_source = self.image_selector.select_image(
                    content="",  # We don't have content in retry, just use prompt
                    title=title,
                    ai_prompt=image_prompt
                )
                
                if image_data:
                    # Upload image to WordPress
                    # Generate English alt text for the image
                    english_alt_text = self._convert_hindi_to_english_alt_text(title)
                    featured_image_id = self.wordpress_api.upload_image(
                        image_data=image_data,
                        title=title,
                        caption=title,
                        ascii_slug=ascii_slug,
                        alt_text=english_alt_text  # Use English alt text
                    )
                    
                    if featured_image_id:
                        # Update the post with the new featured image
                        success = self._update_post_featured_image(post_id, featured_image_id)
                        if success:
                            logger.info(f"Successfully updated existing post {post_id} with featured image {featured_image_id} (Source: {image_source})")
                        else:
                            logger.warning(f"Failed to update existing post {post_id} with featured image")
                    else:
                        logger.warning(f"Failed to upload image for existing post {post_id}")
                else:
                    logger.warning(f"Failed to generate image for existing post {post_id} after retries")
                
                # Add delay between retries
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"Error during image retry for existing post {post_data.get('post_id', 'unknown')}: {str(e)}")
                continue
        
        logger.info("Image retry process for existing posts completed")
    
    def _generate_image_with_retry(self, prompt: str, max_retries: int = 3) -> Optional[str]:
        """Generate image with retry logic"""
        for attempt in range(max_retries):
            try:
                logger.info(f"Image generation attempt {attempt + 1}/{max_retries}")
                image_data = self.image_generator.generate_image(prompt)
                if image_data:
                    logger.info(f"Successfully generated image on attempt {attempt + 1}")
                    return image_data
                else:
                    logger.warning(f"Image generation failed on attempt {attempt + 1}")
            except Exception as e:
                logger.error(f"Error generating image on attempt {attempt + 1}: {str(e)}")
            
            if attempt < max_retries - 1:
                logger.info(f"Waiting 5 seconds before retry...")
                time.sleep(5)
        
        logger.error(f"Failed to generate image after {max_retries} attempts")
        return None
    
    def _update_post_featured_image(self, post_id: int, featured_image_id: int, new_content: str = None) -> bool:
        """Update a WordPress post with a new featured image and optionally new content"""
        try:
            url = f"{self.wordpress_api.api_url}/posts/{post_id}"
            payload = {
                "featured_media": featured_image_id
            }
            if new_content is not None:
                payload["content"] = new_content
            
            response = requests.post(url, json=payload, headers=self.wordpress_api.headers, timeout=30)
            
            if response.status_code in [200, 201]:
                logger.info(f"Successfully updated post {post_id} with featured image {featured_image_id}")
                return True
            else:
                logger.error(f"Failed to update post {post_id}: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error updating post {post_id} with featured image: {str(e)}")
            return False

    def _convert_hindi_to_english_alt_text(self, hindi_title: str) -> str:
        """Convert Hindi title to English for alt text"""
        try:
            # Use Gemini to translate the title to English
            prompt = f"""
            Translate this Hindi news title to English. Provide only the English translation, nothing else:
            
            Hindi title: {hindi_title}
            
            English translation:"""
            
            url = f"{self.gemini_ai.base_url}/{self.gemini_ai.model}:generateContent?key={self.gemini_ai.api_key}"
            
            payload = {
                "contents": [{
                    "parts": [{
                        "text": prompt
                    }]
                }]
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    english_text = result['candidates'][0]['content']['parts'][0]['text'].strip()
                    logger.info(f"Translated alt text: {hindi_title} -> {english_text}")
                    return english_text
                else:
                    logger.warning("No translation generated, using original title")
                    return hindi_title
            else:
                logger.warning(f"Translation failed: {response.status_code}, using original title")
                return hindi_title
                
        except Exception as e:
            logger.error(f"Error translating title: {str(e)}")
            return hindi_title

def load_config() -> Dict:
    config_file = 'config.json'
    
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
    
    default_config = {
        "gemini": {
            "api_key": "AIzaSyAMAltWoHufiTV-_SAO5qnwW7CadXXqJQA"
        },
        "wordpress": {
            "site_url": "https://your-wordpress-site.com",
            "username": "your_username",
            "password": "your_application_password"
        },
        "automation": {
            "max_posts_per_run": 3,
            "country": "US"
        },
        "image_generator": {
            "api_key": "your_image_generator_api_key"
        }
    }
    
    try:
        with open(config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        logger.info(f"Created default config file: {config_file}")
        logger.info("Please update the config file with your actual credentials before running.")
    except Exception as e:
        logger.error(f"Error creating config file: {str(e)}")
    
    return default_config

def main():
    print("=" * 60)
    print("Hindi News RSS to WordPress Content Automation")
    print("=" * 60)
    
    config = load_config()
    
    if config['wordpress']['site_url'] == 'https://your-wordpress-site.com':
        print("\n⚠️  Please update the config.json file with your actual credentials first!")
        print("Required credentials:")
        print("- WordPress site URL, username, and application password")
        return
    
    try:
        automation = ContentAutomation(config)
        
        # Check if user wants to retry images for existing posts
        print("\nChoose an option:")
        print("1. Run normal automation (create new posts)")
        print("2. Retry image generation for existing posts without images")
        print("3. Both (run automation + retry images)")
        
        choice = input("\nEnter your choice (1/2/3): ").strip()
        
        if choice == "1":
            max_posts = config['automation'].get('max_posts_per_run', 3)
            automation.run_automation(max_posts)
            print("\n✅ Normal automation completed successfully!")
            
        elif choice == "2":
            max_posts = int(input("Enter number of recent posts to check (default 10): ") or "10")
            automation.retry_images_for_existing_posts(max_posts)
            print("\n✅ Image retry for existing posts completed successfully!")
            
        elif choice == "3":
            max_posts = config['automation'].get('max_posts_per_run', 3)
            automation.run_automation(max_posts)
            print("\n✅ Normal automation completed successfully!")
            
            # Wait a bit before retrying images
            print("\nWaiting 10 seconds before retrying images for existing posts...")
            time.sleep(10)
            
            max_retry_posts = int(input("Enter number of recent posts to check for image retry (default 10): ") or "10")
            automation.retry_images_for_existing_posts(max_retry_posts)
            print("\n✅ Image retry for existing posts completed successfully!")
            
        else:
            print("Invalid choice. Please run the script again and choose 1, 2, or 3.")
            return
        
        print("Check the automation.log file for detailed logs.")
        
    except KeyboardInterrupt:
        print("\n⏹️  Automation interrupted by user")
    except Exception as e:
        logger.error(f"Automation failed: {str(e)}")
        print(f"\n❌ Automation failed: {str(e)}")

if __name__ == "__main__":
    main() 