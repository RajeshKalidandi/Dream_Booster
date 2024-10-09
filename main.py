import os
import re
import sys
from pathlib import Path
import yaml
import click
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import WebDriverException
from src.utils import chrome_browser_options
from src.llm.llm_manager import GPTAnswerer
from src.dream_booster_authenticator import DreamBoosterAuthenticator
from src.dream_booster_bot_facade import DreamBoosterBotFacade
from src.dream_booster_job_manager import DreamBoosterJobManager
from src.job_application_profile import JobApplicationProfile
from loguru import logger

# Suppress stderr
sys.stderr = open(os.devnull, 'w')

class ConfigError(Exception):
    pass

class ConfigValidator:
    @staticmethod
    def validate_email(email: str) -> bool:
        return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None
    
    @staticmethod
    def validate_yaml_file(yaml_path: Path) -> dict:
        try:
            with open(yaml_path, 'r') as stream:
                return yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise ConfigError(f"Error reading file {yaml_path}: {exc}")
        except FileNotFoundError:
            raise ConfigError(f"File not found: {yaml_path}")
    
    @staticmethod
    def validate_config(config_yaml_path: Path) -> dict:
        parameters = ConfigValidator.validate_yaml_file(config_yaml_path)
        required_keys = {
            'remote': bool,
            'experienceLevel': dict,
            'jobTypes': dict,
            'date': dict,
            'positions': list,
            'locations': list,
            'distance': int,
            'company_blacklist': list,
            'title_blacklist': list,
            'llm_model_type': str,
            'llm_model': str,
            'llm_api_url': str,
            'job_portals': list,
        }

        for key, expected_type in required_keys.items():
            if key not in parameters:
                if key in ['company_blacklist', 'title_blacklist']:
                    parameters[key] = []
                else:
                    raise ConfigError(f"Missing or invalid key '{key}' in config file {config_yaml_path}")
            elif not isinstance(parameters[key], expected_type):
                if key in ['company_blacklist', 'title_blacklist'] and parameters[key] is None:
                    parameters[key] = []
                else:
                    raise ConfigError(f"Invalid type for key '{key}' in config file {config_yaml_path}. Expected {expected_type}.")

        # Validate job_portals
        if 'job_portals' not in parameters or not parameters['job_portals']:
            raise ConfigError(f"Missing or empty 'job_portals' in config file {config_yaml_path}")

        for portal in parameters['job_portals']:
            required_portal_keys = ['name', 'login_url', 'feed_url', 'login_element', 'feed_element', 'profile_image_xpath', 'security_check_url']
            for key in required_portal_keys:
                if key not in portal:
                    raise ConfigError(f"Missing required key '{key}' in job portal configuration")

        return parameters

    @staticmethod
    def validate_secrets(secrets_yaml_path: Path) -> tuple:
        secrets = ConfigValidator.validate_yaml_file(secrets_yaml_path)
        mandatory_secrets = ['llm_api_key']

        for secret in mandatory_secrets:
            if secret not in secrets:
                raise ConfigError(f"Missing secret '{secret}' in file {secrets_yaml_path}")

        if not secrets['llm_api_key']:
            raise ConfigError(f"llm_api_key cannot be empty in secrets file {secrets_yaml_path}.")
        return secrets['llm_api_key']

class FileManager:
    @staticmethod
    def find_file(name_containing: str, with_extension: str, at_path: Path) -> Path:
        return next((file for file in at_path.iterdir() if name_containing.lower() in file.name.lower() and file.suffix.lower() == with_extension.lower()), None)

    @staticmethod
    def validate_data_folder(app_data_folder: Path) -> tuple:
        if not app_data_folder.exists() or not app_data_folder.is_dir():
            raise FileNotFoundError(f"Data folder not found: {app_data_folder}")

        required_files = ['secrets.yaml', 'config.yaml', 'plain_text_resume.yaml']
        missing_files = [file for file in required_files if not (app_data_folder / file).exists()]
        
        if missing_files:
            raise FileNotFoundError(f"Missing files in the data folder: {', '.join(missing_files)}")

        output_folder = app_data_folder / 'output'
        output_folder.mkdir(exist_ok=True)

        resume_file = app_data_folder / 'RajeshKalidandi_2024_Latest.pdf'
        if not resume_file.exists():
            logger.warning(f"Resume file not found: {resume_file}")
            resume_file = None

        return (app_data_folder / 'secrets.yaml', app_data_folder / 'config.yaml', app_data_folder / 'plain_text_resume.yaml', output_folder, resume_file)

    @staticmethod
    def file_paths_to_dict(resume_file: Path | None, plain_text_resume_file: Path) -> dict:
        if not plain_text_resume_file.exists():
            raise FileNotFoundError(f"Plain text resume file not found: {plain_text_resume_file}")

        result = {'plainTextResume': plain_text_resume_file}

        if resume_file and resume_file.exists():
            result['resume'] = resume_file
            logger.info(f"Resume file found and will be used: {resume_file}")
        else:
            logger.warning("No resume file found. The bot will not be able to upload a resume during applications.")

        return result

def init_browser() -> webdriver.Chrome:
    try:
        options = chrome_browser_options()
        service = ChromeService(ChromeDriverManager().install())
        
        # Try to close any existing Chrome instances
        os.system("taskkill /f /im chrome.exe")
        
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)  # Set a page load timeout
        return driver
    except Exception as e:
        logger.error(f"Failed to initialize browser: {str(e)}")
        raise RuntimeError(f"Failed to initialize browser: {str(e)}")

def create_and_run_bot(parameters, llm_api_key, secrets_path, config_path):
    browser = None
    try:
        with open(parameters['uploads']['plainTextResume'], "r", encoding='utf-8') as file:
            plain_text_resume = file.read()
        
        job_application_profile = JobApplicationProfile.from_yaml(plain_text_resume)
        
        parameters['portal_name'] = 'LinkedIn'  # or whatever portal you're using
        
        browser = init_browser()
        login_component = DreamBoosterAuthenticator(config_path, secrets_path, browser)
        apply_component = DreamBoosterJobManager(browser)
        gpt_answerer_component = GPTAnswerer(parameters, llm_api_key)
        bot = DreamBoosterBotFacade(login_component, apply_component)
        bot.set_job_application_profile_and_resume(job_application_profile, plain_text_resume)
        bot.set_gpt_answerer_and_resume_generator(gpt_answerer_component, None)
        bot.set_parameters(parameters)
        
        # Check login status
        bot.start_login()
        if not bot.state.logged_in:
            logger.error("Failed to confirm login. Exiting.")
            return
        
        # If login is confirmed, start applying
        bot.start_apply()
    except WebDriverException as e:
        logger.error(f"WebDriver error occurred: {e}")
    except Exception as e:
        logger.error(f"Error running the bot: {str(e)}")
    finally:
        if browser:
            try:
                browser.quit()
            except Exception as e:
                logger.error(f"Error closing browser: {str(e)}")

@click.command()
@click.option('--resume', type=click.Path(exists=True, file_okay=True, dir_okay=False, path_type=Path), help="Path to the resume PDF file")
def main(resume: Path = None):
    try:
        data_folder = Path("data_folder")
        secrets_file, config_file, plain_text_resume_file, output_folder, default_resume_file = FileManager.validate_data_folder(data_folder)
        
        parameters = ConfigValidator.validate_config(config_file)
        llm_api_key = ConfigValidator.validate_secrets(secrets_file)
        
        resume_to_use = resume or default_resume_file
        parameters['uploads'] = FileManager.file_paths_to_dict(resume_to_use, plain_text_resume_file)
        parameters['outputFileDirectory'] = output_folder
        
        create_and_run_bot(parameters, llm_api_key, secrets_file, config_file)
    except ConfigError as ce:
        logger.error(f"Configuration error: {str(ce)}")
        logger.error(f"Refer to the configuration guide for troubleshooting: [Your project's configuration guide URL]")
    except FileNotFoundError as fnf:
        logger.error(f"File not found: {str(fnf)}")
        logger.error("Ensure all required files are present in the data folder.")
        logger.error("Refer to the file setup guide: [Your project's file setup guide URL]")
    except RuntimeError as re:
        logger.error(f"Runtime error: {str(re)}")
        logger.error("Refer to the configuration and troubleshooting guide: [Your project's troubleshooting guide URL]")
    except Exception as e:
        logger.error(f"An unexpected error occurred: {str(e)}")
        logger.error("Refer to the general troubleshooting guide: [Your project's general troubleshooting guide URL]")

if __name__ == "__main__":
    main()