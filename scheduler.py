#!/usr/bin/env python3
"""
Scheduler script for automatic Hindi news RSS to WordPress automation
This script is designed to be run by cron jobs with different intervals:
- Viral and UP news: Every 3 hours
- Multi-source news: Every 45 minutes
"""

import os
import sys
import logging
from datetime import datetime
from wordpress import ContentAutomation, load_config

# Set up logging for scheduler
def setup_scheduler_logging():
    """Set up logging specifically for the scheduler"""
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # Create timestamp for log file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"scheduler_{timestamp}.log")
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.FileHandler('scheduler.log', encoding='utf-8', mode='a'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def run_viral_up_automation():
    """Run automation for viral and Uttar Pradesh news (every 3 hours)"""
    logger = setup_scheduler_logging()
    
    try:
        logger.info("=" * 60)
        logger.info("Starting VIRAL & UP automation run (3-hour interval)")
        logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        # Load configuration
        config = load_config()
        
        # Check if WordPress credentials are configured
        if config['wordpress']['site_url'] == 'https://your-wordpress-site.com':
            logger.error("WordPress credentials not configured. Please update config.json")
            return False
        
        # Initialize automation
        automation = ContentAutomation(config)
        
        # Run automation specifically for viral and UP content
        max_posts = config['automation'].get('max_posts_per_run', 5)
        logger.info(f"Running viral/UP automation with max_posts={max_posts}")
        
        # Call the new method for viral/UP only
        automation.run_viral_up_automation(max_posts)
        
        logger.info("=" * 60)
        logger.info("VIRAL & UP automation run completed successfully")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"VIRAL & UP automation failed: {str(e)}")
        return False

def run_multi_source_automation():
    """Run automation for multi-source news (every 45 minutes)"""
    logger = setup_scheduler_logging()
    
    try:
        logger.info("=" * 60)
        logger.info("Starting MULTI-SOURCE automation run (45-minute interval)")
        logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        # Load configuration
        config = load_config()
        
        # Check if WordPress credentials are configured
        if config['wordpress']['site_url'] == 'https://your-wordpress-site.com':
            logger.error("WordPress credentials not configured. Please update config.json")
            return False
        
        # Initialize automation
        automation = ContentAutomation(config)
        
        # Run automation for multi-source content only
        max_posts = config['automation'].get('max_posts_per_run', 3)
        logger.info(f"Running multi-source automation with max_posts={max_posts}")
        
        # Call the new method for multi-source only
        automation.run_multi_source_automation(max_posts)
        
        logger.info("=" * 60)
        logger.info("MULTI-SOURCE automation run completed successfully")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"MULTI-SOURCE automation failed: {str(e)}")
        return False

def run_automation():
    """Run the automation process (legacy - runs all content types)"""
    logger = setup_scheduler_logging()
    
    try:
        logger.info("=" * 60)
        logger.info("Starting scheduled automation run (ALL CONTENT TYPES)")
        logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        # Load configuration
        config = load_config()
        
        # Check if WordPress credentials are configured
        if config['wordpress']['site_url'] == 'https://your-wordpress-site.com':
            logger.error("WordPress credentials not configured. Please update config.json")
            return False
        
        # Initialize automation
        automation = ContentAutomation(config)
        
        # Run automation with default settings
        max_posts = config['automation'].get('max_posts_per_run', 3)
        logger.info(f"Running automation with max_posts={max_posts}")
        
        automation.run_automation(max_posts)
        
        logger.info("=" * 60)
        logger.info("Scheduled automation run completed successfully")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Scheduled automation failed: {str(e)}")
        return False

def run_image_retry():
    """Run image retry for existing posts"""
    logger = setup_scheduler_logging()
    
    try:
        logger.info("=" * 60)
        logger.info("Starting scheduled image retry run")
        logger.info(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)
        
        # Load configuration
        config = load_config()
        
        # Initialize automation
        automation = ContentAutomation(config)
        
        # Run image retry for recent posts
        max_posts = 10
        logger.info(f"Running image retry with max_posts={max_posts}")
        
        automation.retry_images_for_existing_posts(max_posts)
        
        logger.info("=" * 60)
        logger.info("Scheduled image retry run completed successfully")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Scheduled image retry failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "automation":
            success = run_automation()
            sys.exit(0 if success else 1)
        elif command == "viral_up":
            success = run_viral_up_automation()
            sys.exit(0 if success else 1)
        elif command == "multi_source":
            success = run_multi_source_automation()
            sys.exit(0 if success else 1)
        elif command == "image_retry":
            success = run_image_retry()
            sys.exit(0 if success else 1)
        else:
            print("Usage: python scheduler.py [automation|viral_up|multi_source|image_retry]")
            sys.exit(1)
    else:
        # Default: run automation (all content types)
        success = run_automation()
        sys.exit(0 if success else 1) 