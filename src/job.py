from dataclasses import dataclass, field
from typing import Optional
from loguru import logger


@dataclass
class Job:
    """
    Dataclass representing job details.

    Attributes:
        title (str): The title of the job.
        company (str): The company offering the job.
        location (str): The location of the job.
        link (str): The URL link to the job posting.
        apply_method (str): The method to apply for the job.
        description (str, optional): The full description of the job. Defaults to an empty string.
        summarize_job_description (str, optional): A summarized version of the job description. Defaults to an empty string.
        pdf_path (str, optional): The path to the PDF file related to the job. Defaults to an empty string.
        recruiter_link (str, optional): The link to the recruiter's profile. Defaults to an empty string.
    """
    title: str
    company: str
    location: str
    link: str
    apply_method: str
    description: str = field(default="", repr=False)
    summarize_job_description: str = field(default="", repr=False)
    pdf_path: str = ""
    recruiter_link: str = ""

    def __post_init__(self):
        """
        Post-initialization method to validate the job data.
        """
        self._validate_non_empty_fields()
        logger.debug(f"Job instance created: {self.title} at {self.company}")

    def _validate_non_empty_fields(self):
        """
        Validates that required fields are not empty.
        """
        required_fields = ['title', 'company', 'location', 'link', 'apply_method']
        for field in required_fields:
            if not getattr(self, field):
                logger.error(f"Required field '{field}' is empty")
                raise ValueError(f"'{field}' cannot be empty.")

    def set_summarize_job_description(self, summarize_job_description: str) -> None:
        """
        Sets the summarized job description.

        Args:
            summarize_job_description (str): The summarized job description.
        """
        logger.debug(f"Setting summarized job description for {self.title} at {self.company}")
        self.summarize_job_description = summarize_job_description

    def set_job_description(self, description: str) -> None:
        """
        Sets the full job description.

        Args:
            description (str): The full job description.
        """
        logger.debug(f"Setting job description for {self.title} at {self.company}")
        self.description = description

    def set_recruiter_link(self, recruiter_link: str) -> None:
        """
        Sets the recruiter's profile link.

        Args:
            recruiter_link (str): The link to the recruiter's profile.
        """
        logger.debug(f"Setting recruiter link for {self.title} at {self.company}: {recruiter_link}")
        self.recruiter_link = recruiter_link

    def formatted_job_information(self) -> str:
        """
        Formats the job information as a markdown string.

        Returns:
            str: The formatted job information.
        """
        logger.debug(f"Formatting job information for {self.title} at {self.company}")
        job_information = f"""
        # Job Description
        ## Job Information 
        - Position: {self.title}
        - At: {self.company}
        - Location: {self.location}
        - Recruiter Profile: {self.recruiter_link or 'Not available'}
        - Apply Method: {self.apply_method}
        - Job Link: {self.link}
        
        ## Description
        {self.description or 'No description provided.'}
        
        ## Summarized Description
        {self.summarize_job_description or 'No summarized description available.'}
        """
        formatted_information = job_information.strip()
        logger.debug(f"Job information formatted for {self.title} at {self.company}")
        return formatted_information

    def __str__(self) -> str:
        """
        Returns a string representation of the Job instance.

        Returns:
            str: A concise string representation of the job.
        """
        return f"Job(title='{self.title}', company='{self.company}', location='{self.location}')"


# Usage example
if __name__ == "__main__":
    try:
        job = Job(
            title="Software Engineer",
            company="Tech Corp",
            location="Remote",
            link="https://example.com/job",
            apply_method="Easy Apply"
        )
        job.set_job_description("We are looking for a talented software engineer...")
        job.set_summarize_job_description("Software engineering role for a tech company.")
        job.set_recruiter_link("https://linkedin.com/recruiter")
        
        print(job)
        print(job.formatted_job_information())
    except Exception as e:
        logger.error(f"Error creating or using Job instance: {e}")
