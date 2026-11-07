import http from 'k6/http';
import { check, sleep } from 'k6';
import exec from 'k6/execution';

const phase = __ENV.PHASE || 'read';
if (!['warmup', 'read', 'write', 'enqueue'].includes(phase)) throw new Error('Invalid phase');
const fixtures = JSON.parse(open('/work/fixtures.json'));
const boundedRead = phase === 'read' || phase === 'warmup';
export const options = {
  scenarios: {
    bounded: boundedRead
      ? { executor: 'constant-vus', vus: phase === 'warmup' ? 2 : 4, duration: phase === 'warmup' ? '5s' : '20s', gracefulStop: '3s' }
      : { executor: 'shared-iterations', vus: 2, iterations: phase === 'enqueue' ? 60 : 40, maxDuration: '20s' },
  },
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(95)', 'p(99)'],
  thresholds: { http_req_failed: ['rate==0'], checks: ['rate==1'] },
  discardResponseBodies: true,
};
const base = 'http://bench-api:8080/api/incidents';
export default function () {
  if (boundedRead) {
    const n = exec.scenario.iterationInTest;
    const paths = ['', '?severity=HIGH&status=PENDING&service=bench-seed', '/' + fixtures.ids[n % fixtures.ids.length]];
    const response = http.get(base + paths[n % 3], { timeout: '5s', tags: { name: ['list', 'filtered-list', 'detail'][n % 3] } });
    check(response, { 'HTTP 200': r => r.status === 200 });
    sleep(0.05);
  } else {
    const service = 'bench-' + (phase === 'enqueue' ? 'async' : 'write') + '-' + __ENV.BENCH_RUN;
    const response = http.post(base, JSON.stringify({ service, title: 'Synthetic connection pool timeout', description: 'PostgreSQL too many clients, connection pool exhausted, SQLSTATE 08006.', severity: 'HIGH' }),
      { timeout: '5s', headers: { 'Content-Type': 'application/json' }, tags: { name: 'create' } });
    check(response, { 'HTTP 201': r => r.status === 201 });
    sleep(0.1);
  }
}
export function handleSummary(data) {
  return { ['/results/' + phase + '.json']: JSON.stringify(data, null, 2), stdout: phase + ': ' + JSON.stringify(data.metrics.http_req_duration.values) + '\n' };
}
