import base64
import json
import os
import random
import re
import time
import traceback
from typing import List, Optional, Any, Tuple

from httpx import HTTPStatusError
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from selenium.common.exceptions import NoSuchElementException, TimeoutException, ElementClickInterceptedException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

import src.utils as utils
from loguru import logger


class DreamBoosterEasyApplier:
    def __init__(self, driver: Any, resume_dir: Optional[str], set_old_answers: List[Tuple[str, str, str]],
                 gpt_answerer: Any, resume_generator_manager):
        logger.debug("Initializing DreamBoosterEasyApplier")
        if resume_dir is None or not os.path.exists(resume_dir):
            resume_dir = None
        self.driver = driver
        self.resume_path = resume_dir
        self.set_old_answers = set_old_answers
        self.gpt_answerer = gpt_answerer
        self.resume_generator_manager = resume_generator_manager
        self.all_data = self._load_questions_from_json()
        self.max_retries = 3
        logger.debug("DreamBoosterEasyApplier initialized successfully")

    def _load_questions_from_json(self) -> List[dict]:
        output_file = 'answers.json'
        logger.debug(f"Loading questions from JSON file: {output_file}")
        try:
            with open(output_file, 'r') as f:
                try:
                    data = json.load(f)
                    if not isinstance(data, list):
                        raise ValueError("JSON file format is incorrect. Expected a list of questions.")
                except json.JSONDecodeError:
                    logger.error("JSON decoding failed")
                    data = []
            logger.debug("Questions loaded successfully from JSON")
            return data
        except FileNotFoundError:
            logger.warning("JSON file not found, returning empty list")
            return []
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Error loading questions data from JSON file: {tb_str}")
            raise Exception(f"Error loading questions data from JSON file: \nTraceback:\n{tb_str}")

    def check_for_premium_redirect(self, job: Any, max_attempts=3):
        current_url = self.driver.current_url
        attempts = 0

        while "linkedin.com/premium" in current_url and attempts < max_attempts:
            logger.warning("Redirected to Dream Booster Premium page. Attempting to return to job page.")
            attempts += 1

            self.driver.get(job.link)
            time.sleep(2)
            current_url = self.driver.current_url

        if "linkedin.com/premium" in current_url:
            logger.error(f"Failed to return to job page after {max_attempts} attempts. Cannot apply for the job.")
            raise Exception(
                f"Redirected to Dream Booster Premium page and failed to return after {max_attempts} attempts. Job application aborted.")
            
    def apply_to_job(self, job: Any) -> None:
        logger.debug(f"Applying to job: {job}")
        try:
            self.job_apply(job)
            logger.info(f"Successfully applied to job: {job.title}")
        except Exception as e:
            logger.error(f"Failed to apply to job: {job.title}, error: {str(e)}")
            raise e

    def job_apply(self, job: Any):
        logger.debug(f"Starting job application for job: {job}")

        for attempt in range(self.max_retries):
            try:
                self._execute_job_apply(job)
                return  # If successful, exit the function
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise  # If all attempts fail, raise the last exception
                time.sleep(random.uniform(2, 5))  # Wait before retrying

    def _execute_job_apply(self, job: Any):
        try:
            self.driver.get(job.link)
            logger.debug(f"Navigated to job link: {job.link}")
        except Exception as e:
            logger.error(f"Failed to navigate to job link: {job.link}, error: {str(e)}")
            raise

        time.sleep(random.uniform(3, 5))
        self.check_for_premium_redirect(job)

        try:
            self.driver.execute_script("document.activeElement.blur();")
            logger.debug("Focus removed from the active element")

            self.check_for_premium_redirect(job)

            easy_apply_button = self._find_easy_apply_button(job)

            self.check_for_premium_redirect(job)

            logger.debug("Retrieving job description")
            job_description = self._get_job_description()
            job.set_job_description(job_description)
            logger.debug(f"Job description set: {job_description[:100]}")

            logger.debug("Retrieving recruiter link")
            recruiter_link = self._get_job_recruiter()
            job.set_recruiter_link(recruiter_link)
            logger.debug(f"Recruiter link set: {recruiter_link}")

            logger.debug("Attempting to click 'Easy Apply' button")
            self._click_button(easy_apply_button)
            logger.debug("'Easy Apply' button clicked successfully")

            logger.debug("Passing job information to GPT Answerer")
            self.gpt_answerer.set_job(job)

            logger.debug("Filling out application form")
            self._fill_application_form(job)
            logger.debug(f"Job application process completed successfully for job: {job}")

        except Exception as e:
            tb_str = traceback.format_exc()
            logger.error(f"Failed to apply to job: {job}, error: {tb_str}")

            logger.debug("Discarding application due to failure")
            self._discard_application()

            raise Exception(f"Failed to apply to job! Original exception:\nTraceback:\n{tb_str}")

    def _click_button(self, button: WebElement):
        try:
            button.click()
        except ElementClickInterceptedException:
            self.driver.execute_script("arguments[0].click();", button)

    def _find_easy_apply_button(self, job: Any) -> WebElement:
        logger.debug("Searching for 'Easy Apply' button")
        attempt = 0

        search_methods = [
            {
                'description': "find all 'Easy Apply' buttons using find_elements",
                'find_elements': True,
                'xpath': '//button[contains(@class, "jobs-apply-button") and contains(., "Easy Apply")]'
            },
            {
                'description': "'aria-label' containing 'Easy Apply to'",
                'xpath': '//button[contains(@aria-label, "Easy Apply to")]'
            },
            {
                'description': "button text search",
                'xpath': '//button[contains(text(), "Easy Apply") or contains(text(), "Apply now")]'
            }
        ]

        while attempt < 2:
            self.check_for_premium_redirect(job)
            self._scroll_page()

            for method in search_methods:
                try:
                    logger.debug(f"Attempting search using {method['description']}")

                    if method.get('find_elements'):
                        buttons = self.driver.find_elements(By.XPATH, method['xpath'])
                        if buttons:
                            for index, button in enumerate(buttons):
                                try:
                                    WebDriverWait(self.driver, 10).until(EC.visibility_of(button))
                                    WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(button))
                                    logger.debug(f"Found 'Easy Apply' button {index + 1}, attempting to click")
                                    return button
                                except Exception as e:
                                    logger.warning(f"Button {index + 1} found but not clickable: {e}")
                        else:
                            raise TimeoutException("No 'Easy Apply' buttons found")
                    else:
                        button = WebDriverWait(self.driver, 10).until(
                            EC.presence_of_element_located((By.XPATH, method['xpath']))
                        )
                        WebDriverWait(self.driver, 10).until(EC.visibility_of(button))
                        WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(button))
                        logger.debug("Found 'Easy Apply' button, attempting to click")
                        return button

                except TimeoutException:
                    logger.warning(f"Timeout during search using {method['description']}")
                except Exception as e:
                    logger.warning(
                        f"Failed to click 'Easy Apply' button using {method['description']} on attempt {attempt + 1}: {e}")

            self.check_for_premium_redirect(job)

            if attempt == 0:
                logger.debug("Refreshing page to retry finding 'Easy Apply' button")
                self.driver.refresh()
                time.sleep(random.randint(3, 5))
            attempt += 1

        page_source = self.driver.page_source
        logger.error(f"No clickable 'Easy Apply' button found after 2 attempts. Page source:\n{page_source}")
        raise Exception("No clickable 'Easy Apply' button found")

    def _get_job_description(self) -> str:
        logger.debug("Getting job description")
        try:
            try:
                see_more_button = self.driver.find_element(By.XPATH,
                                                           '//button[@aria-label="Click to see more description"]')
                self._click_button(see_more_button)
                time.sleep(2)
            except NoSuchElementException:
                logger.debug("See more button not found, skipping")

            description = self.driver.find_element(By.CLASS_NAME, 'jobs-description-content__text').text
            logger.debug("Job description retrieved successfully")
            return description
        except NoSuchElementException:
            tb_str = traceback.format_exc()
            logger.error(f"Job description not found: {tb_str}")
            raise Exception(f"Job description not found: \nTraceback:\n{tb_str}")
        except Exception:
            tb_str = traceback.format_exc()
            logger.error(f"Error getting Job description: {tb_str}")
            raise Exception(f"Error getting Job description: \nTraceback:\n{tb_str}")

    def _get_job_recruiter(self):
        logger.debug("Getting job recruiter information")
        try:
            hiring_team_section = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, '//h2[text()="Meet the hiring team"]'))
            )
            logger.debug("Hiring team section found")

            recruiter_elements = hiring_team_section.find_elements(By.XPATH,
                                                                   './/following::a[contains(@href, "linkedin.com/in/")]')

            if recruiter_elements:
                recruiter_element = recruiter_elements[0]
                recruiter_link = recruiter_element.get_attribute('href')
                logger.debug(f"Job recruiter link retrieved successfully: {recruiter_link}")
                return recruiter_link
            else:
                logger.debug("No recruiter link found in the hiring team section")
                return ""
        except Exception as e:
            logger.warning(f"Failed to retrieve recruiter information: {e}")
            return ""

    def _scroll_page(self) -> None:
        logger.debug("Scrolling the page")
        scrollable_element = self.driver.find_element(By.TAG_NAME, 'html')
        utils.scroll_slow(self.driver, scrollable_element, step=300, reverse=False)
        utils.scroll_slow(self.driver, scrollable_element, step=300, reverse=True)

    def _fill_application_form(self, job):
        logger.debug(f"Filling out application form for job: {job}")
        while True:
            self.fill_up(job)
            if self._next_or_submit():
                logger.debug("Application form submitted")
                break

    def _next_or_submit(self):
        logger.debug("Clicking 'Next' or 'Submit' button")
        next_button = self.driver.find_element(By.CLASS_NAME, "artdeco-button--primary")
        button_text = next_button.text.lower()
        if 'submit application' in button_text:
            logger.debug("Submit button found, submitting application")
            self._unfollow_company()
            time.sleep(random.uniform(1.5, 2.5))
            self._click_button(next_button)
            time.sleep(random.uniform(1.5, 2.5))
            return True
        time.sleep(random.uniform(1.5, 2.5))
        self._click_button(next_button)
        time.sleep(random.uniform(3.0, 5.0))
        self._check_for_errors()

    def _unfollow_company(self) -> None:
        try:
            logger.debug("Unfollowing company")
            follow_checkbox = self.driver.find_element(
                By.XPATH, "//label[contains(.,'to stay up to date with their page.')]")
            self._click_button(follow_checkbox)
        except Exception as e:
            logger.debug(f"Failed to unfollow company: {e}")

    def _check_for_errors(self) -> None:
        logger.debug("Checking for form errors")
        error_elements = self.driver.find_elements(By.CLASS_NAME, 'artdeco-inline-feedback--error')
        if error_elements:
            logger.error(f"Form submission failed with errors: {error_elements}")
            raise Exception(f"Failed answering or file upload. {str([e.text for e in error_elements])}")

    def _discard_application(self) -> None:
        logger.debug("Discarding application")
        try:
            discard_button = self.driver.find_element(By.CLASS_NAME, 'artdeco-modal__dismiss')
            self._click_button(discard_button)
            time.sleep(random.uniform(3, 5))
            confirm_button = self.driver.find_elements(By.CLASS_NAME, 'artdeco-modal__confirm-dialog-btn')[0]
            self._click_button(confirm_button)
            time.sleep(random.uniform(3, 5))
        except Exception as e:
            logger.warning(f"Failed to discard application: {e}")

    def fill_up(self, job) -> None:
        logger.debug(f"Filling up form sections for job: {job}")

        try:
            easy_apply_content = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, 'jobs-easy-apply-content'))
            )

            pb4_elements = easy_apply_content.find_elements(By.CLASS_NAME, 'pb4')
            for element in pb4_elements:
                self._process_form_element(element, job)
        except Exception as e:
            logger.error(f"Failed to find form elements: {e}")

    def _process_form_element(self, element: WebElement, job) -> None:
        logger.debug("Processing form element")
        if self._is_upload_field(element):
            self._handle_upload_fields(element, job)
        else:
            self._fill_additional_questions(element)

    def _is_upload_field(self, element: WebElement) -> bool:
        return 'upload' in element.text.lower()

    def _handle_upload_fields(self, element: WebElement, job) -> None:
        logger.debug("Handling upload fields")
        upload_button = element.find_element(By.CSS_SELECTOR, 'input[type="file"]')
        if self.resume_path:
            upload_button.send_keys(self.resume_path)
            logger.debug(f"Uploaded resume from path: {self.resume_path}")
        else:
            logger.warning("No resume path provided, skipping upload")

    def _fill_additional_questions(self, element: WebElement) -> None:
        logger.debug("Filling additional questions")
        try:
            question_element = element.find_element(By.TAG_NAME, 'label')
            question = question_element.text.strip()

            if self._is_dropdown_field(element):
                self._handle_dropdown_fields(element)
            elif self._is_text_field(element):
                self._handle_text_fields(element, question)
            elif self._is_radio_field(element):
                self._handle_radio_fields(element, question)
            else:
                logger.warning(f"Unhandled field type for question: {question}")
        except Exception as e:
            logger.error(f"Error filling additional question: {e}")

    def _is_dropdown_field(self, element: WebElement) -> bool:
        return element.find_elements(By.TAG_NAME, 'select')

    def _is_text_field(self, element: WebElement) -> bool:
        return element.find_elements(By.TAG_NAME, 'input') or element.find_elements(By.TAG_NAME, 'textarea')

    def _is_radio_field(self, element: WebElement) -> bool:
        return element.find_elements(By.XPATH, './/input[@type="radio"]')

    def _handle_dropdown_fields(self, element: WebElement) -> None:
        logger.debug("Handling dropdown fields")
        dropdown = element.find_element(By.TAG_NAME, 'select')
        select = Select(dropdown)
        options = [option.text for option in select.options]
        if len(options) > 1:
            selected_option = random.choice(options[1:])  # Exclude the first option as it's usually a placeholder
            select.select_by_visible_text(selected_option)
            logger.debug(f"Selected option: {selected_option}")

    def _handle_text_fields(self, element: WebElement, question: str) -> None:
        logger.debug(f"Handling text field for question: {question}")
        input_field = element.find_element(By.TAG_NAME, 'input') or element.find_element(By.TAG_NAME, 'textarea')
        answer = self._get_answer_for_question(question)
        input_field.send_keys(answer)
        logger.debug(f"Filled answer: {answer}")

    def _handle_radio_fields(self, element: WebElement, question: str) -> None:
        logger.debug(f"Handling radio field for question: {question}")
        radio_options = element.find_elements(By.XPATH, './/input[@type="radio"]')
        selected_option = random.choice(radio_options)
        self._click_button(selected_option)
        logger.debug(f"Selected radio option: {selected_option.get_attribute('value')}")

    def _get_answer_for_question(self, question: str) -> str:
        logger.debug(f"Getting answer for question: {question}")
        for item in self.all_data:
            if item['question'].lower() == question.lower():
                logger.debug(f"Found matching question, returning answer: {item['answer']}")
                return item['answer']
        
        logger.warning(f"No matching question found, generating answer using GPT")
        return self.gpt_answerer.answer_question(question)

# Usage example
if __name__ == "__main__":
    # Add your main execution code here
    pass