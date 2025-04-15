import os
import requests
from github import Github
from requests.exceptions import RequestException

class SonarQubePrComment:
    def __init__(self, sonar_host_url, sonar_projectkey, sonar_token, github_token, repo_name, pr_number, github_api_base_url, verbose):
        self.sonar_host_url = sonar_host_url
        self.sonar_projectkey = sonar_projectkey
        self.sonar_token = sonar_token
        self.github_token = github_token
        self.repo_name = repo_name
        self.pr_number = pr_number
        self.github_api_base_url = github_api_base_url
        self.verbose = verbose

        if verbose:
            self.verbose_print(f"Configuration:")
            self.verbose_print(f"SONAR_HOST_URL: {self.sonar_host_url}")
            self.verbose_print(f"SONAR_PROJECTKEY: {self.sonar_projectkey}")
            self.verbose_print(f"SONAR_TOKEN: {'[REDACTED]' if self.sonar_token else 'None'}")
            self.verbose_print(f"GITHUB_TOKEN: {'[REDACTED]' if self.github_token else 'None'}")
            self.verbose_print(f"GITHUB_REPOSITORY: {self.repo_name}")
            self.verbose_print(f"PR_NUMBER: {self.pr_number}")
            self.verbose_print(f"GITHUB_API_BASE_URL: {self.github_api_base_url}")
            self.verbose_print(f"VERBOSE: {self.verbose}")

    def verbose_print(self, message):
        if self.verbose:
            print(f"VERBOSE: {message}")

    def get_quality_gate_status(self):
        quality_gate_url = f"{self.sonar_host_url}/api/qualitygates/project_status?projectKey={self.sonar_projectkey}"

        # Debug output for configuration
        self.verbose_print(f"Configuration:")
        self.verbose_print(f"SONAR_HOST_URL: {self.sonar_host_url}")
        self.verbose_print(f"SONAR_PROJECTKEY: {self.sonar_projectkey}")
        self.verbose_print(f"SONAR_TOKEN: {'[REDACTED]' if self.sonar_token else 'None'}")
        self.verbose_print(f"Quality Gate URL: {quality_gate_url}")

        # Make the request to the SonarQube API
        try:
            response = requests.get(quality_gate_url, auth=(self.sonar_token, ''))
            self.verbose_print(f"Response Status Code: {response.status_code}")
            self.verbose_print(f"Response Headers: {response.headers}")

            if response.status_code != 200:
                self.verbose_print(f"Error Response Body: {response.text}")

            response.raise_for_status()

            project_status = response.json()
            self.verbose_print(f"Full Response JSON: {project_status}")

            quality_gate_status = project_status['projectStatus']['status']
            self.verbose_print(f"Quality gate status retrieved: {quality_gate_status}")

            return quality_gate_status, project_status
        except RequestException as e:
            self.verbose_print(f"Request Exception: {str(e)}")
            raise
        except KeyError as e:
            self.verbose_print(f"JSON Structure Error: {str(e)}")
            self.verbose_print(f"Available Keys: {project_status.keys() if 'project_status' in locals() else 'No response data'}")
            raise

    def extract_code_details(self, project_status, status_filter):
        # Filter conditions based on status ("OK" or "ERROR")
        conditions = project_status['projectStatus']['conditions']
        filtered_conditions = [condition for condition in conditions if condition['status'] == status_filter]

        # Create formatted strings with details of the filtered conditions
        details = [
            f"\n{'✅' if status_filter == 'OK' else '💣'}Status: {condition['status']}, \n"
            f"MetricKey: {condition['metricKey']}\n"
            f"Comparator: {condition['comparator']}\n"
            f"ErrorThreshold: {condition['errorThreshold']}\n"
            f"ActualValue: {condition['actualValue']}\n"
            for condition in filtered_conditions
        ]
        
        return ''.join(details)

    def code_validation(self):
        try:
            quality_gate_status, project_status = self.get_quality_gate_status()
            match quality_gate_status:
                case "OK":
                    code_ok = self.extract_code_details(project_status, "OK")
                    return f"👋 Hey, the Quality Gate has PASSED.{code_ok}"
                case "ERROR":
                    code_fail = self.extract_code_details(project_status, "ERROR")
                    return f"👋 Hey, the Quality Gate has FAILED.{code_fail}"
                case _:
                    return "quality_check=ERROR CONFIGURATION"
        except Exception as e:
            match e:
                case KeyError():
                    return f"quality_check=API ERROR: PARSE ERROR: {str(e)}"
                case RequestException():
                    return f"quality_check=API ERROR: REQUEST ERROR: {str(e)}"
                case _:
                    return f"quality_check=API ERROR: {str(e)}"

    def comment_on_pull_request(self, body):
        if not (self.github_token and self.repo_name and self.pr_number):
            self.verbose_print("Error: GitHub token, repository, or PR number not configured.")

        # Authenticate with GitHub
        if self.github_api_base_url is not None:
            g = Github(self.github_token, base_url=self.github_api_base_url)
        else:
            g = Github(self.github_token)
            
        repo = g.get_repo(self.repo_name)
        pull_request = repo.get_pull(int(self.pr_number))

        self.verbose_print(f"Commenting on Pull Request #{self.pr_number}.")
        # Comment on the Pull Request
        pull_request.create_issue_comment(body)

if __name__ == "__main__":

    sonarqube_pr_comment = SonarQubePrComment(
        sonar_host_url = os.getenv('SONAR_HOST_URL'),
        sonar_projectkey = os.getenv('SONAR_PROJECTKEY'),
        sonar_token = os.getenv('SONAR_TOKEN'),
        github_token = os.getenv('GITHUB_TOKEN'),
        repo_name = os.getenv('GITHUB_REPOSITORY'),
        pr_number = os.getenv('PR_NUMBER'),
        github_api_base_url = os.getenv('GITHUB_API_BASE_URL') or None,
        verbose = os.getenv('VERBOSE') == 'true'
    )

    # Execute code validation
    result = sonarqube_pr_comment.code_validation()
    
    # Comment on the Pull Request
    sonarqube_pr_comment.comment_on_pull_request(result)