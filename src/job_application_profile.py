from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
import yaml
from loguru import logger


@dataclass
class PersonalInformation:
    """
    Dataclass representing personal information.
    """
    name: str = "Rajesh"
    surname: str = "Kalidandi"
    country: str = "India"
    city: str = "Hyderabad"
    phone_prefix: str = "+91"
    phone: str = "8688586373"
    email: str = "kalidandiirajesh@gmail.com"
    github: str = "https://github.com/RajeshKalidandi"
    linkedin: str = "https://www.linkedin.com/in/rajesh-kalidandi"


@dataclass
class Education:
    """
    Dataclass representing education details.
    """
    education_level: str
    institution: str
    field_of_study: str
    year_of_completion: str


@dataclass
class Experience:
    """
    Dataclass representing work experience.
    """
    position: str
    company: str
    employment_period: str
    key_responsibilities: List[str]


@dataclass
class Project:
    """
    Dataclass representing a project.
    """
    name: str
    description: str


@dataclass
class Language:
    """
    Dataclass representing language proficiency.
    """
    language: str
    proficiency: str


@dataclass
class SelfIdentification:
    """
    Dataclass representing self-identification details.
    """
    gender: str = "Male"
    pronouns: str = "He/Him"
    veteran: str = "No"
    disability: str = "No"
    ethnicity: str = "Asian"


@dataclass
class LegalAuthorization:
    """
    Dataclass representing legal authorization details.
    """
    eu_work_authorization: str = "No"
    us_work_authorization: str = "No"
    requires_us_visa: str = "Yes"
    legally_allowed_to_work_in_us: str = "No"
    requires_us_sponsorship: str = "Yes"
    requires_eu_visa: str = "Yes"
    legally_allowed_to_work_in_eu: str = "No"
    requires_eu_sponsorship: str = "Yes"
    canada_work_authorization: str = "No"
    requires_canada_visa: str = "Yes"
    legally_allowed_to_work_in_canada: str = "No"
    requires_canada_sponsorship: str = "Yes"
    uk_work_authorization: str = "No"
    requires_uk_visa: str = "Yes"
    legally_allowed_to_work_in_uk: str = "No"
    requires_uk_sponsorship: str = "Yes"


@dataclass
class WorkPreferences:
    """
    Dataclass representing work preferences.
    """
    remote_work: str = "Yes"
    in_person_work: str = "Yes"
    open_to_relocation: str = "Yes"
    willing_to_complete_assessments: str = "Yes"
    willing_to_undergo_drug_tests: str = "Yes"
    willing_to_undergo_background_checks: str = "Yes"


@dataclass
class Availability:
    """
    Dataclass representing availability details.
    """
    notice_period: str = "2 weeks"


@dataclass
class SalaryExpectations:
    """
    Dataclass representing salary expectations.
    """
    salary_range_usd: str = "700000 - 1200000"


@dataclass
class JobApplicationProfile:
    """
    Dataclass representing the complete job application profile.
    """
    personal_information: PersonalInformation = field(default_factory=PersonalInformation)
    professional_summary: str = ""
    education_details: List[Education] = field(default_factory=list)
    skills: Dict[str, List[str]] = field(default_factory=dict)
    experience_details: List[Experience] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
    certifications: List[str] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    languages: List[Language] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    availability: Availability = field(default_factory=Availability)
    salary_expectations: SalaryExpectations = field(default_factory=SalaryExpectations)
    self_identification: SelfIdentification = field(default_factory=SelfIdentification)
    legal_authorization: LegalAuthorization = field(default_factory=LegalAuthorization)
    work_preferences: WorkPreferences = field(default_factory=WorkPreferences)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> 'JobApplicationProfile':
        """
        Creates a JobApplicationProfile instance from a YAML string.
        """
        logger.debug("Creating JobApplicationProfile from YAML string")
        try:
            data = yaml.safe_load(yaml_str)
            logger.debug(f"YAML data successfully parsed")
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file: {e}")
            raise ValueError("Error parsing YAML file.") from e

        if not isinstance(data, dict):
            logger.error(f"YAML data must be a dictionary, received: {type(data)}")
            raise TypeError("YAML data must be a dictionary.")

        profile = cls()
        profile._process_section(data, 'personal_information', PersonalInformation)
        profile.professional_summary = data.get('professional_summary', '')
        profile.education_details = [Education(**edu) for edu in data.get('education_details', [])]
        profile.skills = data.get('skills', {})
        profile.experience_details = [Experience(**exp) for exp in data.get('experience_details', [])]
        profile.projects = [Project(**proj) for proj in data.get('projects', [])]
        profile.certifications = data.get('certifications', [])
        profile.achievements = data.get('achievements', [])
        profile.languages = [Language(**lang) for lang in data.get('languages', [])]
        profile.interests = data.get('interests', [])
        profile._process_section(data, 'availability', Availability)
        profile._process_section(data, 'salary_expectations', SalaryExpectations)
        profile._process_section(data, 'self_identification', SelfIdentification)
        profile._process_section(data, 'legal_authorization', LegalAuthorization)
        profile._process_section(data, 'work_preferences', WorkPreferences)

        logger.debug("JobApplicationProfile creation completed successfully.")
        return profile

    def _process_section(self, data: Dict[str, Any], section_name: str, section_class: Any) -> None:
        """
        Processes a section of the YAML data and sets the corresponding attribute.
        """
        logger.debug(f"Processing {section_name}")
        try:
            section_data = data.get(section_name, {})
            section_instance = section_class(**section_data)
            setattr(self, section_name, section_instance)
            logger.debug(f"{section_name} processed successfully")
        except Exception as e:
            logger.error(f"An error occurred while processing {section_name}: {e}")
            raise

    def __str__(self) -> str:
        """
        Generates a string representation of the JobApplicationProfile.
        """
        logger.debug("Generating string representation of JobApplicationProfile")

        def format_dataclass(obj):
            return "\n".join(f"  {field.name}: {getattr(obj, field.name)}" for field in obj.__dataclass_fields__.values())

        formatted_str = (
            f"Job Application Profile:\n"
            f"Personal Information:\n{format_dataclass(self.personal_information)}\n\n"
            f"Professional Summary:\n{self.professional_summary}\n\n"
            f"Education:\n{', '.join(str(edu) for edu in self.education_details)}\n\n"
            f"Skills:\n{self.skills}\n\n"
            f"Experience:\n{', '.join(str(exp) for exp in self.experience_details)}\n\n"
            f"Projects:\n{', '.join(str(proj) for proj in self.projects)}\n\n"
            f"Certifications:\n{', '.join(self.certifications)}\n\n"
            f"Achievements:\n{', '.join(self.achievements)}\n\n"
            f"Languages:\n{', '.join(str(lang) for lang in self.languages)}\n\n"
            f"Interests:\n{', '.join(self.interests)}\n\n"
            f"Availability:\n{format_dataclass(self.availability)}\n\n"
            f"Salary Expectations:\n{format_dataclass(self.salary_expectations)}\n\n"
            f"Self Identification:\n{format_dataclass(self.self_identification)}\n\n"
            f"Legal Authorization:\n{format_dataclass(self.legal_authorization)}\n\n"
            f"Work Preferences:\n{format_dataclass(self.work_preferences)}"
        )
        logger.debug("String representation generated")
        return formatted_str


# Usage example
if __name__ == "__main__":
    yaml_str = """
    personal_information:
      name: "Rajesh"
      surname: "Kalidandi"
      country: "India"
      city: "Hyderabad"
      phone_prefix: "+91"
      phone: "8688586373"
      email: "kalidandiirajesh@gmail.com"
      github: "https://github.com/RajeshKalidandi"
      linkedin: "https://www.linkedin.com/in/rajesh-kalidandi"

    professional_summary: >
      Highly motivated and results-driven Computer Science and Engineering student with hands-on experience in
      data analysis, software development, and AI/ML projects. Proven ability to enhance system efficiency, design
      innovative solutions, and drive impactful results. Adept at collaborating with cross-functional teams and applying
      cutting-edge technologies to real-world problems. Seeking to leverage technical skills and creative problem-solving
      in a challenging role.

    education_details:
      - education_level: "B.Tech"
        institution: "Malla Reddy Engineering College"
        field_of_study: "Computer Science & Engineering (AI & ML)"
        year_of_completion: "Expected 2025"

    skills:
      programming_languages:
        - Python
        - Java
        - HTML
        - CSS
        - Node.js
      ai_ml:
        - Generative AI
        - Natural Language Processing (NLP)
        - Data Analysis
      frameworks:
        - Next.js 14
        - React
        - Tailwind CSS
        - Typescript
      databases:
        - SQL
        - MongoDB
        - Firebase
      tools:
        - GitHub
        - Postman
      other_skills:
        - Prompt Engineering
        - Digital Marketing
        - Content Creation
        - SaaS & No Code Development

    experience_details:
      - position: "Data Analyst Virtual Intern"
        company: "Accenture North America"
        employment_period: "Dec 2023"
        key_responsibilities:
          - "Analyzed and cleaned seven datasets for a social media client, uncovering actionable insights that informed strategic decision-making."
          - "Modeled data to generate visualizations and presented findings via PowerPoint and video, improving client engagement and decision-making processes."

    projects:
      - name: "TrackMyDrive- India's Driving School App"
        description: "Created a comprehensive platform for discovering driving schools, managing bookings, engaging with the community, and accessing learning resources."

    certifications:
      - "Data Analysis with Python (freeCodeCamp)"
      - "Databricks Accredited Generative AI Fundamentals"

    achievements:
      - "Patent: Steve- The Voice Assistant with Smart Blind Stick"
      - "Student Ambassador: Internshala, LetsUpgrade, eDC IIT Delhi"

    languages:
      - language: "English"
        proficiency: "Fluent"
      - language: "Telugu"
        proficiency: "Native"
      - language: "Hindi"
        proficiency: "Intermediate"

    interests:
      - "Full Stack Development"
      - "Artificial Intelligence"
      - "Open Source Projects"
      - "Digital Marketing"
      - "Entrepreneurship"

    availability:
      notice_period: "2 weeks"

    salary_expectations:
      salary_range_usd: "700000 - 1200000"

    self_identification:
      gender: "Male"
      pronouns: "He/Him"
      veteran: "No"
      disability: "No"
      ethnicity: "Asian"

    legal_authorization:
      eu_work_authorization: "No"
      us_work_authorization: "No"
      requires_us_visa: "Yes"
      legally_allowed_to_work_in_us: "No"
      requires_us_sponsorship: "Yes"

    work_preferences:
      remote_work: "Yes"
      in_person_work: "Yes"
      open_to_relocation: "Yes"
      willing_to_complete_assessments: "Yes"
      willing_to_undergo_drug_tests: "Yes"
      willing_to_undergo_background_checks: "Yes"
    """
    
    try:
        profile = JobApplicationProfile.from_yaml(yaml_str)
        print(profile)
    except Exception as e:
        logger.error(f"Error creating JobApplicationProfile: {e}")