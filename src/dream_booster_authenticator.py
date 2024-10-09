import random
import time
import yaml
from selenium import webdriver
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, NoAlertPresentException,
    UnexpectedAlertPresentException, WebDriverException
)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from loguru import logger


class DreamBoosterAuthenticator:

    def __init__(self, config_path, secrets_path, driver=None):
        try:
            self.config = self.load_yaml(config_path)
            self.secrets = self.load_yaml(secrets_path)
            self.driver = driver
            logger.debug(f"DreamBoosterAuthenticator initialized with driver: {driver}")
        except Exception as e:
            logger.error(f"Failed to initialize DreamBoosterAuthenticator: {str(e)}")
            raise

    def load_yaml(self, file_path):
        try:
            with open(file_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            logger.error(f"YAML file not found: {file_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {file_path}: {str(e)}")
            raise

    def setup_driver(self):
        if not self.driver:
            try:
                options = webdriver.ChromeOptions()
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                self.driver = webdriver.Chrome(options=options)
                logger.info("Chrome driver set up successfully")
            except WebDriverException as e:
                logger.error(f"Failed to set up Chrome driver: {str(e)}")
                raise

    def start(self, portal_name):
        logger.info(f"Checking if user is already logged in to {portal_name}.")
        if self.is_logged_in(portal_name):
            logger.info(f"User is already logged in to {portal_name}.")
            return True
        else:
            logger.warning(f"User is not logged in to {portal_name}. Please log in manually.")
            input("Press Enter after you have logged in manually...")
            if self.is_logged_in(portal_name):
                logger.info(f"Login confirmed for {portal_name}.")
                return True
            else:
                logger.error(f"Login failed for {portal_name}.")
                return False

    def handle_login(self, portal_name):
        try:
            portal_config = self.get_portal_config(portal_name)
            logger.info(f"Navigating to the {portal_name} login page...")
            self.driver.get(portal_config['login_url'])
            if portal_config['feed_url'] in self.driver.current_url:
                logger.debug(f"User is already logged in to {portal_name}.")
                return True
            
            success = self.enter_credentials(portal_name)
            if not success:
                return False

            # Check for CAPTCHA or security verification
            if self.is_captcha_present() or self.is_security_verification_present():
                logger.warning("CAPTCHA or security verification detected. Manual intervention required.")
                input("Please solve the CAPTCHA or complete the security verification manually, then press Enter to continue...")
            
            # Wait for successful login
            try:
                WebDriverWait(self.driver, 60).until(
                    EC.url_contains(portal_config['feed_url'])
                )
                logger.info(f"Successfully logged in to {portal_name}")
                return True
            except TimeoutException:
                logger.error(f"Login to {portal_name} failed or timed out")
                return False

        except Exception as e:
            logger.error(f"An error occurred during login process for {portal_name}: {str(e)}")
            return False

    def is_captcha_present(self):
        try:
            return bool(self.driver.find_element(By.ID, 'captcha-challenge'))
        except NoSuchElementException:
            return False

    def is_security_verification_present(self):
        try:
            return bool(self.driver.find_element(By.ID, 'security-verification-challenge'))
        except NoSuchElementException:
            return False

    def enter_credentials(self, portal_name):
        portal_config = self.get_portal_config(portal_name)
        try:
            logger.debug(f"Entering credentials for {portal_name}...")
            
            username = self.secrets.get(f'{portal_name.lower()}_username')
            password = self.secrets.get(f'{portal_name.lower()}_password')

            logger.debug(f"Username found: {'Yes' if username else 'No'}")
            logger.debug(f"Password found: {'Yes' if password else 'No'}")

            if not username or not password:
                logger.error(f"Credentials for {portal_name} not found in secrets file")
                return False

            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "username"))
            )
            logger.debug("Username field found")
            username_field.send_keys(username)
            logger.debug("Username entered")

            password_field = self.driver.find_element(By.ID, portal_config['login_element'])
            logger.debug("Password field found")
            password_field.send_keys(password)
            logger.debug("Password entered")

            login_button = self.driver.find_element(By.XPATH, "//button[@type='submit']")
            logger.debug("Login button found")
            login_button.click()
            logger.debug("Login button clicked")

            return True

        except Exception as e:
            logger.error(f"An error occurred while entering credentials for {portal_name}: {str(e)}")
            return False

    def handle_security_check(self, portal_name):
        portal_config = self.get_portal_config(portal_name)
        try:
            logger.debug(f"Handling security check for {portal_name}...")
            WebDriverWait(self.driver, 10).until(
                EC.url_contains(portal_config['security_check_url'])
            )
            logger.warning(f"Security checkpoint detected for {portal_name}. Please complete the challenge.")
            WebDriverWait(self.driver, 300).until(
                EC.url_contains(portal_config['feed_url'])
            )
            logger.info(f"Security check completed for {portal_name}")
            return True
        except TimeoutException:
            logger.error(f"Security check not completed for {portal_name}. Please try again later.")
            return False
        except Exception as e:
            logger.error(f"An error occurred during security check for {portal_name}: {str(e)}")
            return False

    def is_logged_in(self, portal_name):
        portal_config = self.get_portal_config(portal_name)
        try:
            self.driver.get(portal_config['feed_url'])
            logger.debug(f"Checking if user is logged in to {portal_name}...")
            WebDriverWait(self.driver, 3).until(
                EC.presence_of_element_located((By.CLASS_NAME, portal_config['feed_element']))
            )

            profile_img_elements = self.driver.find_elements(By.XPATH, portal_config['profile_image_xpath'])
            if profile_img_elements:
                logger.info(f"Profile image found. Assuming user is logged in to {portal_name}.")
                return True

            logger.info(f"Did not find profile image. User might not be logged in to {portal_name}.")
            return False

        except TimeoutException:
            logger.error(f"Page elements took too long to load or were not found for {portal_name}.")
            return False
        except Exception as e:
            logger.error(f"An error occurred while checking login status for {portal_name}: {str(e)}")
            return False

    def get_portal_config(self, portal_name):
        try:
            job_portals = self.config.get('job_portals', [])
            if not job_portals:
                raise ValueError("No job portals configured in the configuration file")
            
            portal_config = next((portal for portal in job_portals if portal['name'] == portal_name), None)
            if not portal_config:
                raise ValueError(f"Portal '{portal_name}' not found in configuration")
            return portal_config
        except Exception as e:
            logger.error(f"Failed to get portal configuration for {portal_name}: {str(e)}")
            raise

    def close(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Browser closed successfully.")
            except Exception as e:
                logger.error(f"An error occurred while closing the browser: {str(e)}")

# Usage example
if __name__ == "__main__":
    try:
        authenticator = DreamBoosterAuthenticator("data_folder/config.yaml", "data_folder/secrets.yaml")
        
        for portal in authenticator.config['job_portals']:
            portal_name = portal['name']
            try:
                if authenticator.start(portal_name):
                    logger.info(f"Authentication successful for {portal_name}")
                else:
                    logger.error(f"Authentication failed for {portal_name}")
            except Exception as e:
                logger.error(f"An error occurred during authentication process for {portal_name}: {str(e)}")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
    finally:
        if 'authenticator' in locals():
            authenticator.close()