import os
import time
import random
import logging
import re
from pathlib import Path  # Added Path import
from playwright.sync_api import sync_playwright
from gmail_reader import GmailReader
from dotenv import load_dotenv
from utils import get_random_user_agent, random_delay  # Added missing imports from utils

logger = logging.getLogger(__name__)

class TwitterClient:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.session_file = "twitter_session.json"
        self.is_logged_in = False
        
    def _setup_browser(self):
        """Initialize the browser with appropriate settings"""
        logger.info("Setting up browser")
        self.playwright = sync_playwright().start()
        
        browser_args = ["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        logger.info(f"Browser arguments: {browser_args}")
        
        # Check if storage state exists and is valid
        storage_path = Path(self.session_file)
        storage_state = None
        
        if storage_path.exists():
            try:
                # Check if file contains valid JSON
                import json
                with open(storage_path, 'r') as f:
                    json.load(f)
                storage_state = str(storage_path)
                logger.info(f"Using existing session file: {storage_path}")
            except json.JSONDecodeError:
                logger.warning("Invalid session file, will create new session")
                storage_state = None
        else:
            logger.info("No session file found, will create new session")
          # Launch browser with custom user agent
        self.browser = self.playwright.chromium.launch(
            headless=True,  # Headless mode for production
            args=browser_args
        )
        logger.info("Browser launched successfully in visible mode")
        
        # Create context with storage state if available
        self.context = self.browser.new_context(
            user_agent=get_random_user_agent(),
            storage_state=storage_state
        )
        logger.info("Browser context created")
        
        # Create page
        self.page = self.context.new_page()
        logger.info("Browser page created")
        
        # Set default timeout
        self.page.set_default_timeout(60000)
        logger.info("Default timeout set to 60 seconds")
        
    def login(self):
        """Login to Twitter with automatic verification code handling"""
        if self.playwright is None:
            self._setup_browser()
            
        try:
            logger.info("===== STARTING TWITTER LOGIN PROCESS =====")
            
            # Go to Twitter login directly
            logger.info("Navigating to Twitter login page")
            self.page.goto("https://twitter.com/i/flow/login", wait_until="networkidle")
            random_delay(3, 5)
            
            # Take screenshot
            self.page.screenshot(path="1_login_page.png")
            logger.info("Saved login page screenshot")
            
            # STEP 1: USERNAME ENTRY
            logger.info("STEP 1: Entering username")
            # Make sure the username field is visible
            try:
                self.page.wait_for_selector('input[name="text"]', state="visible", timeout=10000)
                self.page.fill('input[name="text"]', os.getenv("TWITTER_USERNAME"))
                logger.info(f"Entered username: {os.getenv('TWITTER_USERNAME')}")
                random_delay(2, 3)
                
                # Click next button
                logger.info("Clicking next after username")
                next_result = self.page.evaluate('''() => {
                    const nextButtons = Array.from(document.querySelectorAll('[role="button"]'));
                    const nextButton = nextButtons.find(btn => 
                        btn.textContent.includes("Next") || 
                        btn.textContent.includes("İleri"));
                    if (nextButton) {
                        nextButton.click();
                        return "clicked";
                    }
                    return "not found";
                }''')
                logger.info(f"Next button click result: {next_result}")
                
                # Wait longer after clicking Next
                random_delay(5, 8)
                
            except Exception as e:
                logger.error(f"Error entering username: {str(e)}")
                return False
            
            # STEP 2: PASSWORD ENTRY
            logger.info("STEP 2: Entering password")
            try:
                # Check if we're on password page
                password_visible = self.page.wait_for_selector('input[name="password"]', state="visible", timeout=10000)
                
                if password_visible:
                    self.page.fill('input[name="password"]', os.getenv("TWITTER_PASSWORD"))
                    logger.info("Password entered")
                    random_delay(2, 3)
                    
                    # Click Log in button
                    logger.info("Clicking login button")
                    login_result = self.page.evaluate('''() => {
                        const loginButtons = Array.from(document.querySelectorAll('[role="button"]'));
                        const loginButton = loginButtons.find(btn => 
                            btn.textContent.includes("Log in") || 
                            btn.textContent.includes("Login") ||
                            btn.textContent.includes("Giriş"));
                        if (loginButton) {
                            loginButton.click();
                            return "clicked";
                        }
                        return "not found";
                    }''')
                    logger.info(f"Login button click result: {login_result}")
                    
                    # Wait longer after clicking login
                    random_delay(8, 12)
                else:
                    logger.error("Password field not found!")
                    return False
                    
            except Exception as e:
                logger.error(f"Error entering password: {str(e)}")
                return False
            
            # STEP 3: CHECK IF VERIFICATION IS NEEDED
            logger.info("STEP 3: Checking if verification is needed")
            self.page.screenshot(path="3_after_login.png")
            
            # Check the current URL and page content
            current_url = self.page.url
            page_content = self.page.content().lower()
            logger.info(f"Current URL after login: {current_url}")
            
            # Indicators that verification is needed
            verification_needed = False
            
            # Check if we're still in the login flow and need verification
            if ("login" in current_url.lower() or "i/flow" in current_url.lower()) and not "home" in current_url.lower():
                if ("verification" in page_content or 
                    "confirm" in page_content or 
                    "code" in page_content or 
                    "verify" in page_content):
                    verification_needed = True
                    logger.info("Verification appears to be needed")
            
            if verification_needed:
                logger.info("STEP 4: Getting verification code from Gmail")
                
                # Get verification code from Gmail
                gmail_reader = GmailReader()
                verification_code = gmail_reader.get_twitter_verification_code()
                
                if verification_code:
                    logger.info(f"Retrieved verification code: {verification_code}")
                    
                    # Look for verification code input field
                    code_selectors = [
                        'input[name="text"]', 
                        'input[data-testid="ocfEnterTextTextInput"]',
                        'input[placeholder*="code"]',
                        'input[type="text"]'
                    ]
                    
                    input_found = False
                    for selector in code_selectors:
                        try:
                            if self.page.query_selector(selector):
                                logger.info(f"Found verification code input with selector: {selector}")
                                self.page.fill(selector, verification_code)
                                random_delay(2, 3)
                                self.page.screenshot(path="4_verification_code_entered.png")
                                input_found = True
                                break
                        except:
                            continue
                    
                    if not input_found:
                        logger.error("Could not find verification code input field!")
                        return False
                    
                    # Click next/verify button
                    logger.info("Clicking next/verify button")
                    verify_result = self.page.evaluate('''() => {
                        const buttons = Array.from(document.querySelectorAll('[role="button"]'));
                        const verifyButton = buttons.find(btn => 
                            btn.textContent.includes("Next") || 
                            btn.textContent.includes("Verify") || 
                            btn.textContent.includes("İleri") ||
                            btn.textContent.includes("Doğrula"));
                        if (verifyButton) {
                            verifyButton.click();
                            return "clicked";
                        }
                        return "not found";
                    }''')
                    logger.info(f"Verify button click result: {verify_result}")
                    
                    # Wait longer after verification
                    random_delay(5, 8)
                else:
                    logger.error("Failed to get verification code from Gmail!")
                    return False
            
            # STEP 5: CHECK LOGIN SUCCESS
            logger.info("Checking if login was successful")
            
            # Wait a moment for possible redirects
            random_delay(5, 8)
            
            # Take final screenshot
            self.page.screenshot(path="5_final_state.png")
            
            # Check current URL
            current_url = self.page.url
            logger.info(f"Final URL: {current_url}")
            
            # Check for success indicators
            if "home" in current_url.lower():
                logger.info("SUCCESS: Logged in successfully based on URL")
                self.is_logged_in = True
                
                # Save the session
                self.context.storage_state(path=self.session_file)
                logger.info(f"Session saved to {self.session_file}")
                
                return True
            else:
                # Check for UI elements that indicate successful login
                success_indicators = [
                    '[data-testid="AppTabBar_Home_Link"]',
                    'div[aria-label="Home timeline"]',
                    'div[data-testid="primaryColumn"]'
                ]
                
                for indicator in success_indicators:
                    if self.page.query_selector(indicator):
                        logger.info(f"SUCCESS: Found login success indicator: {indicator}")
                        self.is_logged_in = True
                        
                        # Save the session
                        self.context.storage_state(path=self.session_file)
                        logger.info(f"Session saved to {self.session_file}")
                        
                        return True
                
                logger.error("Login failed - could not verify success")
                return False
                
        except Exception as e:
            logger.error(f"Login process failed with exception: {str(e)}")
            self.page.screenshot(path="login_error.png")
            return False
    
    def _split_into_tweets(self, content):
        """Split content into tweets while preserving sentence integrity"""
        # Give some buffer space for safety (URLs, emojis, etc.)
        TWEET_LIMIT = 260  # Reduced from 280 to give safety margin
        
        def clean_and_trim(text):
            return text.strip()
        
        def find_sentence_boundary(text, max_length):
            """Find the best place to split text without breaking sentences"""
            if len(text) <= max_length:
                return len(text)
                
            # Try to find the last sentence ending before max_length
            sentence_endings = ['. ', '! ', '? ', '.\n', '!\n', '?\n']
            best_split = 0
            
            # Start looking from earlier in the text to ensure we stay well within limits
            safe_max = min(max_length - 20, len(text))  # Give 20 chars safety margin
            
            for i in range(safe_max, -1, -1):
                if i == 0:
                    break
                    
                # Check if we're at a sentence ending
                for ending in sentence_endings:
                    if text[i-1:i+1] == ending:
                        return i
                        
                # If we haven't found a sentence ending, look for the last complete word
                if best_split == 0 and text[i] == ' ':
                    best_split = i
            
            # If we couldn't find a good split point, use the last word boundary
            return best_split if best_split > 0 else min(max_length - 20, len(text))

        tweets = []
        remaining = content
        
        while remaining:
            # Clean up the remaining text
            remaining = clean_and_trim(remaining)
            if not remaining:
                break
                
            # If remaining text fits in one tweet
            if len(remaining) <= TWEET_LIMIT:
                tweets.append(remaining)
                break
                
            # Find the best place to split
            split_index = find_sentence_boundary(remaining, TWEET_LIMIT)
            
            if split_index == 0:
                logger.warning("Could not find a good split point")
                # Emergency split at TWEET_LIMIT - 20 if no good point found
                split_index = min(TWEET_LIMIT - 20, len(remaining))
                
            # Add the split portion to tweets
            tweets.append(clean_and_trim(remaining[:split_index]))
            remaining = clean_and_trim(remaining[split_index:])
            
        # Verify all tweets are within limit
        for i, tweet in enumerate(tweets):
            if len(tweet) > TWEET_LIMIT:
                logger.warning(f"Tweet {i+1} exceeds limit ({len(tweet)} chars), forcing split")
                # Force split at TWEET_LIMIT - 20 if somehow still too long
                first_part = clean_and_trim(tweet[:TWEET_LIMIT-20])
                second_part = clean_and_trim(tweet[TWEET_LIMIT-20:])
                tweets[i] = first_part
                tweets.insert(i + 1, second_part)
        
        logger.info(f"Split content into {len(tweets)} tweets")
        for i, tweet in enumerate(tweets, 1):
            logger.info(f"Thread part {i}: {tweet[:30]}... ({len(tweet)} chars)")
            
        return tweets

    def post_tweet(self, content):
        """Post a tweet or thread depending on content length"""
        if not self.is_logged_in:
            if not self.login():
                logger.error("Login failed, cannot post tweet")
                return False
                
        # Split content into tweets if necessary
        if len(content) > 280:
            logger.info(f"Content exceeds Twitter character limit ({len(content)} chars), creating thread")
            tweet_parts = self._split_into_tweets(content)
            logger.info(f"Split content into {len(tweet_parts)} tweets")
            return self.post_tweet_thread(tweet_parts)
        else:
            return self._post_single_tweet(content)

    def _post_single_tweet(self, content):
        """Post a single tweet"""
        try:
            logger.info("Posting single tweet")
            # Navigate to home if not already there
            if not self.page.url.startswith("https://twitter.com/home") and not self.page.url.startswith("https://x.com/home"):
                logger.info(f"Navigating to home from {self.page.url}")
                self.page.goto("https://twitter.com/home", wait_until="domcontentloaded")
                random_delay(2, 4)
            
            # Take screenshot of home page
            self.page.screenshot(path="home_before_compose.png")
            logger.info("Saved screenshot of home page")
            
            # Try multiple approaches to click compose tweet button
            compose_clicked = False
            
            # Approach 1: Try various selectors for the compose button
            compose_selectors = [
                'a[href="/compose/tweet"]',
                'a[data-testid="SideNav_NewTweet_Button"]',
                'a[aria-label="Post"]',
                'a[aria-label="Tweet"]',
                'div[aria-label="Tweet"]',
                'div[aria-label="Post"]'
            ]
            
            for selector in compose_selectors:
                logger.info(f"Trying compose button selector: {selector}")
                try:
                    if self.page.query_selector(selector):
                        self.page.click(selector)
                        logger.info(f"Clicked compose button using selector: {selector}")
                        compose_clicked = True
                        break
                except Exception as e:
                    logger.info(f"Selector {selector} failed: {str(e)}")
            
            # Approach 2: If selectors fail, try using JavaScript
            if not compose_clicked:
                logger.info("Trying JavaScript to find and click compose button")
                js_result = self.page.evaluate('''() => {
                    // Try to find compose button by common characteristics
                    const composeSelectors = [
                        'a[href="/compose/tweet"]',
                        '[data-testid="SideNav_NewTweet_Button"]',
                        '[aria-label="Post"]',
                        '[aria-label="Tweet"]',
                        '[data-testid="FloatingActionButton_Tweet"]',
                        '[data-icon="feather"]'
                    ];
                    
                    for (const selector of composeSelectors) {
                        const element = document.querySelector(selector);
                        if (element) {
                            element.click();
                            return `Clicked ${selector}`;
                        }
                    }
                    
                    // Look for any likely compose buttons
                    const allLinks = Array.from(document.querySelectorAll('a, div, button'));
                    const likelyComposeButton = allLinks.find(el => {
                        const ariaLabel = el.getAttribute('aria-label');
                        const text = el.textContent;
                        return (ariaLabel && 
                               (ariaLabel.includes('Tweet') || 
                                ariaLabel.includes('Post'))) ||
                               (text && 
                               (text.includes('Tweet') || 
                                text.includes('Post')));
                    });
                    
                    if (likelyComposeButton) {
                        likelyComposeButton.click();
                        return 'Clicked likely compose button';
                    }
                    
                    return 'No compose button found';
                }''')
                logger.info(f"JavaScript compose button result: {js_result}")
                
                if "Clicked" in js_result:
                    compose_clicked = True
        
            if not compose_clicked:
                logger.error("Could not find compose button")
                self.page.screenshot(path="compose_button_not_found.png")
                return False
                
            # Wait for compose dialog and take screenshot
            random_delay(2, 4)
            self.page.screenshot(path="compose_dialog.png")
            
            # Fill in tweet content
            logger.info("Entering tweet content")
            content_selectors = [
                'div[role="textbox"][data-testid="tweetTextarea_0"]',
                'div[contenteditable="true"][data-testid="tweetTextarea_0"]',
                'div[role="textbox"]',
                'div[contenteditable="true"]'
            ]
            
            content_entered = False
            for selector in content_selectors:
                try:
                    if self.page.query_selector(selector):
                        self.page.fill(selector, content)
                        logger.info(f"Entered content using selector: {selector}")
                        content_entered = True
                        break
                except Exception as e:
                    logger.info(f"Content selector {selector} failed: {str(e)}")
            
            if not content_entered:
                logger.error("Could not enter tweet content")
                self.page.screenshot(path="tweet_content_not_entered.png")
                return False
                
            random_delay(2, 4)
            
            # Click tweet/post button
            logger.info("Clicking post button")
            post_selectors = [
                'div[data-testid="tweetButtonInline"]',
                'div[data-testid="tweetButton"]',
                'div[role="button"]:has-text("Tweet")',
                'div[role="button"]:has-text("Post")'
            ]
            
            post_clicked = False
            for selector in post_selectors:
                try:
                    if self.page.query_selector(selector):
                        self.page.click(selector)
                        logger.info(f"Clicked post button using selector: {selector}")
                        post_clicked = True
                        break
                except Exception as e:
                    logger.info(f"Post button selector {selector} failed: {str(e)}")
            
            # Try JavaScript if regular selectors fail
            if not post_clicked:
                logger.info("Trying JavaScript to click post button")
                js_post_result = self.page.evaluate('''() => {
                    const postButtonSelectors = [
                        '[data-testid="tweetButtonInline"]',
                        '[data-testid="tweetButton"]'
                    ];
                    
                    for (const selector of postButtonSelectors) {
                        const button = document.querySelector(selector);
                        if (button) {
                            button.click();
                            return `Clicked ${selector}`;
                        }
                    }
                    
                    // Look for buttons with "Tweet" or "Post" text
                    const allButtons = Array.from(document.querySelectorAll('div[role="button"]'));
                    const postButton = allButtons.find(btn => 
                        btn.textContent.includes('Tweet') || 
                        btn.textContent.includes('Post'));
                    
                    if (postButton) {
                        postButton.click();
                        return 'Clicked button with Tweet/Post text';
                    }
                    
                    return 'No post button found';
                }''')
                logger.info(f"JavaScript post button result: {js_post_result}")
                
                if "Clicked" in js_post_result:
                    post_clicked = True
            
            if not post_clicked:
                logger.error("Could not click post button")
                self.page.screenshot(path="post_button_not_found.png")
                return False
                
            # Wait for tweet to be posted
            logger.info("Waiting for tweet to be posted")
            random_delay(4, 8)
            
            # Take screenshot of result
            self.page.screenshot(path="after_posting_tweet.png")
            
            logger.info("Tweet posted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to post tweet: {str(e)}")
            # Take screenshot of error state
            self.page.screenshot(path="tweet_error.png")
            return False

    def post_tweet_thread(self, content_list):
        """Post a thread of tweets"""
        if not self.is_logged_in:
            if not self.login():
                logger.error("Login failed, cannot post tweet thread")
                return False
                
        try:
            logger.info(f"Posting a thread with {len(content_list)} tweets")
            
            # Navigate to compose tweet page directly
            compose_url = "https://twitter.com/compose/tweet"
            logger.info(f"Navigating to {compose_url}")
            self.page.goto(compose_url, wait_until="domcontentloaded")
            random_delay(3, 5)
            
            # Enter the first tweet
            logger.info(f"Entering content for tweet 1/{len(content_list)}")
            first_tweet_content = content_list[0]
            
            # Wait for the textarea to be ready
            self.page.wait_for_selector('[data-testid="tweetTextarea_0"]', state="visible", timeout=10000)
            random_delay(1, 2)
            
            # Enter first tweet content
            try:
                self.page.fill('[data-testid="tweetTextarea_0"]', first_tweet_content)
                logger.info("Entered content for first tweet")
                random_delay(2, 3)
            except Exception as e:
                logger.error(f"Error entering first tweet content: {str(e)}")
                return False
            
            # Add remaining tweets to thread
            for i, tweet_content in enumerate(content_list[1:], 2):
                logger.info(f"Adding tweet {i}/{len(content_list)} to thread")
                
                try:
                    # First try to find the + Add button
                    add_button_found = False
                    add_button_selectors = [
                        '[data-testid="addButton"]',
                        'div[aria-label="Add"]',
                        'div[aria-label="Add post"]',
                        'div[role="button"]:has-text("Add")',
                    ]
                    
                    for selector in add_button_selectors:
                        try:
                            add_button = self.page.wait_for_selector(selector, state="visible", timeout=5000)
                            if add_button:
                                logger.info(f"Found Add button with selector: {selector}")
                                # Try multiple ways to click the button
                                try:
                                    add_button.click(delay=100)  # Try with delay
                                    add_button_found = True
                                    break
                                except:
                                    try:
                                        add_button.click(force=True)  # Try force click
                                        add_button_found = True
                                        break
                                    except:
                                        continue
                        except:
                            continue
                    
                    if not add_button_found:
                        # Try JavaScript click as last resort
                        js_result = self.page.evaluate('''() => {
                            const selectors = [
                                '[data-testid="addButton"]',
                                '[aria-label="Add"]',
                                '[aria-label="Add post"]'
                            ];
                            for (const selector of selectors) {
                                const button = document.querySelector(selector);
                                if (button) {
                                    button.click();
                                    return true;
                                }
                            }
                            return false;
                        }''')
                        add_button_found = js_result
                    
                    if not add_button_found:
                        raise Exception("Could not find or click Add button")
                    
                    random_delay(2, 3)
                    
                    # Wait for and fill the new tweet textarea
                    next_textarea_selector = f'[data-testid="tweetTextarea_{i-1}"]'
                    self.page.wait_for_selector(next_textarea_selector, state="visible", timeout=5000)
                    self.page.fill(next_textarea_selector, tweet_content)
                    logger.info(f"Entered content for tweet {i}")
                    random_delay(2, 3)
                    
                except Exception as e:
                    logger.error(f"Error adding tweet {i} to thread: {str(e)}")
                    self.page.screenshot(path=f"thread_tweet_{i}_error.png")
                    return False
            
            # Post the complete thread
            logger.info("Posting the complete thread")
            try:
                post_button = self.page.wait_for_selector('[data-testid="tweetButton"]', state="visible", timeout=5000)
                if post_button:
                    post_button.click()
                    logger.info("Clicked post button")
                    random_delay(5, 8)
                    return True
            except Exception as e:
                logger.error(f"Error posting thread: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"Thread posting failed: {str(e)}")
            return False
            
        return True

    def get_latest_tweet(self, username):
        """Get the latest tweet from a user"""
        if not self.is_logged_in:
            if not self.login():
                logger.error("Login failed, cannot get latest tweet")
                return None
        
        try:
            # Navigate to user's profile
            profile_url = f"https://twitter.com/{username}"
            logger.info(f"Getting latest tweet from {profile_url}")
            self.page.goto(profile_url, wait_until="domcontentloaded")
            random_delay(3, 5)
            
            # Wait for tweets to load
            selectors = [
                'article[data-testid="tweet"]',
                '[data-testid="tweet"]',
                'article[role="article"]'
            ]
            
            tweet_found = False
            tweet_element = None
            
            for selector in selectors:
                try:
                    tweet_element = self.page.wait_for_selector(selector, timeout=10000)
                    if tweet_element:
                        tweet_found = True
                        logger.info(f"Found tweet with selector: {selector}")
                        break
                except Exception as e:
                    logger.info(f"Selector {selector} failed: {str(e)}")
            
            if not tweet_found or not tweet_element:
                logger.error(f"Could not find latest tweet for @{username}")
                return None
            
            # Get tweet URL
            tweet_link = tweet_element.query_selector('a[href*="/status/"]')
            if not tweet_link:
                logger.error("Could not find tweet URL")
                return None
            
            tweet_url = tweet_link.get_attribute('href')
            if not tweet_url.startswith('http'):
                tweet_url = f"https://twitter.com{tweet_url}"
            
            # Get tweet text
            tweet_text = tweet_element.inner_text()
            
            return {
                "url": tweet_url,
                "text": tweet_text,
                "username": username
            }
            
        except Exception as e:
            logger.error(f"Error getting latest tweet from @{username}: {str(e)}")
            return None

    def post_comment(self, tweet_url, comment):
        """Post a comment on a tweet"""
        if not self.is_logged_in:
            if not self.login():
                logger.error("Login failed, cannot post comment")
                return False
        
        try:
            # Navigate to tweet
            logger.info(f"Navigating to tweet: {tweet_url}")
            self.page.goto(tweet_url, wait_until="domcontentloaded")
            random_delay(3, 5)
            
            # Find and click reply button
            reply_selectors = [
                '[data-testid="reply"]',
                'div[aria-label="Reply"]',
                'div[role="button"]:has-text("Reply")'
            ]
            
            reply_clicked = False
            for selector in reply_selectors:
                try:
                    if self.page.query_selector(selector):
                        self.page.click(selector)
                        logger.info(f"Clicked reply button using selector: {selector}")
                        reply_clicked = True
                        break
                except Exception as e:
                    logger.info(f"Reply selector {selector} failed: {str(e)}")
            
            if not reply_clicked:
                logger.error("Could not click reply button")
                return False
            
            random_delay(2, 3)
            
            # Enter comment text
            textarea_selectors = [
                '[data-testid="tweetTextarea_0"]',
                'div[role="textbox"]',
                'div[contenteditable="true"]'
            ]
            
            comment_entered = False
            for selector in textarea_selectors:
                try:
                    if self.page.query_selector(selector):
                        self.page.fill(selector, comment)
                        logger.info(f"Entered comment using selector: {selector}")
                        comment_entered = True
                        break
                except Exception as e:
                    logger.info(f"Comment selector {selector} failed: {str(e)}")
            
            if not comment_entered:
                logger.error("Could not enter comment text")
                return False
            
            random_delay(2, 3)
            
            # Click reply/post button
            post_selectors = [
                '[data-testid="tweetButton"]',
                'div[data-testid="tweetButtonInline"]',
                'div[role="button"]:has-text("Reply")',
                'div[role="button"]:has-text("Post")'
            ]
            
            posted = False
            for selector in post_selectors:
                try:
                    if self.page.query_selector(selector):
                        self.page.click(selector)
                        logger.info(f"Clicked post button using selector: {selector}")
                        posted = True
                        break
                except Exception as e:
                    logger.info(f"Post selector {selector} failed: {str(e)}")
            
            if not posted:
                logger.error("Could not click post button")
                return False
            
            random_delay(3, 5)
            return True
            
        except Exception as e:
            logger.error(f"Error posting comment: {str(e)}")
            return False

    def close(self):
        """Close browser and playwright"""
        try:
            if self.context:
                # Save the session state before closing
                self.context.storage_state(path=self.session_file)
            
            if self.browser:
                self.browser.close()
                
            if self.playwright:
                self.playwright.stop()
                
            logger.info("Browser and Playwright closed")
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")