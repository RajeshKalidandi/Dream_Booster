from loguru import logger
from typing import List


class DreamBoosterBotState:
    def __init__(self):
        logger.debug("Initializing DreamBoosterBotState")
        self.reset()

    def reset(self):
        logger.debug("Resetting DreamBoosterBotState")
        self.credentials_set = False
        self.api_key_set = False
        self.job_application_profile_set = False
        self.gpt_answerer_set = False
        self.parameters_set = False
        self.logged_in = False
        self.application_process_active = False

    def validate_state(self, required_keys: List[str]):
        logger.debug(f"Validating DreamBoosterBotState with required keys: {required_keys}")
        for key in required_keys:
            if not getattr(self, key):
                logger.error(f"State validation failed: {key} is not set")
                raise ValueError(f"{key.replace('_', ' ').capitalize()} must be set before proceeding.")
        logger.debug("State validation passed")

    def set_application_process_active(self, active: bool):
        logger.debug(f"Setting application process active state to: {active}")
        self.application_process_active = active

    def is_application_process_active(self) -> bool:
        return self.application_process_active

    def __str__(self) -> str:
        return (f"DreamBoosterBotState(credentials_set={self.credentials_set}, "
                f"api_key_set={self.api_key_set}, "
                f"job_application_profile_set={self.job_application_profile_set}, "
                f"gpt_answerer_set={self.gpt_answerer_set}, "
                f"parameters_set={self.parameters_set}, "
                f"logged_in={self.logged_in}, "
                f"application_process_active={self.application_process_active})")