"""Render the real regional contracts; never use application secrets."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


class RegionalTopologyTests(unittest.TestCase):
    def setUp(self):
        (ROOT / '.codex-tmp').mkdir(exist_ok=True)
        self.scratch = tempfile.TemporaryDirectory(dir=ROOT / '.codex-tmp')
        self.addCleanup(self.scratch.cleanup)
        self.env_file = Path(self.scratch.name) / '.env'
        self.env_file.write_text('')
        self.env = os.environ | {
            'FITICIAN_ENV_FILE': str(self.env_file),
            'DOCKERHUB_USERNAME': 'example', 'IMAGE_TAG': 'a' * 40,
            'POSTGRES_PASSWORD': 'test-only', 'REDIS_PASSWORD': 'test-only',
            'DATABASE_URL': 'postgresql+psycopg://fitician:test-only@db:5432/fitician',
            'FITICIAN_DOMAIN': 'example.com',
            'AGENT_SERVICE_BASE_URL': 'https://agent.example.ts.net',
            'AGENT_SERVICE_TOKEN': 'test-only-token-that-is-more-than-32-characters',
            'POSTGRES_VOLUME_NAME': 'test-pg', 'REDIS_VOLUME_NAME': 'test-redis',
            'CADDY_DATA_VOLUME_NAME': 'test-caddy', 'CADDY_CONFIG_VOLUME_NAME': 'test-caddy-config',
            'AGENT_HOME_VOLUME_NAME': 'existing-agent-home',
        }

    def render(self, region):
        result = subprocess.run(['docker', 'compose', '-f', f'compose.prod.{region}.yaml',
                                 'config', '--format', 'json'], cwd=ROOT, env=self.env,
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def test_iran_starts_without_local_agent_and_keeps_data_private(self):
        config = self.render('iran')
        services = config['services']
        self.assertEqual(set(services), {'db', 'redis', 'backend', 'backend-2', 'migrations',
                                       'food-photo-worker', 'body-analysis-worker',
                                       'notification-worker', 'scheduler', 'frontend', 'caddy'})
        for name, service in services.items():
            self.assertNotIn('agent-service', service.get('depends_on', {}), name)
            if name != 'caddy':
                self.assertFalse(service.get('ports'), name)
            if name in {'backend', 'backend-2', 'food-photo-worker', 'body-analysis-worker',
                        'scheduler', 'notification-worker'}:
                self.assertEqual(service['environment']['AGENT_SERVICE_BASE_URL'],
                                 self.env['AGENT_SERVICE_BASE_URL'])
        for volume in config['volumes'].values():
            self.assertTrue(volume['external'])
        self.assertEqual(int(services['db']['mem_limit']), 512 * 1024**2)

    def test_netherlands_has_only_agent_and_existing_auth_volume(self):
        config = self.render('netherlands')
        self.assertEqual(set(config['services']), {'agent-service'})
        agent = config['services']['agent-service']
        self.assertNotIn('env_file', agent)
        self.assertFalse(any(key.startswith(('S3_', 'DATABASE_', 'REDIS_'))
                             for key in agent['environment']))
        self.assertEqual(agent['ports'][0]['host_ip'], '127.0.0.1')
        self.assertEqual(agent['ports'][0]['published'], '9001')
        self.assertEqual(len(agent['volumes']), 1)
        volume = config['volumes']['fitician_agent_home']
        self.assertTrue(volume['external'])
        self.assertEqual(volume['name'], 'existing-agent-home')

    def test_capacity_uses_region_specific_rendered_limits(self):
        for region in ('iran', 'netherlands'):
            result = subprocess.run([sys.executable, 'ops/check-runtime-capacity.py',
                                     '--region', region, '--compose-file',
                                     f'compose.prod.{region}.yaml'], cwd=ROOT, env=self.env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            payload = json.loads(result.stdout)
            self.assertTrue(payload['within_budget'])
            self.assertGreaterEqual(payload['memory_headroom_mib'], 750)
            if region == 'iran':
                self.assertNotIn('agent-service', payload['services'])
                self.assertEqual(payload['replicas'], 2)
            else:
                self.assertEqual(set(payload['services']), {'agent-service'})

    def test_capacity_rejects_wrong_host_topology(self):
        for region, filename in (('iran', 'compose.prod.yaml'),
                                 ('netherlands', 'compose.prod.iran.yaml')):
            result = subprocess.run([sys.executable, 'ops/check-runtime-capacity.py',
                                     '--region', region, '--compose-file', filename],
                                    cwd=ROOT, env=self.env, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('runtime capacity configuration invalid', result.stderr)

    def test_iran_over_budget_resources_fail_closed(self):
        result = subprocess.run([sys.executable, 'ops/check-runtime-capacity.py',
                                 '--region', 'iran', '--compose-file', 'compose.prod.iran.yaml'],
                                cwd=ROOT, env=self.env | {'BACKEND_MEMORY_LIMIT': '2g'},
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['within_budget'])


if __name__ == '__main__':
    unittest.main()
