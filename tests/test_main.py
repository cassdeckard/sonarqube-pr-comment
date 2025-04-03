import unittest
from unittest.mock import patch, MagicMock
from requests.exceptions import RequestException

from main import SonarQubePrComment

class TestSonarQubeIntegration(unittest.TestCase):

    def setUp(self):
        self.test_object = SonarQubePrComment(
            'https://sonar.example.com',
            'my_project',
            'my_token',
            'my_github_token',
            'my_repo',
            '123',
            'https://api.github.com',
            'true'
        )

    def get_mock_response_ok(self):
        # Mock response for a passing quality gate
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
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
        return mock_response
    
    def get_mock_response_quality_gate_error(self):
        # Mock response for a failing quality gate
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
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
        return mock_response
    
    def get_mock_response_api_http_error(self):
        # Mock response for an API error
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        return mock_response

    def get_mock_response_api_response_parse_error(self):
        # Mock response for a malformed API response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'error': 'something happened'
        }
        return mock_response

    def test_get_quality_gate_status_ok(self):
        mock_response = self.get_mock_response_ok()

        with patch('requests.get', return_value=mock_response) as mock_get:
            quality_gate_status, project_status = self.test_object.get_quality_gate_status()
            code = self.test_object.extract_code_details(project_status, quality_gate_status)
            
            # Verify the API was called correctly
            mock_get.assert_called_once()
            self.assertEqual(quality_gate_status, 'OK')
            self.assertEqual(code, '\n✅Status: OK, \nMetricKey: coverage\nComparator: GT\nErrorThreshold: 80\nActualValue: 85\n')

    def test_get_quality_gate_status_error(self):
        mock_response = self.get_mock_response_quality_gate_error()

        with patch('requests.get', return_value=mock_response) as mock_get:
            quality_gate_status, project_status = self.test_object.get_quality_gate_status()
            code = self.test_object.extract_code_details(project_status, quality_gate_status)
            
            # Verify the API was called correctly
            mock_get.assert_called_once()
            self.assertEqual(quality_gate_status, 'ERROR')
            self.assertEqual(code, '\n💣Status: ERROR, \nMetricKey: coverage\nComparator: GT\nErrorThreshold: 80\nActualValue: 75\n')

    def test_get_quality_gate_status_api_http_error(self):
        mock_response = self.get_mock_response_api_http_error()

        with patch('requests.get', return_value=mock_response) as mock_get:
            with self.assertRaises(RequestException):
                self.test_object.get_quality_gate_status()
            
            # Verify the API was called correctly
            mock_get.assert_called_once()

    def test_get_quality_gate_status_api_response_parse_error(self):
        mock_response = self.get_mock_response_api_response_parse_error()

        with patch('requests.get', return_value=mock_response) as mock_get:
            with self.assertRaises(KeyError):
                self.test_object.get_quality_gate_status()

            # Verify the API was called correctly
            mock_get.assert_called_once()

    def test_code_validation_ok(self):
        mock_response = self.get_mock_response_ok()

        with patch('requests.get', return_value=mock_response) as mock_get:
            result = self.test_object.code_validation()

            # Verify the API was called correctly
            mock_get.assert_called_once()
            self.assertTrue('Quality Gate has PASSED' in result)

    def test_code_validation_error(self):
        mock_response = self.get_mock_response_quality_gate_error()

        with patch('requests.get', return_value=mock_response) as mock_get:
            result = self.test_object.code_validation()

            # Verify the API was called correctly
            mock_get.assert_called_once()
            self.assertTrue('Quality Gate has FAILED' in result)

    def test_code_validation_api_http_error(self):
        mock_response = self.get_mock_response_api_http_error()

        with patch('requests.get', return_value=mock_response) as mock_get:
            result = self.test_object.code_validation()

            # Verify the API was called correctly
            mock_get.assert_called_once()
            self.assertIn('quality_check=API ERROR: HTTP 401', result)

    def test_code_validation_api_response_parse_error(self):
        mock_response = self.get_mock_response_api_response_parse_error()

        with patch('requests.get', return_value=mock_response) as mock_get:
            result = self.test_object.code_validation()

            # Verify the API was called correctly
            mock_get.assert_called_once()
            self.assertIn('quality_check=API ERROR: PARSE ERROR', result)

if __name__ == '__main__':
    unittest.main() 