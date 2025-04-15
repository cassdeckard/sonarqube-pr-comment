import unittest
import responses
from requests.exceptions import RequestException
from main import SonarQubePrComment
from parameterized import parameterized
from unittest.mock import patch, MagicMock

class TestSonarQubeIntegration(unittest.TestCase):
    def setUp(self):
        self.quality_gate_url = None
        self.github_api_base_url = None
        self.sonar_projectkey = None
        self.pr_number = None

    def setup_test_object(self,
                          sonar_host_url='https://sonar.example.com',
                          sonar_projectkey='my_project',
                          sonar_token='my_token',
                          github_token='my_github_token',
                          repo_name='my_repo',
                          pr_number='123',
                          github_api_base_url='https://api.github.com',
                          verbose='true'):
        self.quality_gate_url = f'{sonar_host_url}/api/qualitygates/project_status'
        self.github_api_base_url = github_api_base_url
        self.sonar_projectkey = sonar_projectkey
        self.pr_number = pr_number
        return SonarQubePrComment(
            sonar_host_url=sonar_host_url,
            sonar_projectkey=sonar_projectkey,
            sonar_token=sonar_token,
            github_token=github_token,
            repo_name=repo_name,
            pr_number=pr_number,
            github_api_base_url=github_api_base_url,
            verbose=verbose
        )

    def get_mock_response_ok(self):
        return {
            'projectStatus': {
                'status': 'OK',
                'conditions': [
                    {
                        'status': 'OK',
                        'metricKey': 'coverage',
                        'comparator': 'GT',
                        'errorThreshold': '80',
                        'actualValue': '85'
                    }
                ]
            }
        }
    
    def get_mock_response_quality_gate_error(self):
        return {
            'projectStatus': {
                'status': 'ERROR',
                'conditions': [
                    {
                        'status': 'ERROR',
                        'metricKey': 'coverage',
                        'comparator': 'GT',
                        'errorThreshold': '80',
                        'actualValue': '75'
                    }
                ]
            }
        }

    @responses.activate
    def test_get_quality_gate_status_ok(self):
        # Arrange
        test_object = self.setup_test_object()
        responses.add(
            responses.GET,
            self.quality_gate_url,
            json=self.get_mock_response_ok(),
            status=200
        )

        # Act
        quality_gate_status, project_status = test_object.get_quality_gate_status()
        code = test_object.extract_code_details(project_status, quality_gate_status)
        
        # Assert
        self.assertEqual(quality_gate_status, 'OK')
        self.assertEqual(code, '\n✅Status: OK, \nMetricKey: coverage\nComparator: GT\nErrorThreshold: 80\nActualValue: 85\n')
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, f'{self.quality_gate_url}?projectKey={self.sonar_projectkey}&pullRequest={self.pr_number}')

    @parameterized.expand([
        ("no_pr_number", None),
        ("empty_pr_number", ""),
        ("invalid_pr_number", "abc123")
    ])
    @responses.activate
    def test_get_quality_gate_status_no_pr_number_ok(self, name, pr_number):
        # Arrange
        test_object = self.setup_test_object(pr_number=pr_number)
        responses.add(
            responses.GET,
            self.quality_gate_url,
            json=self.get_mock_response_ok(),
            status=200)

        # Act
        quality_gate_status, project_status = test_object.get_quality_gate_status()
        code = test_object.extract_code_details(project_status, quality_gate_status)

        # Assert
        self.assertEqual(quality_gate_status, 'OK')
        self.assertEqual(code, '\n✅Status: OK, \nMetricKey: coverage\nComparator: GT\nErrorThreshold: 80\nActualValue: 85\n')
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, f'{self.quality_gate_url}?projectKey={self.sonar_projectkey}')

    @responses.activate
    def test_get_quality_gate_status_error(self):
        # Arrange
        test_object = self.setup_test_object()
        responses.add(
            responses.GET,
            self.quality_gate_url,
            json=self.get_mock_response_quality_gate_error(),
            status=200
        )

        # Act
        quality_gate_status, project_status = test_object.get_quality_gate_status()
        code = test_object.extract_code_details(project_status, quality_gate_status)
        
        # Assert
        self.assertEqual(quality_gate_status, 'ERROR')
        self.assertEqual(code, '\n💣Status: ERROR, \nMetricKey: coverage\nComparator: GT\nErrorThreshold: 80\nActualValue: 75\n')
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.url, f'{self.quality_gate_url}?projectKey={self.sonar_projectkey}&pullRequest={self.pr_number}')

    @responses.activate
    def test_get_quality_gate_status_api_http_error(self):
        # Arrange
        test_object = self.setup_test_object()
        responses.add(
            responses.GET,
            self.quality_gate_url,
            body='Unauthorized',
            status=401
        )

        # Act
        with self.assertRaises(RequestException):
            test_object.get_quality_gate_status()

        # Assert
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_get_quality_gate_status_api_response_parse_error(self):
        # Arrange
        test_object = self.setup_test_object()
        responses.add(
            responses.GET,
            self.quality_gate_url,
            json={'error': 'something happened'},
            status=200
        )

        # Act
        with self.assertRaises(KeyError):
            test_object.get_quality_gate_status()

        # Assert
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_code_validation_ok(self):
        # Arrange
        test_object = self.setup_test_object()
        responses.add(
            responses.GET,
            self.quality_gate_url,
            json=self.get_mock_response_ok(),
            status=200
        )

        # Act
        result = test_object.code_validation()

        # Assert
        self.assertTrue('Quality Gate has PASSED' in result)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_code_validation_error(self):
        # Arrange
        test_object = self.setup_test_object()
        responses.add(
            responses.GET,
            self.quality_gate_url,
            json=self.get_mock_response_quality_gate_error(),
            status=200
        )

        # Act
        result = test_object.code_validation()

        # Assert
        self.assertTrue('Quality Gate has FAILED' in result)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_code_validation_api_http_error(self):
        # Arrange
        test_object = self.setup_test_object()
        responses.add(
            responses.GET,
            self.quality_gate_url,
            body='Unauthorized',
            status=401
        )

        # Act
        result = test_object.code_validation()

        # Assert
        self.assertTrue('quality_check=API ERROR: REQUEST ERROR: 401' in result)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_code_validation_api_response_parse_error(self):
        # Arrange
        test_object = self.setup_test_object()
        responses.add(
            responses.GET,
            self.quality_gate_url,
            json={'error': 'something happened'},
            status=200
        )

        # Act
        result = test_object.code_validation()

        # Assert
        self.assertTrue('quality_check=API ERROR: PARSE ERROR' in result)
        self.assertEqual(len(responses.calls), 1)

    @parameterized.expand([
        ("no_pr_number", None),
        ("empty_pr_number", ""),
        ("invalid_pr_number", "abc123")
    ])
    @responses.activate
    def test_code_validation_no_pr_number_ok(self, name, pr_number):
        # Arrange
        test_object = self.setup_test_object(pr_number=pr_number)
        responses.add(
            responses.GET,
            self.quality_gate_url,
            json=self.get_mock_response_ok(),
            status=200
        )

        # Act
        result = test_object.code_validation()

        # Assert
        self.assertTrue('Quality Gate has PASSED' in result)
        self.assertEqual(len(responses.calls), 1)

    @patch('main.Github')
    def test_comment_on_pull_request_ok(self, mock_github_class):
        # Arrange
        test_object = self.setup_test_object()

        # Setup mock objects
        mock_github = MagicMock()
        mock_repo = MagicMock()
        mock_pull = MagicMock()

        # Configure the mock chain
        mock_github_class.return_value = mock_github
        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pull

        # Act
        test_object.comment_on_pull_request("Test comment")

        # Assert
        mock_github_class.assert_called_once_with(test_object.github_token, base_url=self.github_api_base_url)
        mock_github.get_repo.assert_called_once_with(test_object.repo_name)
        mock_repo.get_pull.assert_called_once_with(int(test_object.pr_number))
        mock_pull.create_issue_comment.assert_called_once_with("Test comment")

    @parameterized.expand([
        ("no_config", None, None, None),
        ("no_pr_number", "fake token", "fake repo", None),
        ("empty_pr_number", "fake token", "fake repo", ""),
        ("invalid_pr_number", "fake token", "fake repo", "abc123"),
        ("no_github_token", None, "fake repo", "123"),
        ("no_repo_name", "fake token", None, "123"),
    ])
    @patch('main.Github')
    def test_comment_on_pull_request_invalid_github_config(self, name, github_token, repo_name, pr_number, mock_github_class):
        # Arrange
        test_object = self.setup_test_object(github_token=github_token, repo_name=repo_name, pr_number=pr_number)

        # Act
        test_object.comment_on_pull_request("Test comment")

        # Assert
        mock_github_class.assert_not_called()

if __name__ == '__main__':
    unittest.main() 