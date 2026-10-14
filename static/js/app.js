const form = document.querySelector('#prediction-form');
const result = document.querySelector('#result');
const stage = document.querySelector('#water-stage');
const caption = document.querySelector('#vial-caption');

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = form.querySelector('button');
  button.disabled = true;
  button.textContent = 'Analyzing…';
  stage.className = 'water-stage analyzing';
  caption.textContent = 'Reading the five signals…';
  const values = Object.fromEntries(new FormData(form).entries());
  try {
    const response = await fetch('/api/predict', {
      method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(values)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'The sample could not be analyzed.');
    const healthy = data.status === 'Healthy';
    await new Promise((resolve) => setTimeout(resolve, 700));
    stage.className = `water-stage ${healthy ? 'healthy' : 'risk'}`;
    caption.textContent = healthy ? 'Water looks Healthy' : 'Water looks At-Risk';
    result.className = `result ${healthy ? 'healthy' : 'risk'}`;
    const analysis = data.indicator_analysis || {};
const indicators = analysis.screened_indicators || [];
const notAssessed = analysis.not_assessed || [];

const indicatorSection = indicators.length
  ? `
    <div class="indicator-analysis">
      <h3>Potential stress indicators</h3>
      <ul>
        ${indicators.map(item => `
          <li>
            <strong>${item.parameter}</strong>: ${item.value}
            <p>${item.message}</p>
          </li>
        `).join('')}
      </ul>
    </div>
  `
  : `
    <div class="indicator-analysis">
      <h3>Potential stress indicators</h3>
      <p>No indicators were flagged by the configured screening rules.</p>
    </div>
  `;

const notAssessedSection = notAssessed.length
  ? `
    <div class="not-assessed">
      <h3>Not assessed by screening rules</h3>
      <ul>
        ${notAssessed.map(item => `
          <li>
            <strong>${item.parameter}</strong>: ${item.value}
            <p>${item.reason}</p>
          </li>
        `).join('')}
      </ul>
    </div>
  `
  : '';

result.innerHTML = `
  <h2>${healthy ? '✓' : '!'} ${data.status}</h2>

  <p>
    <b>${data.healthy_probability}% Healthy probability</b>
    · ${data.at_risk_probability}% At-Risk probability
  </p>

  <p>
    ${healthy
      ? 'Continue routine monitoring and share this observation.'
      : 'Consider repeat sampling and investigate potential sources of water-quality stress.'}
  </p>

  ${indicatorSection}
  ${notAssessedSection}
`;
    result.scrollIntoView({behavior: 'smooth', block: 'center'});
  } catch (error) {
    stage.className = 'water-stage risk';
    caption.textContent = 'Unable to analyze';
    result.className = 'result risk';
    result.innerHTML = `<h2>Unable to analyze</h2><p>${error.message}</p>`;
  } finally {
    button.disabled = false;
    button.innerHTML = 'Analyze water quality <span>→</span>';
  }
});

fetch('/api/insights').then(response => response.json()).then(data => {
  const importance = Object.entries(data.feature_importance).sort((a,b) => b[1] - a[1]);
  const max = importance[0][1];
  document.querySelector('#importance-chart').innerHTML = importance.map(([name, value]) => `<div class="bar-row" title="${name}: ${value}"><span>${name}</span><div class="bar"><i style="--w:${value / max * 100}%"></i></div><b>${value}</b></div>`).join('');
  const healthy = data.health_distribution.Healthy || 0, risk = data.health_distribution['At-Risk'] || 0;
  document.querySelector('#distribution').innerHTML = `<div class="donut" style="--healthy:${healthy / (healthy + risk) * 360}deg"></div><div class="legend"><p><i class="dot" style="background:#209768"></i>Healthy: <b>${healthy}</b></p><p><i class="dot" style="background:#e06143"></i>At-Risk: <b>${risk}</b></p></div>`;
  if (data.model_check) {
    document.querySelector('#guide-check').innerHTML = `<article><span>Hold-out checks</span><strong>${data.model_check.samples}</strong></article><article><span>Match rate</span><strong>${data.model_check.accuracy}%</strong></article><article><span>Signals used</span><strong>5</strong></article><article><span>Decision</span><strong>Healthy / At-Risk</strong></article>`;
  }
});
