import unittest
import responses
from requests.exceptions import RequestException
from main import SonarQubePrComment
from parameterized import parameterized

class TestSonarQubeIntegration(unittest.TestCase):
    def setUp(self):
        self.quality_gate_url = None
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

if __name__ == '__main__':
    unittest.main() 