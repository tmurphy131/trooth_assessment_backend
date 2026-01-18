import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const apiLatency = new Trend('api_latency');
const assessmentSubmissions = new Counter('assessment_submissions');
const draftSaves = new Counter('draft_saves');

// Configuration - passed via environment variables
const BASE_URL = __ENV.BASE_URL || 'https://trooth-backend-dev-301248215198.us-east4.run.app';
const AUTH_TOKEN = __ENV.AUTH_TOKEN || '';
const MENTOR_TOKEN = __ENV.MENTOR_TOKEN || '';  // Optional: for mentor operations

// Shared state for draft IDs (used across VU iterations)
let activeDraftIds = [];
let availableTemplateId = null;

// Test scenarios - Ramping Virtual Users
export const options = {
  scenarios: {
    load_test: {
      executor: 'ramping-vus',
      startVUs: 1,
      stages: [
        { duration: '30s', target: 10 },   // Warm up: Ramp to 10 users over 30s
        { duration: '1m', target: 25 },    // Ramp to 25 users over 1 min
        { duration: '2m', target: 50 },    // Hold at 50 users for 2 min  
        { duration: '1m', target: 100 },   // Spike to 100 users over 1 min
        { duration: '30s', target: 0 },    // Ramp down to 0
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    http_req_duration: ['p(95)<3000'],  // 95% of requests should be under 3s (increased for submissions)
    errors: ['rate<0.15'],               // Error rate should be under 15%
    'http_req_duration{type:submission}': ['p(95)<5000'],  // Submissions can take longer
  },
};

// Headers for authenticated requests
function getHeaders() {
  const headers = {
    'Content-Type': 'application/json',
  };
  if (AUTH_TOKEN) {
    headers['Authorization'] = `Bearer ${AUTH_TOKEN}`;
  }
  return headers;
}

// Main test function - called repeatedly by each virtual user
export default function () {
  const testGroup = Math.random();
  
  if (testGroup < 0.20) {
    // 20% - Health check (lightweight, unauthenticated)
    testHealthCheck();
  } else if (testGroup < 0.35) {
    // 15% - Browse templates (common read operation)
    testReadOperations();
  } else if (testGroup < 0.50) {
    // 15% - User profile operations  
    testUserOperations();
  } else if (testGroup < 0.65) {
    // 15% - Assessment browsing flow
    testAssessmentBrowsing();
  } else if (testGroup < 0.80) {
    // 15% - Draft auto-save simulation (frequent during assessment)
    testDraftAutoSave();
  } else if (testGroup < 0.92) {
    // 12% - FULL ASSESSMENT WORKFLOW (start → save → submit)
    testFullAssessmentWorkflow();
  } else {
    // 8% - Mentor operations (if token provided)
    testMentorOperations();
  }
  
  // Random think time between requests (1-3 seconds)
  sleep(Math.random() * 2 + 1);
}

function testHealthCheck() {
  const start = Date.now();
  const res = http.get(`${BASE_URL}/health`);
  apiLatency.add(Date.now() - start);
  
  const success = check(res, {
    'health check status 200': (r) => r.status === 200,
    'health check has status field': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.status === 'healthy';
      } catch {
        return false;
      }
    },
  });
  errorRate.add(!success);
}

function testReadOperations() {
  const headers = getHeaders();
  const start = Date.now();
  
  // Get published templates (requires auth)
  const res = http.get(`${BASE_URL}/templates/published`, { headers });
  apiLatency.add(Date.now() - start);
  
  const success = check(res, {
    'templates status 200 or 401': (r) => r.status === 200 || r.status === 401,
    'templates response is array or error': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body) || body.detail;
      } catch {
        return false;
      }
    },
  });
  errorRate.add(!success);
}

function testUserOperations() {
  const headers = getHeaders();
  const start = Date.now();
  
  // Get current user (apprentice endpoint)
  const res = http.get(`${BASE_URL}/apprentice/me`, { headers });
  apiLatency.add(Date.now() - start);
  
  const success = check(res, {
    'user endpoint responds': (r) => r.status === 200 || r.status === 401 || r.status === 404,
  });
  errorRate.add(!success);
}

function testAssessmentBrowsing() {
  const headers = getHeaders();
  
  // Simulate user browsing flow
  // 1. Get templates
  const start1 = Date.now();
  const templatesRes = http.get(`${BASE_URL}/templates/published`, { headers });
  apiLatency.add(Date.now() - start1);
  
  check(templatesRes, {
    'browse templates ok': (r) => r.status < 500,
  });
  
  sleep(0.5); // Brief pause between requests
  
  // 2. Get user profile
  const start2 = Date.now();
  const profileRes = http.get(`${BASE_URL}/apprentice/me`, { headers });
  apiLatency.add(Date.now() - start2);
  
  const success = check(profileRes, {
    'browse profile ok': (r) => r.status < 500,
  });
  errorRate.add(!success);
}

// ============================================================================
// NEW: Draft Auto-Save Test (simulates frequent saves during assessment)
// ============================================================================
function testDraftAutoSave() {
  const headers = getHeaders();
  
  // First, we need a draft to save. Try to get existing drafts (correct endpoint is /list)
  const start = Date.now();
  const draftsRes = http.get(`${BASE_URL}/assessment-drafts/list`, { headers });
  apiLatency.add(Date.now() - start);
  
  if (draftsRes.status === 200) {
    try {
      const draftsList = JSON.parse(draftsRes.body);
      if (Array.isArray(draftsList) && draftsList.length > 0) {
        // Pick a random draft to "save"
        const draftSummary = draftsList[Math.floor(Math.random() * draftsList.length)];
        
        // Fetch full draft to get questions (we need real question IDs for answers)
        const fullDraftRes = http.get(`${BASE_URL}/assessment-drafts/${draftSummary.id}`, { headers });
        if (fullDraftRes.status !== 200) {
          testReadOperations();
          return;
        }
        
        const fullDraft = JSON.parse(fullDraftRes.body);
        const questions = fullDraft.questions || [];
        
        // Generate answers using REAL question IDs
        const answers = generateAnswersFromQuestions(questions);
        if (Object.keys(answers).length === 0) {
          testReadOperations();
          return;
        }
        
        // Simulate auto-save with real question IDs
        const saveStart = Date.now();
        const saveRes = http.patch(
          `${BASE_URL}/assessment-drafts/${fullDraft.id}`,
          JSON.stringify({ answers }),
          { headers, tags: { type: 'autosave' } }
        );
        apiLatency.add(Date.now() - saveStart);
        draftSaves.add(1);
        
        const success = check(saveRes, {
          'draft save responds': (r) => r.status < 500,
        });
        errorRate.add(!success);
        return;
      }
    } catch (e) {
      // If parsing fails, just skip
    }
  }
  
  // Fallback: just do a read operation
  testReadOperations();
}

// Generate answers using real question IDs from the questions array
function generateAnswersFromQuestions(questions) {
  const answers = {};
  if (!questions || !Array.isArray(questions)) return answers;
  
  questions.forEach((q, idx) => {
    // Use the question's actual ID as the answer key
    const questionId = q.id;
    if (!questionId) return;
    
    if (q.question_type === 'multiple_choice' && q.options && q.options.length > 0) {
      // Pick a random option (use option text or value)
      const options = q.options;
      const selected = options[Math.floor(Math.random() * options.length)];
      answers[questionId] = selected.option_text || selected.text || selected.value || String(idx);
    } else {
      // Open-ended response
      answers[questionId] = `Load test response for question ${idx + 1}. ` +
        `This is a thoughtful answer demonstrating understanding. ` +
        `Testing at ${new Date().toISOString()}.`;
    }
  });
  
  return answers;
}

// ============================================================================
// NEW: Full Assessment Workflow (START → SAVE → SUBMIT)
// This is the critical test for concurrent assessment submissions
// ============================================================================
function testFullAssessmentWorkflow() {
  const headers = getHeaders();
  
  group('Assessment Workflow', function() {
    // Step 1: Check for existing drafts first (correct endpoint is /list)
    const draftsRes = http.get(`${BASE_URL}/assessment-drafts/list`, { headers });
    
    let existingDrafts = [];
    if (draftsRes.status === 200) {
      try {
        existingDrafts = JSON.parse(draftsRes.body);
      } catch (e) {
        existingDrafts = [];
      }
    }
    
    // If we have existing drafts, work with those instead of creating new ones
    if (Array.isArray(existingDrafts) && existingDrafts.length > 0) {
      // Pick a random existing draft
      const draftSummary = existingDrafts[Math.floor(Math.random() * existingDrafts.length)];
      
      // Fetch full draft to get questions (we need real question IDs for answers)
      const fullDraftRes = http.get(`${BASE_URL}/assessment-drafts/${draftSummary.id}`, { headers });
      if (fullDraftRes.status !== 200) {
        return; // Skip if we can't fetch full draft
      }
      
      let fullDraft;
      try {
        fullDraft = JSON.parse(fullDraftRes.body);
      } catch (e) {
        return;
      }
      
      const questions = fullDraft.questions || [];
      
      // Generate answers using REAL question IDs
      const answers = generateAnswersFromQuestions(questions);
      if (Object.keys(answers).length === 0) {
        return; // Skip if no valid questions
      }
      
      // Simulate auto-save on existing draft with real question IDs
      const saveRes = http.patch(
        `${BASE_URL}/assessment-drafts/${fullDraft.id}`,
        JSON.stringify({ answers }),
        { headers, tags: { type: 'autosave' } }
      );
      draftSaves.add(1);
      
      check(saveRes, {
        'draft save ok': (r) => r.status < 500,
      });
      
      // 30% chance to submit an existing draft (to test submissions without creating too many)
      if (Math.random() < 0.3) {
        const submitStart = Date.now();
        const submitRes = http.post(
          `${BASE_URL}/assessment-drafts/submit?draft_id=${fullDraft.id}`,
          null,
          { headers, tags: { type: 'submission' } }
        );
        const submitDuration = Date.now() - submitStart;
        apiLatency.add(submitDuration);
        assessmentSubmissions.add(1);
        
        const submitSuccess = check(submitRes, {
          'submission accepted or already submitted': (r) => r.status === 200 || r.status === 201 || r.status === 202 || r.status === 400,
          'submission not server error': (r) => r.status < 500,
        });
        
        if (submitRes.status >= 500) {
          console.log(`Submission error: ${submitRes.status} - ${submitRes.body.substring(0, 200)}`);
          errorRate.add(true);
        }
        
        if (submitDuration > 2000) {
          console.log(`Slow submission: ${submitDuration}ms`);
        }
      }
      return;
    }
    
    // Step 2: Get available templates (only if no existing drafts)
    const templatesRes = http.get(`${BASE_URL}/templates/published`, { headers });
    
    if (templatesRes.status !== 200) {
      if (__ITER < 5) {
        console.log(`Templates endpoint returned ${templatesRes.status}: ${templatesRes.body.substring(0, 200)}`);
      }
      errorRate.add(true);
      return;
    }
    
    let templates;
    try {
      templates = JSON.parse(templatesRes.body);
    } catch (e) {
      errorRate.add(true);
      return;
    }
    
    if (!Array.isArray(templates) || templates.length === 0) {
      return;
    }
    
    // Pick a random template
    const template = templates[Math.floor(Math.random() * templates.length)];
    
    sleep(0.3); // User reads template description
    
    // Step 3: Start a new draft (template_id is a QUERY parameter, not body)
    const startDraftRes = http.post(
      `${BASE_URL}/assessment-drafts/start?template_id=${template.id}`,
      null,
      { headers, tags: { type: 'draft_start' } }
    );
    
    // Handle case where draft already exists for this template (409 Conflict)
    if (startDraftRes.status === 409 || startDraftRes.status === 400) {
      // User already has a draft for this template - this is expected
      return;
    }
    
    if (startDraftRes.status !== 200 && startDraftRes.status !== 201) {
      if (__ITER < 3) {
        console.log(`Draft start failed: ${startDraftRes.status} - ${startDraftRes.body.substring(0, 200)}`);
      }
      check(startDraftRes, {
        'draft start ok': (r) => r.status < 500,
      });
      if (startDraftRes.status >= 500) {
        errorRate.add(true);
      }
      return;
    }
    
    let draft;
    try {
      draft = JSON.parse(startDraftRes.body);
    } catch (e) {
      errorRate.add(true);
      return;
    }
    
    // The draft response includes questions - use those for real answer keys
    const questions = draft.questions || [];
    if (questions.length === 0) {
      console.log('Draft has no questions, skipping');
      return;
    }
    
    sleep(0.5); // User starts filling out assessment
    
    // Step 4: Simulate auto-saves (2-3 saves as user fills form)
    const numSaves = Math.floor(Math.random() * 2) + 2;
    for (let i = 0; i < numSaves; i++) {
      // Use REAL question IDs from the draft's questions
      const answers = generateAnswersFromQuestions(questions);
      
      const saveRes = http.patch(
        `${BASE_URL}/assessment-drafts/${draft.id}`,
        JSON.stringify({ answers }),
        { headers, tags: { type: 'autosave' } }
      );
      draftSaves.add(1);
      
      check(saveRes, {
        'auto-save successful': (r) => r.status < 500,
      });
      
      sleep(0.3 + Math.random() * 0.5); // Time between saves
    }
    
    // Step 5: SUBMIT the assessment (the big one!)
    const submitStart = Date.now();
    const submitRes = http.post(
      `${BASE_URL}/assessment-drafts/submit?draft_id=${draft.id}`,
      null,
      { headers, tags: { type: 'submission' } }
    );
    const submitDuration = Date.now() - submitStart;
    apiLatency.add(submitDuration);
    assessmentSubmissions.add(1);
    
    const submitSuccess = check(submitRes, {
      'submission accepted': (r) => r.status === 200 || r.status === 201 || r.status === 202,
      'submission not server error': (r) => r.status < 500,
    });
    
    if (!submitSuccess) {
      console.log(`Submission failed: ${submitRes.status} - ${submitRes.body.substring(0, 200)}`);
    }
    errorRate.add(!submitSuccess);
    
    // Log submission timing for analysis
    if (submitDuration > 2000) {
      console.log(`Slow submission: ${submitDuration}ms`);
    }
  });
}

// ============================================================================
// NEW: Mentor Operations (requires MENTOR_TOKEN)
// ============================================================================
function testMentorOperations() {
  // Use mentor token if available, otherwise fall back to regular token
  const token = MENTOR_TOKEN || AUTH_TOKEN;
  if (!token) {
    testReadOperations();
    return;
  }
  
  const headers = {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`,
  };
  
  const testType = Math.random();
  
  if (testType < 0.5) {
    // Get mentor's apprentices
    const start = Date.now();
    const res = http.get(`${BASE_URL}/mentor/my-apprentices`, { headers });
    apiLatency.add(Date.now() - start);
    
    check(res, {
      'mentor apprentices responds': (r) => r.status < 500,
    });
  } else {
    // Get submitted assessments for review
    const start = Date.now();
    const res = http.get(`${BASE_URL}/mentor/submitted-drafts`, { headers });
    apiLatency.add(Date.now() - start);
    
    check(res, {
      'mentor submissions responds': (r) => r.status < 500,
    });
  }
}

// Setup function - runs once at the start
export function setup() {
  console.log(`Starting load test against: ${BASE_URL}`);
  console.log(`Auth token provided: ${AUTH_TOKEN ? 'Yes' : 'No'}`);
  
  // Quick health check to ensure server is up
  const res = http.get(`${BASE_URL}/health`);
  if (res.status !== 200) {
    throw new Error(`Server health check failed! Status: ${res.status}`);
  }
  console.log('Server is healthy, starting test...');
}

// Teardown function - runs once at the end
export function teardown(data) {
  console.log('Load test completed!');
}

// Custom summary output
export function handleSummary(data) {
  const summary = {
    timestamp: new Date().toISOString(),
    baseUrl: BASE_URL,
    metrics: {
      totalRequests: data.metrics.http_reqs?.values?.count || 0,
      failedRequests: data.metrics.http_req_failed?.values?.passes || 0,
      avgResponseTime: data.metrics.http_req_duration?.values?.avg?.toFixed(2) || 'N/A',
      p95ResponseTime: data.metrics.http_req_duration?.values['p(95)']?.toFixed(2) || 'N/A',
      maxResponseTime: data.metrics.http_req_duration?.values?.max?.toFixed(2) || 'N/A',
      errorRate: ((data.metrics.errors?.values?.rate || 0) * 100).toFixed(2),
      // New metrics
      assessmentSubmissions: data.metrics.assessment_submissions?.values?.count || 0,
      draftSaves: data.metrics.draft_saves?.values?.count || 0,
    },
  };
  
  const textReport = `
================================================================================
                        LOAD TEST RESULTS SUMMARY
================================================================================
Timestamp:          ${summary.timestamp}
Target URL:         ${summary.baseUrl}
--------------------------------------------------------------------------------
REQUESTS
  Total:            ${summary.metrics.totalRequests}
  Failed:           ${summary.metrics.failedRequests}
  Error Rate:       ${summary.metrics.errorRate}%

RESPONSE TIMES
  Average:          ${summary.metrics.avgResponseTime}ms
  95th Percentile:  ${summary.metrics.p95ResponseTime}ms
  Maximum:          ${summary.metrics.maxResponseTime}ms

ASSESSMENT OPERATIONS
  Submissions:      ${summary.metrics.assessmentSubmissions}
  Draft Saves:      ${summary.metrics.draftSaves}
================================================================================
`;

  return {
    'load_test_results.json': JSON.stringify(summary, null, 2),
    stdout: textReport,
  };
}
