import os
import time
import random
import logging
import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

class GeminiClient:
    def __init__(self):
        # Configure Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        
        genai.configure(api_key=api_key)
        # Use the correct model name for Gemini Flash
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        logger.info("Initialized Gemini 1.5 Flash model")
    
    def generate_project_tweet(self, project):
        """Generate tweet content for a project"""
        try:
            logger.info(f"Generating tweet content for {project['name']}")
            logger.info(f"Project details: Category: {project['category']}, Twitter: {project['twitter']}")
            
            # Construct the prompt
            prompt = f"""
            You are a Web3 and blockchain expert. Create an English tweet about this project:
            
            - Project Name: {project['name']}
            - Twitter: {project['twitter']}
            - Website: {project['website']}
            - Category: {project['category']}
            
            Rules:
            1. Authentic, unique content that feels human-written
            2. Analytical and interpretive approach (not just promotional)
            3. No copy-paste, unique sentences
            4. Thought-provoking questions/highlights
            5. Insights connected to Web3 trends
            6. If content exceeds 280 characters, it's fine - it will be posted as a thread
            7. Emoji restriction: Max 2 emojis
            8. Format: 
               "Thoughts about the project... 
               [Interesting question/highlight] 
               {project['website']}"
            """
            
            logger.debug(f"Sending prompt to Gemini: {prompt[:100]}...")
            
            # Generate content with Gemini
            response = self.model.generate_content(prompt)
            tweet_content = response.text.strip()
            
            logger.info(f"Generated tweet content: {tweet_content}")
            return tweet_content
            
        except Exception as e:
            logger.error(f"Error generating tweet content for {project['name']}: {str(e)}")
            logger.info("Using fallback tweet instead")
            # Return a fallback tweet if generation fails
            fallback_tweet = f"Exploring {project['name']}'s innovative approach in {project['category']}. Check out their work at {project['website']}"
            return fallback_tweet
    
    def generate_comment(self, username, tweet_data):
        """Generate a comment for a tweet"""
        prompt = f"""
        I want you to generate an engaging and relevant comment for the following tweet by @{username}:

        Tweet: {tweet_data['text']}

        Please generate a comment that:
        1. Is relevant to the tweet's content
        2. Adds value to the discussion
        3. Is engaging but professional
        4. May include a thoughtful question
        5. Is under 280 characters
        6. Avoids generic responses
        7. Is neither overly positive nor negative
        8. Uses appropriate emojis sparingly (max 1-2)

        Format: Just provide the comment text directly, no additional context or explanations.
        """

        try:
            response = self.model.generate_content(prompt)
            comment = response.text.strip()
            
            # Ensure the comment is not too long
            if len(comment) > 280:
                comment = comment[:277] + "..."

            logger.info(f"Generated comment: {comment}")
            return comment
        except Exception as e:
            logger.error(f"Error generating comment: {str(e)}")
            logger.info("Using fallback comment instead")
            # Return a fallback comment if generation fails
            return f"Interesting perspective @{username}! This connects well with recent developments in the space."