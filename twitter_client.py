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
        """Initialize the browser with enhanced anti-detection settings"""
        logger.info("Setting up browser")
        self.playwright = sync_playwright().start()
        
        browser_args = [
            "--no-sandbox",
            "--disable-setuid-sandbox", 
            "--disable-dev-shm-usage",
            "--window-size=1920,1080",
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--disable-features=site-per-process,TranslateUI",
            "--disable-site-isolation-trials",
            "--metrics-recording-only",
            "--no-first-run",
            "--no-service-autorun",
            "--disable-extensions",
            "--font-render-hinting=none"
        ]
        logger.info(f"Browser arguments: {browser_args}")
        
        # Check if storage state exists and is valid
        storage_path = Path(self.session_file)
        storage_state = None
        
        if storage_path.exists():
            try:
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
        
        # Launch browser with enhanced settings
        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=browser_args
        )
        logger.info("Browser launched successfully in headless mode")
        
        # Create context with enhanced settings
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
            storage_state=storage_state
        )
        logger.info("Browser context created")
        
        # Create page and add anti-detection scripts
        self.page = self.context.new_page()
        logger.info("Browser page created")
        
        # Disable webdriver flag
        self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            
            // Hide automation-related properties
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({state: Notification.permission}) :
                    originalQuery(parameters)
            );
            
            // Fake plugins and languages
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5].map(() => ({
                    0: {type: "application/x-google-chrome-pdf"},
                    description: "Portable Document Format",
                    filename: "internal-pdf-viewer",
                    length: 1,
                    name: "Chrome PDF Plugin"
                }))
            });
            
            Object.defineProperty(navigator, 'languages', {
                get: () => ["en-US", "en"]
            });
        """)
        
        # Set default timeout
        self.page.set_default_timeout(60000)
        logger.info("Default timeout set to 60 seconds")
        
    def login(self):
        """Handle Twitter login process with enhanced anti-detection measures"""
        if self.playwright is None:
            self._setup_browser()
            
        try:
            logger.info("===== STARTING TWITTER LOGIN PROCESS =====")
            logger.info("Navigating to Twitter login page")
            
            # Go directly to login page
            self.page.goto("https://twitter.com/i/flow/login")
            
            # Wait for page to be fully loaded and interactive
            self.page.wait_for_load_state("networkidle")
            self.page.wait_for_load_state("domcontentloaded")
            
            # Additional wait for any dynamic content
            random_delay(3, 5)
            
            # Take screenshot for debugging
            self.page.screenshot(path="1_login_page.png", full_page=True)
            logger.info("Saved login page screenshot")
            
            # STEP 1: USERNAME ENTRY
            logger.info("STEP 1: Entering username")
            
            # Try to find username field with multiple approaches
            username_entered = False
            username_selectors = [
                'input[name="text"]',
                'input[autocomplete="username"]',
                '[data-testid="LoginForm_Username_Input"]',
                'input[type="text"]'
            ]
            
            for selector in username_selectors:
                try:
                    # Try both normal selector and JavaScript evaluation
                    try:
                        username_field = self.page.wait_for_selector(selector, timeout=5000)
                        if username_field:
                            username_field.fill(os.getenv('TWITTER_USERNAME'))
                            username_entered = True
                            logger.info(f"Entered username using selector: {selector}")
                            break
                    except:
                        # Try JavaScript fallback
                        self.page.evaluate(f'''
                            const el = document.querySelector('{selector}');
                            if (el) {{
                                el.value = '{os.getenv('TWITTER_USERNAME')}';
                                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                        ''')
                        username_entered = True
                        logger.info(f"Entered username using JavaScript for selector: {selector}")
                        break
                except Exception as e:
                    logger.info(f"Username selector {selector} failed: {str(e)}")
                    continue
            
            if not username_entered:
                raise Exception("Could not find or fill username field")
            
            random_delay(2, 3)
            
            # Click next button after username using multiple approaches
            logger.info("Clicking next after username")
            try:
                next_button = self.page.get_by_role("button", name="Next")
                next_button.click()
            except:
                try:
                    # Try finding by text content
                    self.page.click("text=Next")
                except:
                    # JavaScript fallback
                    self.page.evaluate('''
                        Array.from(document.querySelectorAll('div[role="button"]')).find(el => el.textContent.includes('Next'))?.click();
                    ''')
            
            random_delay(6, 8)
            
            # Take screenshot after username step
            self.page.screenshot(path="2_after_username.png", full_page=True)
            
            # STEP 2: PASSWORD ENTRY
            logger.info("STEP 2: Entering password")
            
            # Wait for password field with multiple approaches
            password_selectors = [
                'input[name="password"]',
                'input[autocomplete="current-password"]',
                '[data-testid="LoginForm_Password_Input"]',
                'input[type="password"]',
                'input[aria-label="Password"]'
            ]
            
            password_entered = False
            for selector in password_selectors:
                try:
                    # Try both normal selector and JavaScript evaluation
                    try:
                        password_field = self.page.wait_for_selector(selector, timeout=8000)
                        if password_field:
                            password_field.fill(os.getenv('TWITTER_PASSWORD'))
                            password_entered = True
                            logger.info(f"Entered password using selector: {selector}")
                            break
                    except:
                        # Try JavaScript fallback
                        self.page.evaluate(f'''
                            const el = document.querySelector('{selector}');
                            if (el) {{
                                el.value = '{os.getenv('TWITTER_PASSWORD')}';
                                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            }}
                        ''')
                        password_entered = True
                        logger.info(f"Entered password using JavaScript for selector: {selector}")
                        break
                except Exception as e:
                    logger.info(f"Password selector {selector} failed: {str(e)}")
                    continue
            
            if not password_entered:
                # Take debug screenshot
                self.page.screenshot(path="3_password_field_not_found.png", full_page=True)
                raise Exception("Could not find or fill password field")
            
            random_delay(2, 3)
            
            # Click login button using multiple approaches
            logger.info("Clicking login button")
            try:
                login_button = self.page.get_by_role("button", name="Log in")
                login_button.click()
            except:
                try:
                    # Try finding by text content
                    self.page.click("text=Log in")
                except:
                    # JavaScript fallback
                    self.page.evaluate('''
                        Array.from(document.querySelectorAll('div[role="button"]')).find(el => el.textContent.includes('Log in'))?.click();
                    ''')
            
            # Wait for navigation and check for verification
            self.page.wait_for_load_state("networkidle")
            random_delay(4, 6)
            
            # Take screenshot after login attempt
            self.page.screenshot(path="4_after_login.png", full_page=True)
              # Check for various post-login scenarios
            logger.info("Checking post-login state...")
            page_content = self.page.content()
            
            # Take screenshot for debugging
            self.page.screenshot(path="post_login_state.png", full_page=True)
            
            # Check for verification code or any security checks
            security_indicators = [
                "Verify your identity",
                "confirmation code",
                "unusual login",
                "suspicious activity",
                "verify it's you",
                "Enter your phone number",
                "Check your phone"
            ]
            
            if any(indicator in page_content for indicator in security_indicators):
                logger.info("Security verification required")
                if "confirmation code" in page_content or "verify it's you" in page_content:
                    logger.info("Email verification code required, checking email")
                    verification_code = self._get_verification_code()
                    if verification_code:
                        self._handle_verification(verification_code)
                    else:
                        raise Exception("Could not get verification code from email")
                else:
                    # Try JavaScript click on any "Continue" or "Skip" buttons that might appear
                    try:
                        self.page.evaluate('''
                            const buttons = Array.from(document.querySelectorAll('div[role="button"]'));
                            const skipButton = buttons.find(el => 
                                el.textContent.includes('Skip') || 
                                el.textContent.includes('Continue') || 
                                el.textContent.includes('Not now')
                            );
                            if (skipButton) skipButton.click();
                        ''')
                        logger.info("Clicked skip/continue button")
                        random_delay(2, 3)
                    except Exception as e:
                        logger.warning(f"Could not find skip button: {str(e)}")
                        
            # Wait longer for the home feed to load
            random_delay(5, 8)
              # Final check for successful login with multiple indicators
            try:
                success_selectors = [
                    '[data-testid="SideNav_NewTweet_Button"]',
                    '[data-testid="AppTabBar_Home_Link"]',
                    '[aria-label="Home"]',
                    '[aria-label="Tweet"]',
                    '[data-testid="tweetButtonInline"]'
                ]
                
                login_success = False
                for selector in success_selectors:
                    try:
                        self.page.wait_for_selector(selector, timeout=5000)
                        login_success = True
                        logger.info(f"Login verified with selector: {selector}")
                        break
                    except Exception as e:
                        logger.info(f"Selector {selector} not found for login verification")
                        continue
                
                if not login_success:
                    # Try JavaScript detection of home feed elements
                    js_success = self.page.evaluate('''
                        const homeElements = document.querySelectorAll('[aria-label="Home"]');
                        const tweetButtons = document.querySelectorAll('[aria-label="Tweet"]');
                        const timeline = document.querySelector('[data-testid="primaryColumn"]');
                        return homeElements.length > 0 || tweetButtons.length > 0 || timeline !== null;
                    ''')
                    
                    if js_success:
                        login_success = True
                        logger.info("Login verified through JavaScript checks")
                
                if login_success:
                    logger.info("Successfully logged in to Twitter")
                    self.is_logged_in = True
                    
                    # Save the authenticated state
                    self.context.storage_state(path=self.session_file)
                    logger.info("Saved authenticated session state")
                else:
                    raise Exception("Could not verify successful login")
                
            except Exception as e:
                logger.error(f"Login status check failed: {str(e)}")
                self.page.screenshot(path="5_login_error.png", full_page=True)
                
                # Try to get any error messages
                try:
                    error_message = self.page.evaluate('''
                        const errorElements = document.querySelectorAll('[role="alert"], .error-message, [data-testid*="error"]');
                        return Array.from(errorElements).map(el => el.textContent).join(", ");
                    ''')
                    if error_message:
                        logger.error(f"Found error message on page: {error_message}")
                except:
                    pass
                    
                raise Exception("Login verification failed")
            
        except Exception as e:
            logger.error(f"Login failed with error: {str(e)}")
            self.page.screenshot(path="login_error.png", full_page=True)
            raise

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