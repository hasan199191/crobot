import os
import random
import time
import schedule
import logging
from datetime import datetime
from dotenv import load_dotenv
from twitter_client import TwitterClient
from gemini_client import GeminiClient

# Configure logging with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("twitter_bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

# Set encoding for stdout
import sys
sys.stdout.reconfigure(encoding='utf-8')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Load project data
PROJECTS = [
    {"name": "Allora", "twitter": "@AlloraNetwork", "website": "allora.network", "category": "AI + Blockchain"},
            {"name": "Caldera", "twitter": "@Calderaxyz", "website": "caldera.xyz", "category": "Rollup Infrastructure"},
            {"name": "Camp Network", "twitter": "@campnetworkxyz", "website": "campnetwork.xyz", "category": "Social Layer"},
            {"name": "Eclipse", "twitter": "@EclipseFND", "website": "eclipse.builders", "category": "SVM L2"},
            {"name": "Fogo", "twitter": "@FogoChain", "website": "fogo.io", "category": "Gaming Chain"},
            {"name": "Humanity Protocol", "twitter": "@Humanityprot", "website": "humanity.org", "category": "Identity"},
            {"name": "Hyperbolic", "twitter": "@hyperbolic_labs", "website": "hyperbolic.xyz", "category": "AI Infrastructure"},
            {"name": "Infinex", "twitter": "@infinex", "website": "infinex.xyz", "category": "DeFi Frontend"},
            {"name": "Irys", "twitter": "@irys_xyz", "website": "irys.xyz", "category": "Data Storage"},
            {"name": "Katana", "twitter": "@KatanaRIPNet", "website": "katana.network", "category": "Gaming Infrastructure"},
            {"name": "Lombard", "twitter": "@Lombard_Finance", "website": "lombard.finance", "category": "Bitcoin DeFi"},
            {"name": "MegaETH", "twitter": "@megaeth_labs", "website": "megaeth.com", "category": "High-Performance L2"},
            {"name": "Mira Network", "twitter": "@mira_network", "website": "mira.network", "category": "Cross-Chain"},
            {"name": "Mitosis", "twitter": "@MitosisOrg", "website": "mitosis.org", "category": "Ecosystem Expansion"},
            {"name": "Monad", "twitter": "@monad_xyz", "website": "monad.xyz", "category": "Parallel EVM"},
            {"name": "Multibank", "twitter": "@multibank_io", "website": "multibank.io", "category": "Multi-Chain Banking"},
            {"name": "Multipli", "twitter": "@multiplifi", "website": "multipli.fi", "category": "Yield Optimization"},
            {"name": "Newton", "twitter": "@MagicNewton", "website": "newton.xyz", "category": "Cross-Chain Liquidity"},
            {"name": "Novastro", "twitter": "@Novastro_xyz", "website": "novastro.xyz", "category": "Cosmos DeFi"},
            {"name": "Noya.ai", "twitter": "@NetworkNoya", "website": "noya.ai", "category": "AI-Powered DeFi"},
            {"name": "OpenLedger", "twitter": "@OpenledgerHQ", "website": "openledger.xyz", "category": "Institutional DeFi"},
            {"name": "PARADEX", "twitter": "@tradeparadex", "website": "paradex.trade", "category": "Perpetuals DEX"},
            {"name": "Portal to BTC", "twitter": "@PortaltoBitcoin", "website": "portaltobitcoin.com", "category": "Bitcoin Bridge"},
            {"name": "Puffpaw", "twitter": "@puffpaw_xyz", "website": "puffpaw.xyz", "category": "Gaming + NFT"},
            {"name": "SatLayer", "twitter": "@satlayer", "website": "satlayer.xyz", "category": "Bitcoin L2"},
            {"name": "Sidekick", "twitter": "@Sidekick_Labs", "website": "N/A", "category": "Developer Tools"},
            {"name": "Somnia", "twitter": "@Somnia_Network", "website": "somnia.network", "category": "Virtual Society"},
            {"name": "Soul Protocol", "twitter": "@DigitalSoulPro", "website": "digitalsoulprotocol.com", "category": "Digital Identity"},
            {"name": "Succinct", "twitter": "@succinctlabs", "website": "succinct.xyz", "category": "Zero-Knowledge"},
            {"name": "Symphony", "twitter": "@SymphonyFinance", "website": "app.symphony.finance", "category": "Yield Farming"},
            {"name": "Theoriq", "twitter": "@theoriq_ai", "website": "theoriq.ai", "category": "AI Agents"},
            {"name": "Thrive Protocol", "twitter": "@thriveprotocol", "website": "thriveprotocol.com", "category": "Social DeFi"},
            {"name": "Union", "twitter": "@union_build", "website": "union.build", "category": "Cross-Chain Infrastructure"},
            {"name": "YEET", "twitter": "@yeet", "website": "yeet.com", "category": "Meme + Utility"},
    # Add all other projects here
]

TWITTER_ACCOUNTS = [
    "0x_ultra", "0xBreadguy", "beast_ico", "mdudas", "lex_node",
            "jessepollak", "0xWenMoon", "ThinkingUSD", "udiWertheimer",
            "vohvohh", "NTmoney", "0xMert_", "QwQiao", "DefiIgnas",
            "notthreadguy", "Chilearmy123", "Punk9277", "DeeZe", "stevenyuntcap",
            "chefcryptoz", "ViktorBunin", "ayyyeandy", "andy8052", "Phineas_Sol",
            "MoonOverlord", "NarwhalTan", "theunipcs", "RyanWatkins_",
            "aixbt_agent", "ai_9684xtpa", "icebergy_", "Luyaoyuan1",
            "stacy_muur", "TheOneandOmsy", "jeffthedunker", "JoshuaDeuk",
            "0x_scientist", "inversebrah", "dachshundwizard", "gammichan",
            "sandeepnailwal", "segall_max", "blknoiz06", "0xmons", "hosseeb",
            "GwartyGwart", "JasonYanowitz", "Tyler_Did_It", "laurashin",
            "Dogetoshi", "benbybit", "MacroCRG", "Melt_Dem"
]

def run_bot():
    """Main function to run the bot tasks"""
    try:
        logger.info("Starting bot run")
        
        # Initialize clients
        twitter_client = TwitterClient()
        gemini_client = GeminiClient()
        
        # Login to Twitter
        twitter_client.login()
        
        # Post project tweets
        if random.random() < 0.85:  # 85% chance to post project tweets
            selected_projects = random.sample(PROJECTS, min(2, len(PROJECTS)))
            for project in selected_projects:
                try:
                    tweet_content = gemini_client.generate_project_tweet(project)
                    twitter_client.post_tweet(tweet_content)
                    logger.info(f"Posted tweet about {project['name']}")
                    time.sleep(random.uniform(5, 10))
                except Exception as e:
                    logger.error(f"Error posting tweet for {project['name']}: {str(e)}")
          # Comment on tweets
        if random.random() < 0.7:  # 70% chance to comment on tweets
            selected_accounts = random.sample(TWITTER_ACCOUNTS, min(15, len(TWITTER_ACCOUNTS)))
            for username in selected_accounts:
                try:
                    latest_tweet = twitter_client.get_latest_tweet(username)
                    if latest_tweet:
                        comment = gemini_client.generate_comment(username, latest_tweet)
                        twitter_client.post_comment(latest_tweet["url"], comment)
                        logger.info(f"Commented on tweet by @{username}")
                        time.sleep(random.uniform(3, 7))
                except Exception as e:
                    logger.error(f"Error commenting on @{username}'s tweet: {str(e)}")
        
        # Close client
        twitter_client.close()
        logger.info("Bot run completed successfully")
    
    except Exception as e:
        logger.error(f"Bot run failed with error: {str(e)}")
        # Try to close browser if it's open
        try:
            if 'twitter_client' in locals():
                twitter_client.close()
        except:
            pass

def main():
    """Schedule the bot to run every 2 hours"""
    logger.info("Bot started, scheduling runs every 2 hours")
    
    # Run once immediately
    run_bot()
    
    # Schedule to run every 2 hours
    schedule.every(2).hours.do(run_bot)
    
    # Keep the script running
    while True:
        schedule.run_pending()
        time.sleep(60)

if __name__ == "__main__":
    main()  