import unittest
import responses
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
        self.quality_gate_url = 'https://sonar.example.com/api/qualitygates/project_status?projectKey=my_project'

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
        responses.add(
            responses.GET,
            self.quality_gate_url,
            json=self.get_mock_response_ok(),
            status=200
        )

        quality_gate_status, project_status = self.test_object.get_quality_gate_status()
        code = self.test_object.extract_code_details(project_status, quality_gate_status)
        
        self.assertEqual(quality_gate_status, 'OK')
        self.assertEqual(code, '\n✅Status: OK, \nMetricKey: coverage\nComparator: GT\nErrorThreshold: 80\nActualValue: 85\n')
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_get_quality_gate_status_error(self):
        responses.add(
            responses.GET,
            self.quality_gate_url,
            json=self.get_mock_response_quality_gate_error(),
            status=200
        )

        quality_gate_status, project_status = self.test_object.get_quality_gate_status()
        code = self.test_object.extract_code_details(project_status, quality_gate_status)
        
        self.assertEqual(quality_gate_status, 'ERROR')
        self.assertEqual(code, '\n💣Status: ERROR, \nMetricKey: coverage\nComparator: GT\nErrorThreshold: 80\nActualValue: 75\n')
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_get_quality_gate_status_api_http_error(self):
        responses.add(
            responses.GET,
            self.quality_gate_url,
            body='Unauthorized',
            status=401
        )

        with self.assertRaises(RequestException):
            self.test_object.get_quality_gate_status()
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_get_quality_gate_status_api_response_parse_error(self):
        responses.add(
            responses.GET,
            self.quality_gate_url,
            json={'error': 'something happened'},
            status=200
        )

        with self.assertRaises(KeyError):
            self.test_object.get_quality_gate_status()
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_code_validation_ok(self):
        responses.add(
            responses.GET,
            self.quality_gate_url,
            json=self.get_mock_response_ok(),
            status=200
        )

        result = self.test_object.code_validation()
        self.assertTrue('Quality Gate has PASSED' in result)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_code_validation_error(self):
        responses.add(
            responses.GET,
            self.quality_gate_url,
            json=self.get_mock_response_quality_gate_error(),
            status=200
        )

        result = self.test_object.code_validation()
        self.assertTrue('Quality Gate has FAILED' in result)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_code_validation_api_http_error(self):
        responses.add(
            responses.GET,
            self.quality_gate_url,
            body='Unauthorized',
            status=401
        )

        result = self.test_object.code_validation()
        self.assertTrue('quality_check=API ERROR: REQUEST ERROR: 401' in result)
        self.assertEqual(len(responses.calls), 1)

    @responses.activate
    def test_code_validation_api_response_parse_error(self):
        responses.add(
            responses.GET,
            self.quality_gate_url,
            json={'error': 'something happened'},
            status=200
        )

        result = self.test_object.code_validation()
        self.assertTrue('quality_check=API ERROR: PARSE ERROR' in result)
        self.assertEqual(len(responses.calls), 1)

if __name__ == '__main__':
    unittest.main() 