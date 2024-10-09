import os
import random
import sys
import time
from typing import Any

from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement
from loguru import logger
from PIL import ImageFont

from app_config import MINIMUM_LOG_LEVEL

log_file = "app_log.log"

# Configure logging
if MINIMUM_LOG_LEVEL in ["DEBUG", "TRACE", "INFO", "WARNING", "ERROR", "CRITICAL"]:
    logger.remove()
    logger.add(sys.stderr, level=MINIMUM_LOG_LEVEL)
    logger.add(log_file, rotation="10 MB", level=MINIMUM_LOG_LEVEL)
else:
    logger.warning(f"Invalid log level: {MINIMUM_LOG_LEVEL}. Defaulting to DEBUG.")
    logger.remove()
    logger.add(sys.stderr, level="DEBUG")
    logger.add(log_file, rotation="10 MB", level="DEBUG")

chromeProfilePath = os.path.join(os.getcwd(), "chrome_profile", "linkedin_profile")

def ensure_chrome_profile() -> str:
    """
    Ensures the Chrome profile directory exists.

    Returns:
        str: The path to the Chrome profile directory.
    """
    logger.debug(f"Ensuring Chrome profile exists at path: {chromeProfilePath}")
    profile_dir = os.path.dirname(chromeProfilePath)
    os.makedirs(profile_dir, exist_ok=True)
    os.makedirs(chromeProfilePath, exist_ok=True)
    logger.debug(f"Chrome profile directory ensured: {chromeProfilePath}")
    return chromeProfilePath

def is_scrollable(element: WebElement) -> bool:
    """
    Checks if the given element is scrollable.

    Args:
        element (WebElement): The element to check.

    Returns:
        bool: True if the element is scrollable, False otherwise.
    """
    try:
        scroll_height = int(element.get_attribute("scrollHeight"))
        client_height = int(element.get_attribute("clientHeight"))
        scrollable = scroll_height > client_height
        logger.debug(f"Element scrollable check: scrollHeight={scroll_height}, clientHeight={client_height}, scrollable={scrollable}")
        return scrollable
    except Exception as e:
        logger.error(f"Error checking if element is scrollable: {e}")
        return False

def scroll_slow(driver: webdriver.Chrome, scrollable_element: WebElement, start: int = 0, end: int = 3600, step: int = 300, reverse: bool = False) -> None:
    """
    Scrolls the given element slowly from start to end.

    Args:
        driver (webdriver.Chrome): The WebDriver instance.
        scrollable_element (WebElement): The element to scroll.
        start (int): The starting scroll position.
        end (int): The ending scroll position.
        step (int): The step size for each scroll.
        reverse (bool): Whether to scroll in reverse direction.
    """
    logger.debug(f"Starting slow scroll: start={start}, end={end}, step={step}, reverse={reverse}")

    if reverse:
        start, end = end, start
        step = -step

    if step == 0:
        logger.error("Step value cannot be zero.")
        raise ValueError("Step cannot be zero.")

    try:
        max_scroll_height = int(scrollable_element.get_attribute("scrollHeight"))
        current_scroll_position = int(float(scrollable_element.get_attribute("scrollTop")))
        logger.debug(f"Max scroll height of the element: {max_scroll_height}")
        logger.debug(f"Current scroll position: {current_scroll_position}")

        if reverse:
            start = min(start, current_scroll_position)
        else:
            end = min(end, max_scroll_height)

        script_scroll_to = "arguments[0].scrollTop = arguments[1];"

        if scrollable_element.is_displayed():
            if not is_scrollable(scrollable_element):
                logger.warning("The element is not scrollable.")
                return

            position = start
            previous_position = None
            while (step > 0 and position < end) or (step < 0 and position > end):
                if position == previous_position:
                    logger.debug(f"Stopping scroll as position hasn't changed: {position}")
                    break

                try:
                    driver.execute_script(script_scroll_to, scrollable_element, position)
                    logger.debug(f"Scrolled to position: {position}")
                except Exception as e:
                    logger.error(f"Error during scrolling: {e}")

                previous_position = position
                position += step

                step = max(10, abs(step) - 10) * (-1 if reverse else 1)

                time.sleep(random.uniform(0.6, 1.5))

            driver.execute_script(script_scroll_to, scrollable_element, end)
            logger.debug(f"Scrolled to final position: {end}")
            time.sleep(0.5)
        else:
            logger.warning("The element is not visible.")
    except Exception as e:
        logger.error(f"Exception occurred during scrolling: {e}")

def chrome_browser_options() -> webdriver.ChromeOptions:
    """
    Sets up Chrome browser options.

    Returns:
        webdriver.ChromeOptions: The configured Chrome options.
    """
    logger.debug("Setting Chrome browser options")
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")
    
    # Use existing Chrome profile
    options.add_argument(f"user-data-dir=C:\\Users\\Krish\\AppData\\Local\\Google\\Chrome\\User Data")
    options.add_argument("profile-directory=Rajesh Kalidandi")
    
    # Add these options to handle the "Chrome failed to start" error
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_argument("--remote-debugging-port=9222")  # Add this line
    options.add_experimental_option("excludeSwitches", ["enable-logging", "enable-automation"])
    options.add_experimental_option("detach", True)
    
    logger.debug("Chrome options set up successfully")
    return options

def printred(text: str) -> None:
    """
    Prints the given text in red.

    Args:
        text (str): The text to print.
    """
    red = "\033[91m"
    reset = "\033[0m"
    logger.debug("Printing text in red: %s", text)
    print(f"{red}{text}{reset}")

def printyellow(text: str) -> None:
    """
    Prints the given text in yellow.

    Args:
        text (str): The text to print.
    """
    yellow = "\033[93m"
    reset = "\033[0m"
    logger.debug("Printing text in yellow: %s", text)
    print(f"{yellow}{text}{reset}")

def stringWidth(text: str, font: ImageFont.FreeTypeFont, font_size: int) -> int:
    """
    Calculates the width of the given text in the specified font and size.

    Args:
        text (str): The text to measure.
        font (ImageFont.FreeTypeFont): The font to use.
        font_size (int): The font size.

    Returns:
        int: The width of the text.
    """
    try:
        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]
        logger.debug(f"Calculated width for text '{text}': {width}")
        return width
    except Exception as e:
        logger.error(f"Error calculating string width: {e}")
        return 0

# Usage example
if __name__ == "__main__":
    try:
        options = chrome_browser_options()
        logger.info("Chrome options set up successfully")
        
        printred("This is a test message in red")
        printyellow("This is a test message in yellow")
        
        # Note: This part requires a font file to be present
        # font = ImageFont.truetype("path/to/font.ttf", 12)
        # width = stringWidth("Test string", font, 12)
        # logger.info(f"Width of 'Test string': {width}")
    except Exception as e:
        logger.error(f"An error occurred: {e}")