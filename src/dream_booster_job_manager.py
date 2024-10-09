import json
import os
import random
import time
from itertools import product
from pathlib import Path
from urllib.parse import quote

from inputimeout import inputimeout, TimeoutOccurred
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

import src.utils as utils
from app_config import MINIMUM_WAIT_TIME
from src.job import Job
from src.dream_booster_easy_applier import DreamBoosterEasyApplier
from loguru import logger


class EnvironmentKeys:
    def __init__(self):
        logger.debug("Initializing EnvironmentKeys")
        self.skip_apply = self._read_env_key_bool("SKIP_APPLY")
        self.disable_description_filter = self._read_env_key_bool("DISABLE_DESCRIPTION_FILTER")
        logger.debug(f"EnvironmentKeys initialized: skip_apply={self.skip_apply}, disable_description_filter={self.disable_description_filter}")

    @staticmethod
    def _read_env_key(key: str) -> str:
        value = os.getenv(key, "")
        logger.debug(f"Read environment key {key}: {value}")
        return value

    @staticmethod
    def _read_env_key_bool(key: str) -> bool:
        value = os.getenv(key) == "True"
        logger.debug(f"Read environment key {key} as bool: {value}")
        return value


class DreamBoosterJobManager:
    def __init__(self, driver):
        logger.debug("Initializing DreamBoosterJobManager")
        self.driver = driver
        self.set_old_answers = set()
        self.easy_applier_component = None
        self.job_matching_algorithm = None
        logger.debug("DreamBoosterJobManager initialized successfully")

    def set_parameters(self, parameters):
        logger.debug("Setting parameters for DreamBoosterJobManager")
        self.company_blacklist = parameters.get('company_blacklist', []) or []
        self.title_blacklist = parameters.get('title_blacklist', []) or []
        self.positions = parameters.get('positions', [])
        self.locations = parameters.get('locations', [])
        self.apply_once_at_company = parameters.get('apply_once_at_company', False)
        self.base_search_url = self.get_base_search_url(parameters)
        self.seen_jobs = []

        job_applicants_threshold = parameters.get('job_applicants_threshold', {})
        self.min_applicants = job_applicants_threshold.get('min_applicants', 0)
        self.max_applicants = job_applicants_threshold.get('max_applicants', float('inf'))

        resume_path = parameters.get('uploads', {}).get('resume', None)
        self.resume_path = Path(resume_path) if resume_path and Path(resume_path).exists() else None
        self.output_file_directory = Path(parameters['outputFileDirectory'])
        self.env_config = EnvironmentKeys()

        self.job_matching_algorithm = parameters.get('job_matching_algorithm', {})
        self.match_threshold = self.job_matching_algorithm.get('match_threshold', 0.75)
        self.keywords = self.job_matching_algorithm.get('keywords', [])

        logger.debug("Parameters set successfully")

    def set_gpt_answerer(self, gpt_answerer):
        logger.debug("Setting GPT answerer")
        self.gpt_answerer = gpt_answerer

    def set_resume_generator_manager(self, resume_generator_manager):
        logger.debug("Setting resume generator manager")
        self.resume_generator_manager = resume_generator_manager

    def start_applying(self, job_search: JobSearch):
        logger.debug("Starting job application process")
        self.easy_applier_component = DreamBoosterEasyApplier(self.driver, self.resume_path, self.set_old_answers,
                                                          self.gpt_answerer, self.resume_generator_manager)
        searches = list(product(self.positions, self.locations))
        random.shuffle(searches)
        page_sleep = 0
        minimum_time = MINIMUM_WAIT_TIME
        minimum_page_time = time.time() + minimum_time

        for page in range(self.max_pages):
            logger.debug(f"Going to job page {page}")
            try:
                self.next_job_page(page)
                logger.debug("Starting the application process for this page...")
                jobs = self.get_jobs_from_page()
                
                if not jobs:
                    logger.info(f"No jobs found on page {page}. Ending search.")
                    break  # Exit the loop if no jobs are found

                for job in jobs:
                    self.apply_job(job)

                logger.debug("Finished applying to jobs on this page.")
                
                if page < self.max_pages - 1:  # Don't wait after the last page
                    wait_time = random.uniform(15, 60)
                    logger.info(f"Waiting for {wait_time:.2f} seconds before moving to the next page...")
                    self.handle_waiting(wait_time)
            except Exception as e:
                logger.error(f"Error on page {page}: {str(e)}")
                break  # Exit the loop if an error occurs

        logger.info("Finished applying to all jobs.")

    def get_jobs_from_page(self):
        logger.debug("Getting jobs from current page")
        try:
            job_list = self.driver.find_element(By.CLASS_NAME, "jobs-search-results-list")
            self.scroll_to_load_jobs()
            job_elements = job_list.find_elements(By.CLASS_NAME, "jobs-search-results__list-item")
            
            if not job_elements:
                logger.info("No job elements found on this page.")
                return []

            jobs = []
            for job_element in job_elements:
                job = self.extract_job_information_from_tile(job_element)
                if job:
                    jobs.append(job)
            
            return jobs
        except Exception as e:
            logger.error(f"Error while fetching job elements: {str(e)}")
            return []

    def apply_jobs(self, job_list_elements):
        job_list = [Job(*self.extract_job_information_from_tile(job_element)) for job_element in job_list_elements]

        for job in job_list:
            logger.debug(f"Starting application for job: {job.title} at {job.company}")

            if not self.is_job_suitable(job):
                continue

            try:
                if job.apply_method not in {"Continue", "Applied", "Apply"}:
                    self.easy_applier_component.job_apply(job)
                    self.write_to_file(job, "success")
                    logger.debug(f"Applied to job: {job.title} at {job.company}")
            except Exception as e:
                logger.error(f"Failed to apply for {job.title} at {job.company}: {e}")
                self.write_to_file(job, "failed")
                continue

    def is_job_suitable(self, job):
        if self.is_blacklisted(job.title, job.company, job.link):
            logger.debug(f"Job blacklisted: {job.title} at {job.company}")
            self.write_to_file(job, "skipped")
            return False

        if self.is_already_applied_to_job(job.title, job.company, job.link):
            self.write_to_file(job, "skipped")
            return False

        if self.is_already_applied_to_company(job.company):
            self.write_to_file(job, "skipped")
            return False

        if not self.matches_job_criteria(job):
            logger.debug(f"Job does not match criteria: {job.title} at {job.company}")
            self.write_to_file(job, "skipped")
            return False

        return True

    def matches_job_criteria(self, job):
        match_score = sum(keyword.lower() in job.title.lower() or keyword.lower() in job.description.lower() 
                          for keyword in self.keywords) / len(self.keywords)
        return match_score >= self.match_threshold

    def write_to_file(self, job, file_name):
        logger.debug(f"Writing job application result to file: {file_name}")
        pdf_path = Path(job.pdf_path).resolve()
        pdf_path = pdf_path.as_uri()
        data = {
            "company": job.company,
            "job_title": job.title,
            "link": job.link,
            "job_recruiter": job.recruiter_link,
            "job_location": job.location,
            "pdf_path": pdf_path
        }
        file_path = self.output_file_directory / f"{file_name}.json"
        if not file_path.exists():
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump([data], f, indent=4)
                logger.debug(f"Job data written to new file: {file_name}")
        else:
            with open(file_path, 'r+', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    logger.error(f"JSON decode error in file: {file_path}")
                    existing_data = []
                existing_data.append(data)
                f.seek(0)
                json.dump(existing_data, f, indent=4)
                f.truncate()
                logger.debug(f"Job data appended to existing file: {file_name}")

    def get_base_search_url(self, parameters):
        base_url = "https://www.linkedin.com/jobs/search/?"
        filters = []
        
        if parameters.get('remote'):
            filters.append("f_WRA=true")
        
        experience_levels = [level for level, value in parameters.get('experienceLevel', {}).items() if value]
        if experience_levels:
            filters.append(f"f_E={','.join(experience_levels)}")
        
        job_types = [job_type for job_type, value in parameters.get('jobTypes', {}).items() if value]
        if job_types:
            filters.append(f"f_JT={','.join(job_types)}")
        
        date_posted = next((date for date, value in parameters.get('date', {}).items() if value), None)
        if date_posted:
            filters.append(f"f_TPR={date_posted.replace(' ', '%20')}")
        
        if parameters.get('distance'):
            filters.append(f"distance={parameters['distance']}")
        
        return base_url + "&".join(filters)

    def next_job_page(self, position, location_url, job_page_number):
        logger.debug(f"Navigating to next job page: {job_page_number}")
        encoded_position = quote(position)
        encoded_location = quote(location_url.replace("&location=", ""))
        url = f"{self.base_search_url}&keywords={encoded_position}&location={encoded_location}&start={job_page_number * 25}"
        logger.debug(f"Navigating to URL: {url}")
        self.driver.get(url)
        
        # Wait for the job list to load
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CLASS_NAME, "jobs-search-results__list"))
            )
            logger.debug("Job list loaded successfully")
        except TimeoutException:
            logger.error("Timeout waiting for job list to load")
        
        # Scroll down to load more jobs
        self.scroll_to_load_jobs()
        
        time.sleep(random.uniform(2, 4))

    def scroll_to_load_jobs(self):
        logger.debug("Scrolling to load more jobs")
        last_height = self.driver.execute_script("return document.body.scrollHeight")
        while True:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            new_height = self.driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        logger.debug("Finished scrolling")

    def extract_job_information_from_tile(self, job_tile):
        logger.debug("Extracting job information from tile")
        job_title, company, job_location, apply_method, link = "", "", "", "", ""
        try:
            job_title = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title').text
            link = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title').get_attribute('href').split('?')[0]
            company = job_tile.find_element(By.CLASS_NAME, 'job-card-container__primary-description').text
            logger.debug(f"Job information extracted: {job_title} at {company}")
        except NoSuchElementException:
            logger.warning("Some job information (title, link, or company) is missing.")
        try:
            job_location = job_tile.find_element(By.CLASS_NAME, 'job-card-container__metadata-item').text
        except NoSuchElementException:
            logger.warning("Job location is missing.")
        try:
            apply_method = job_tile.find_element(By.CLASS_NAME, 'job-card-container__apply-method').text
        except NoSuchElementException:
            apply_method = "Applied"
            logger.warning("Apply method not found, assuming 'Applied'.")

        return job_title, company, job_location, link, apply_method

    def is_blacklisted(self, job_title, company, link):
        logger.debug(f"Checking if job is blacklisted: {job_title} at {company}")
        job_title_words = job_title.lower().split(' ')
        title_blacklisted = any(word in job_title_words for word in self.title_blacklist)
        company_blacklisted = company.strip().lower() in (word.strip().lower() for word in self.company_blacklist)
        link_seen = link in self.seen_jobs
        is_blacklisted = title_blacklisted or company_blacklisted or link_seen
        logger.debug(f"Job blacklisted status: {is_blacklisted}")
        return is_blacklisted

    def is_already_applied_to_job(self, job_title, company, link):
        link_seen = link in self.seen_jobs
        return link_seen

    def is_already_applied_to_company(self, company):
        if not self.apply_once_at_company:
            return False

        output_files = ["success.json"]
        for file_name in output_files:
            file_path = self.output_file_directory / file_name
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    try:
                        existing_data = json.load(f)
                    except json.JSONDecodeError:
                        logger.error(f"JSON decode error in file: {file_path}")
                        existing_data = []
                    if any(job['company'].strip().lower() == company.strip().lower() for job in existing_data):
                        return True
        return False

    def handle_waiting(self, minimum_page_time):
        time_left = minimum_page_time - time.time()
        if time_left > 0:
            try:
                user_input = inputimeout(
                    prompt=f"Sleeping for {time_left:.2f} seconds. Press 'y' to skip waiting. Timeout 60 seconds : ",
                    timeout=60).strip().lower()
            except TimeoutOccurred:
                user_input = ''
            if user_input == 'y':
                logger.debug("User chose to skip waiting.")
            else:
                logger.debug(f"Sleeping for {time_left:.2f} seconds as user chose not to skip.")
                time.sleep(time_left)

    def handle_extended_waiting(self):
        sleep_time = random.randint(50, 90)
        try:
            user_input = inputimeout(
                prompt=f"Sleeping for {sleep_time / 60:.2f} minutes. Press 'y' to skip waiting: ",
                timeout=60).strip().lower()
        except TimeoutOccurred:
            user_input = ''
        if user_input == 'y':
            logger.debug("User chose to skip extended waiting.")
        else:
            logger.debug(f"Sleeping for {sleep_time} seconds.")
            time.sleep(sleep_time)

# Usage example
if __name__ == "__main__":
    # Add your main execution code here
    pass