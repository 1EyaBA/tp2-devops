// Test de charge k6 — 3 scénarios enchaînés : ramp-up, stress, spike
// Lancement : k6 run -e BASE_URL=http://localhost:8080 k6/load-test.js
// Mode incident : k6 run -e FLAKY_SHARE=0.3 k6/load-test.js (avec FLAKY_ERROR_RATE=0.5 côté pod)
import http from 'k6/http';
import { check, sleep } from 'k6';

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
const FLAKY_SHARE = parseFloat(__ENV.FLAKY_SHARE || '0.01');   // part du trafic vers /flaky
const CHECKOUT_SHARE = 0.3;
const SCALE = parseFloat(__ENV.SCALE || '1');                    // ex. 0.3 sur une petite machine
const vu = (n) => Math.max(1, Math.round(n * SCALE));                                      // part du trafic vers /checkout

export const options = {
  scenarios: {
    // 1) Ramp-up : 0 -> 100 VU
    ramp_up: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '2m', target: vu(100) },
        { duration: '1m', target: vu(100) },
        { duration: '30s', target: 0 },
      ],
      gracefulRampDown: '10s',
    },
    // 2) Stress test prolongé : 500 VU
    stress: {
      executor: 'ramping-vus',
      startTime: '4m',
      startVUs: 0,
      stages: [
        { duration: '1m', target: vu(500) },
        { duration: '5m', target: vu(500) },
        { duration: '1m', target: 0 },
      ],
      gracefulRampDown: '10s',
    },
    // 3) Spike : montée brutale à 1500 VU pendant 30 s
    spike: {
      executor: 'ramping-vus',
      startTime: '12m',
      startVUs: 0,
      stages: [
        { duration: '10s', target: vu(1500) },
        { duration: '30s', target: vu(1500) },
        { duration: '10s', target: 0 },
      ],
      gracefulRampDown: '5s',
    },
  },
  // Les SLO sont traduits en seuils k6 : le test est "rouge" si un SLO est violé
  thresholds: {
    http_req_failed: ['rate<0.005'],          // Availability SLO 99.5 %
    http_req_duration: ['p(95)<200'],         // Latency SLO p95 <= 200 ms
    'http_req_duration{scenario:spike}': ['p(95)<200'],
    'http_req_duration{scenario:stress}': ['p(95)<200'],
  },
};

const headers = { 'Content-Type': 'application/json' };

export default function () {
  const r = Math.random();
  let res;
  if (r < FLAKY_SHARE) {
    res = http.get(`${BASE_URL}/flaky`, { tags: { endpoint: 'flaky' } });
  } else if (r < FLAKY_SHARE + CHECKOUT_SHARE) {
    const body = JSON.stringify({
      items: [{ product_id: 1 + Math.floor(Math.random() * 3), quantity: 1 }],
    });
    res = http.post(`${BASE_URL}/checkout`, body, { headers, tags: { endpoint: 'checkout' } });
  } else if (r < 0.7) {
    res = http.get(`${BASE_URL}/products`, { tags: { endpoint: 'products' } });
  } else {
    const id = 1 + Math.floor(Math.random() * 4);
    res = http.get(`${BASE_URL}/products/${id}`, { tags: { endpoint: 'product' } });
  }
  check(res, { 'status < 500': (x) => x.status < 500 });
  sleep(Math.random() * 0.5 + 0.5); // temps de réflexion 0.5 à 1 s
}
