from loguru import logger
from typing import Any, Dict, List
from src.dream_booster_bot_state import DreamBoosterBotState
from src.job_application_profile import JobApplicationProfile


class DreamBoosterBotFacade:
    def __init__(self, login_component: Any, apply_component: Any):
        logger.debug("Initializing DreamBoosterBotFacade")
        self.login_component = login_component
        self.apply_component = apply_component
        self.state = DreamBoosterBotState()
        self.job_application_profile = None
        self.resume = None
        self.email = None
        self.password = None
        self.parameters = None
        self.gpt_answerer_component = None
        self.resume_generator_manager = None
        self.portal_name = None  # Added this line

    def set_job_application_profile_and_resume(self, job_application_profile: JobApplicationProfile, resume: str):
        logger.debug("Setting job application profile and resume")
        self._validate_non_empty(job_application_profile, "Job application profile")
        self._validate_non_empty(resume, "Resume")
        self.job_application_profile = job_application_profile
        self.resume = resume
        self.state.job_application_profile_set = True
        logger.debug("Job application profile and resume set successfully")

    def set_gpt_answerer_and_resume_generator(self, gpt_answerer_component: Any, resume_generator_manager: Any):
        logger.debug("Setting GPT answerer and resume generator")
        self._ensure_job_profile_and_resume_set()
        self.gpt_answerer_component = gpt_answerer_component
        self.resume_generator_manager = resume_generator_manager
        self.gpt_answerer_component.set_job_application_profile(self.job_application_profile)
        self.gpt_answerer_component.set_resume(self.resume)
        self.apply_component.set_gpt_answerer(self.gpt_answerer_component)
        self.apply_component.set_resume_generator_manager(self.resume_generator_manager)
        self.state.gpt_answerer_set = True
        logger.debug("GPT answerer and resume generator set successfully")

    def set_parameters(self, parameters: Dict[str, Any]):
        logger.debug("Setting parameters")
        self._validate_non_empty(parameters, "Parameters")
        self.parameters = parameters
        self.apply_component.set_parameters(parameters)
        self.state.credentials_set = True
        self.state.parameters_set = True
        self.portal_name = parameters.get('portal_name', 'LinkedIn')  # Added this line
        logger.debug("Parameters set successfully")

    def start_login(self):
        logger.debug("Starting login process")
        self.state.validate_state(['credentials_set'])
        try:
            if self.login_component.start(self.portal_name):
                self.state.logged_in = True
                logger.debug("Login process completed successfully")
            else:
                logger.error("Login failed")
                self.state.logged_in = False
        except Exception as e:
            logger.error(f"Login process failed: {str(e)}")
            self.state.logged_in = False
            raise

    def start_apply(self):
        logger.debug("Starting apply process")
        self.state.validate_state(['logged_in', 'job_application_profile_set', 'gpt_answerer_set', 'parameters_set'])
        try:
            self.apply_component.start_applying()
            logger.debug("Apply process started successfully")
        except Exception as e:
            logger.error(f"Apply process failed: {str(e)}")
            raise

    def _validate_non_empty(self, value: Any, name: str):
        logger.debug(f"Validating that {name} is not empty")
        if not value:
            logger.error(f"Validation failed: {name} is empty")
            raise ValueError(f"{name} cannot be empty.")
        logger.debug(f"Validation passed for {name}")

    def _ensure_job_profile_and_resume_set(self):
        logger.debug("Ensuring job profile and resume are set")
        if not self.state.job_application_profile_set:
            logger.error("Job application profile and resume are not set")
            raise ValueError("Job application profile and resume must be set before proceeding.")
        logger.debug("Job profile and resume are set")

    def update_job_application_profile(self, new_profile: JobApplicationProfile):
        logger.debug("Updating job application profile")
        self._validate_non_empty(new_profile, "New job application profile")
        self.job_application_profile = new_profile
        if self.gpt_answerer_component:
            self.gpt_answerer_component.set_job_application_profile(new_profile)
        logger.debug("Job application profile updated successfully")

    def update_resume(self, new_resume: str):
        logger.debug("Updating resume")
        self._validate_non_empty(new_resume, "New resume")
        self.resume = new_resume
        if self.gpt_answerer_component:
            self.gpt_answerer_component.set_resume(new_resume)
        logger.debug("Resume updated successfully")

    def get_application_status(self) -> Dict[str, Any]:
        logger.debug("Getting application status")
        return self.apply_component.get_application_status()

    def pause_application_process(self):
        logger.debug("Pausing application process")
        self.apply_component.pause_applying()

    def resume_application_process(self):
        logger.debug("Resuming application process")
        self.apply_component.resume_applying()

    def get_job_recommendations(self) -> List[Dict[str, Any]]:
        logger.debug("Getting job recommendations")
        return self.apply_component.get_job_recommendations()

    def refresh_login(self):
        logger.debug("Refreshing login")
        try:
            self.login_component.refresh()
            logger.debug("Login refreshed successfully")
        except Exception as e:
            logger.error(f"Login refresh failed: {str(e)}")
            raise

    def logout(self):
        logger.debug("Logging out")
        try:
            self.login_component.logout()
            self.state.reset()
            logger.debug("Logged out successfully")
        except Exception as e:
            logger.error(f"Logout failed: {str(e)}")
            raise